#!/usr/bin/env php
<?php
/**
 * cron-scheduler.php — Evaluates cron_jobs and enqueues execution jobs.
 * Run every minute via system cron.
 *
 * Crontab: * * * * * php /var/www/emme-tech/bin/cron-scheduler.php
 */

declare(strict_types=1);

define('APP_ROOT', dirname(__DIR__));
require APP_ROOT . '/app/Config/config.php';

use App\Core\DB;
use App\Lib\Logger;
use App\Lib\WhatsApp;

spl_autoload_register(function (string $class): void {
    $file = APP_ROOT . '/' . str_replace(['App\\', '\\'], ['app/', '/'], $class) . '.php';
    if (file_exists($file)) require_once $file;
});

Logger::info('cron-scheduler: starting');

$now = new DateTimeImmutable('now', new DateTimeZone('UTC'));

// Get all active crons due to run
$crons = DB::fetchAll(
    "SELECT cj.*, t.timezone AS tenant_tz, t.status AS tenant_status
     FROM cron_jobs cj
     JOIN tenants t ON t.id = cj.tenant_id
     WHERE cj.is_active = 1
       AND (cj.next_run_at IS NULL OR cj.next_run_at <= NOW())
       AND t.status IN ('active','trial')"
);

$enqueued = 0;

foreach ($crons as $cron) {
    try {
        $cronId   = (int)$cron['id'];
        $tenantId = (int)$cron['tenant_id'];
        $agentId  = (int)$cron['agent_id'];

        // Verify agent exists and is active
        $agent = DB::fetchOne('SELECT * FROM agents WHERE id = ? AND status = ?', [$agentId, 'active']);
        if (!$agent) {
            Logger::warning('cron-scheduler: agent not active', ['cron_id' => $cronId]);
            updateNextRun($cron, $now);
            continue;
        }

        // Get target phones
        $phones = resolveTargets($cron, $agentId, $tenantId);

        if (empty($phones)) {
            Logger::info('cron-scheduler: no targets', ['cron_id' => $cronId]);
            updateNextRun($cron, $now);
            continue;
        }

        // Create cron run record
        $runId = DB::insert('cron_runs', [
            'tenant_id'   => $tenantId,
            'cron_job_id' => $cronId,
            'status'      => 'running',
            'started_at'  => date('Y-m-d H:i:s'),
        ]);

        $errors = [];
        foreach ($phones as $phone) {
            try {
                enqueueMessage($cron, $agent, $phone, $tenantId, (int)$runId);
            } catch (\Throwable $e) {
                $errors[] = $phone . ': ' . $e->getMessage();
            }
        }

        $runStatus = empty($errors) ? 'done' : 'failed';
        DB::query(
            'UPDATE cron_runs SET status = ?, finished_at = NOW(), error = ? WHERE id = ?',
            [$runStatus, empty($errors) ? null : implode('; ', $errors), $runId]
        );

        updateNextRun($cron, $now);
        $enqueued++;

        Logger::info('cron-scheduler: cron executed', [
            'cron_id' => $cronId,
            'targets' => count($phones),
            'errors'  => count($errors),
        ]);
    } catch (\Throwable $e) {
        Logger::error('cron-scheduler: cron error', ['cron_id' => $cron['id'], 'error' => $e->getMessage()]);
    }
}

Logger::info("cron-scheduler: finished ($enqueued crons triggered)");

// ----------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------

function resolveTargets(array $cron, int $agentId, int $tenantId): array
{
    if ($cron['target_type'] === 'specific_phone' && $cron['target_value']) {
        return [preg_replace('/\D/', '', $cron['target_value'])];
    }

    if ($cron['target_type'] === 'all_contacts') {
        $contacts = DB::fetchAll(
            'SELECT phone FROM contacts WHERE agent_id = ? AND opt_out = 0',
            [$agentId]
        );
        return array_column($contacts, 'phone');
    }

    return [];
}

