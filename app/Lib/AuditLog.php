<?php

declare(strict_types=1);

namespace App\Lib;

use App\Core\DB;
use App\Core\Request;

/**
 * AuditLog — records actor actions for compliance/traceability.
 */
class AuditLog
{
    public static function record(
        string $actorType,
        int|null $actorId,
        int|null $tenantId,
        string $action,
        string|null $resourceType = null,
        int|null $resourceId = null,
        mixed $oldValue = null,
        mixed $newValue = null
    ): void {
        try {
            DB::insert('audit_log', [
                'actor_type'    => $actorType,
                'actor_id'      => $actorId,
                'tenant_id'     => $tenantId,
                'action'        => $action,
                'resource_type' => $resourceType,
                'resource_id'   => $resourceId,
                'old_value'     => $oldValue !== null ? json_encode($oldValue) : null,
                'new_value'     => $newValue !== null ? json_encode($newValue) : null,
                'ip'            => Request::ip(),
                'user_agent'    => substr(Request::userAgent(), 0, 255),
            ]);
        } catch (\Throwable $e) {
            Logger::error('AuditLog::record failed', ['error' => $e->getMessage()]);
        }
    }

    public static function admin(int $adminId, string $action, string $resource = null, int $resourceId = null, mixed $old = null, mixed $new = null): void
    {
        self::record('admin', $adminId, null, $action, $resource, $resourceId, $old, $new);
    }

    public static function tenant(int $userId, int $tenantId, string $action, string $resource = null, int $resourceId = null, mixed $old = null, mixed $new = null): void
    {
        self::record('tenant', $userId, $tenantId, $action, $resource, $resourceId, $old, $new);
    }

    public static function system(string $action, int $tenantId = null, string $resource = null, int $resourceId = null): void
    {
        self::record('system', null, $tenantId, $action, $resource, $resourceId);
    }
}
