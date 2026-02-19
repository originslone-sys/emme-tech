<?php

declare(strict_types=1);

namespace App\Controllers\App;

use App\Core\Auth;
use App\Core\DB;
use App\Core\Request;
use App\Core\Response;

class ThreadsController
{
    public function index(): void
    {
        Auth::requireTenant();
        $tid    = Auth::tenantId();
        $page   = max(1, (int)Request::get('page', 1));
        $perPage = 30;
        $offset = ($page - 1) * $perPage;

        $agentId   = Request::get('agent_id', '');
        $contactQ  = Request::get('contact', '');
        $status    = Request::get('status', '');
        $dateFrom  = Request::get('date_from', '');
        $dateTo    = Request::get('date_to', '');

        $where  = ['th.tenant_id = ?'];
        $params = [$tid];

        if ($agentId) {
            $where[]  = 'th.agent_id = ?';
            $params[] = (int)$agentId;
        }
        if ($contactQ) {
            $where[]  = '(c.phone LIKE ? OR c.name LIKE ?)';
            $params[] = "%$contactQ%";
            $params[] = "%$contactQ%";
        }
        if ($status) {
            $where[]  = 'th.status = ?';
            $params[] = $status;
        }
        if ($dateFrom) {
            $where[]  = 'th.last_message_at >= ?';
            $params[] = $dateFrom . ' 00:00:00';
        }
        if ($dateTo) {
            $where[]  = 'th.last_message_at <= ?';
            $params[] = $dateTo . ' 23:59:59';
        }

        $whereStr = implode(' AND ', $where);

        $total = (int)DB::fetchColumn(
            "SELECT COUNT(*) FROM threads th
             LEFT JOIN contacts c ON c.id = th.contact_id
             WHERE $whereStr",
            $params
        );

        $threads = DB::fetchAll(
            "SELECT th.*, a.name AS agent_name, c.phone AS contact_phone, c.name AS contact_name,
                    (SELECT COUNT(*) FROM messages WHERE thread_id = th.id) AS msg_count,
                    (SELECT content FROM messages WHERE thread_id = th.id ORDER BY id DESC LIMIT 1) AS last_message
             FROM threads th
             LEFT JOIN agents a ON a.id = th.agent_id
             LEFT JOIN contacts c ON c.id = th.contact_id
             WHERE $whereStr
             ORDER BY th.last_message_at DESC
             LIMIT ? OFFSET ?",
            [...$params, $perPage, $offset]
        );

        $agents = DB::fetchAll('SELECT id, name FROM agents WHERE tenant_id = ?', [$tid]);

        Response::view('app/threads/index', [
            'user'      => Auth::tenantUser(),
            'threads'   => $threads,
            'agents'    => $agents,
            'total'     => $total,
            'page'      => $page,
            'perPage'   => $perPage,
            'agentId'   => $agentId,
            'contactQ'  => $contactQ,
            'status'    => $status,
            'dateFrom'  => $dateFrom,
            'dateTo'    => $dateTo,
        ]);
    }

    public function view(): void
    {
        Auth::requireTenant();
        $tid      = Auth::tenantId();
        $threadId = (int)Request::get('id', 0);

        $thread = DB::fetchOne(
            'SELECT th.*, a.name AS agent_name, c.phone AS contact_phone, c.name AS contact_name, c.opt_out, c.handoff
             FROM threads th
             LEFT JOIN agents a ON a.id = th.agent_id
             LEFT JOIN contacts c ON c.id = th.contact_id
             WHERE th.id = ? AND th.tenant_id = ?',
            [$threadId, $tid]
        );
        if (!$thread) Response::abort(404);

        $messages = DB::fetchAll(
            'SELECT * FROM messages WHERE thread_id = ? ORDER BY created_at ASC',
            [$threadId]
        );

        Response::view('app/threads/view', [
            'user'     => Auth::tenantUser(),
            'thread'   => $thread,
            'messages' => $messages,
        ]);
    }
}