function enqueueMessage(array $cron, array $agent, string $phone, int $tenantId, int $runId): void
{
    // Get or create contact
    $contact = DB::fetchOne(
        'SELECT * FROM contacts WHERE agent_id = ? AND phone = ?',
        [$agent['id'], $phone]
    );

    if (!$contact) {
        $contactId = DB::insert('contacts', [
            'tenant_id' => $tenantId,
            'agent_id'  => $agent['id'],
            'phone'     => $phone,
        ]);
    } else {
        $contactId = (int)$contact['id'];
        if ($contact['opt_out']) return;
    }

    // Determine message type
    $inFreeWindow = $contact ? WhatsApp::inFreeWindow($contact['last_inbound_at']) : false;
    $actionType   = $cron['action_type'];

    if (!$inFreeWindow && $actionType !== 'send_template') {
        // Cannot send free text outside window
        if (!$cron['template_name']) {
            Logger::warning('cron-scheduler: outside 24h window, no template set', [
                'cron_id' => $cron['id'],
                'phone'   => $phone,
            ]);
            return;
        }
        $actionType = 'send_template';
    }

    // Get or create thread
    $thread = DB::fetchOne(
        "SELECT id FROM threads WHERE agent_id = ? AND contact_id = ? AND status = 'open' LIMIT 1",
        [$agent['id'], $contactId]
    );

    if (!$thread) {
        $threadId = DB::insert('threads', [
            'tenant_id'  => $tenantId,
            'agent_id'   => $agent['id'],
            'contact_id' => $contactId,
            'status'     => 'open',
            'started_at' => date('Y-m-d H:i:s'),
        ]);
    } else {
        $threadId = (int)$thread['id'];
    }

    $content = $actionType === 'send_template'
        ? "[Template: {$cron['template_name']}]"
        : ($cron['action_payload']['message'] ?? '');

    // Save outbound message
    $msgId = DB::insert('messages', [
        'tenant_id'    => $tenantId,
        'agent_id'     => $agent['id'],
        'thread_id'    => $threadId,
        'contact_id'   => $contactId,
        'direction'    => 'outbound',
        'content'      => $content,
        'message_type' => $actionType === 'send_template' ? 'template' : 'text',
        'status'       => 'queued',
        'metadata'     => json_encode(['cron_run_id' => $runId]),
    ]);

    // Enqueue in outbox
    DB::insert('outbox', [
        'tenant_id'     => $tenantId,
        'agent_id'      => $agent['id'],
        'contact_id'    => $contactId,
        'thread_id'     => $threadId,
        'message_id'    => $msgId,
        'phone'         => $phone,
        'content'       => $content,
        'message_type'  => $actionType === 'send_template' ? 'template' : 'text',
        'template_name' => $cron['template_name'] ?? null,
        'template_vars' => $cron['template_vars'] ?? null,
        'status'        => 'pending',
    ]);

    DB::update('threads', ['last_message_at' => date('Y-m-d H:i:s')], ['id' => $threadId]);
}

function updateNextRun(array $cron, DateTimeImmutable $now): void
{
    $next = calculateNextRun($cron['schedule'], $now);

    DB::query(
        'UPDATE cron_jobs SET last_run_at = NOW(), next_run_at = ? WHERE id = ?',
        [$next ? $next->format('Y-m-d H:i:s') : null, $cron['id']]
    );
}

/**
 * Very basic cron expression parser.
 * Supports standard 5-field expressions.
 */
function calculateNextRun(string $expression, DateTimeImmutable $from): ?DateTimeImmutable
{
    // Simple approach: add 1 minute and check forward up to 366 days
    $parts = explode(' ', trim($expression));
    if (count($parts) !== 5) return null;

    [$min, $hour, $dom, $month, $dow] = $parts;

    $candidate = $from->modify('+1 minute')->setTime(
        (int)($hour === '*' ? $from->format('H') : $hour),
        (int)($min  === '*' ? 0 : $min),
        0
    );

    // If hour is *, start from next minute
    if ($hour === '*') {
        $candidate = $from->modify('+1 minute');
    }

    for ($i = 0; $i < 1440 * 366; $i++) {
        if (matchesCronPart($candidate->format('i'), $min) &&
            matchesCronPart($candidate->format('G'), $hour) &&
            matchesCronPart($candidate->format('j'), $dom) &&
            matchesCronPart($candidate->format('n'), $month) &&
            matchesCronPart($candidate->format('w'), $dow)) {
            return $candidate;
        }
        $candidate = $candidate->modify('+1 minute');
    }

    return null;
}

function matchesCronPart(string $value, string $part): bool
{
    if ($part === '*') return true;

    if (str_contains($part, '/')) {
        [$range, $step] = explode('/', $part);
        if ($range === '*') {
            return (int)$value % (int)$step === 0;
        }
    }

    if (str_contains($part, '-')) {
        [$start, $end] = explode('-', $part);
        return (int)$value >= (int)$start && (int)$value <= (int)$end;
    }

    if (str_contains($part, ',')) {
        return in_array($value, explode(',', $part));
    }

    return (string)(int)$value === (string)(int)$part;
}
