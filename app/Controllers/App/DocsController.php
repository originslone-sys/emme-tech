<?php

declare(strict_types=1);

namespace App\Controllers\App;

use App\Core\Auth;
use App\Core\CSRF;
use App\Core\DB;
use App\Core\Request;
use App\Core\Response;
use App\Core\Session;
use App\Lib\AuditLog;
use App\Lib\Chunker;

class DocsController
{
    public function index(): void
    {
        Auth::requireTenant();
        $tid  = Auth::tenantId();
        $agId = Request::get('agent_id');

        $where  = 'tenant_id = ?';
        $params = [$tid];
        if ($agId) {
            $where  .= ' AND agent_id = ?';
            $params[] = (int)$agId;
        }

        $docs   = DB::fetchAll(
            "SELECT d.*, a.name AS agent_name
             FROM kb_docs d
             LEFT JOIN agents a ON a.id = d.agent_id
             WHERE d.$where
             ORDER BY d.created_at DESC",
            $params
        );
        $agents = DB::fetchAll('SELECT id, name FROM agents WHERE tenant_id = ?', [$tid]);
        $plan   = Auth::tenantPlan();

        Response::view('app/docs/index', [
            'user'         => Auth::tenantUser(),
            'docs'         => $docs,
            'agents'       => $agents,
            'plan'         => $plan,
            'selected_agent' => $agId,
            'csrf'         => CSRF::field(),
        ]);
    }

    public function upload(): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        if (!Auth::canUploadDoc()) {
            Session::flash('error', 'Limite de documentos do plano atingido.');
            Response::redirect('/app/docs');
        }

        $tid    = Auth::tenantId();
        $user   = Auth::tenantUser();
        $agId   = (int)Request::post('agent_id', 0);

        // Validate agent belongs to tenant
        $agent = DB::fetchOne('SELECT id FROM agents WHERE id = ? AND tenant_id = ?', [$agId, $tid]);
        if (!$agent) {
            Session::flash('error', 'Agente inválido.');
            Response::redirect('/app/docs');
        }

        // File validation
        if (!isset($_FILES['document']) || $_FILES['document']['error'] !== UPLOAD_ERR_OK) {
            Session::flash('error', 'Erro no upload do arquivo.');
            Response::redirect('/app/docs');
        }

        $file = $_FILES['document'];
        $allowed = ['txt', 'md', 'pdf'];
        $maxSize = (int)env('UPLOAD_MAX_SIZE_MB', 10) * 1024 * 1024;

        $origName = basename($file['name']);
        $ext      = strtolower(pathinfo($origName, PATHINFO_EXTENSION));

        if (!in_array($ext, $allowed)) {
            Session::flash('error', 'Tipo de arquivo não permitido. Use: txt, md, pdf.');
            Response::redirect('/app/docs');
        }

        if ($file['size'] > $maxSize) {
            Session::flash('error', 'Arquivo muito grande. Máximo: ' . env('UPLOAD_MAX_SIZE_MB', 10) . 'MB.');
            Response::redirect('/app/docs');
        }

        // Verify MIME type
        $finfo    = finfo_open(FILEINFO_MIME_TYPE);
        $mimeType = finfo_file($finfo, $file['tmp_name']);
        finfo_close($finfo);

        $allowedMimes = ['text/plain', 'text/markdown', 'application/pdf', 'application/octet-stream'];
        if (!in_array($mimeType, $allowedMimes) && !str_starts_with($mimeType, 'text/')) {
            Session::flash('error', 'Tipo de arquivo não permitido.');
            Response::redirect('/app/docs');
        }

        // Save file
        $uploadDir = UPLOAD_DIR . "/$tid";
        if (!is_dir($uploadDir)) mkdir($uploadDir, 0775, true);

        $filename = uniqid('doc_', true) . '.' . $ext;
        $destPath = "$uploadDir/$filename";

        if (!move_uploaded_file($file['tmp_name'], $destPath)) {
            Session::flash('error', 'Falha ao salvar arquivo.');
            Response::redirect('/app/docs');
        }

        $docId = DB::insert('kb_docs', [
            'tenant_id'     => $tid,
            'agent_id'      => $agId,
            'filename'      => $filename,
            'original_name' => $origName,
            'file_type'     => $ext,
            'file_size'     => $file['size'],
            'status'        => 'pending',
        ]);

        // Process immediately (or enqueue job)
        try {
            Chunker::processDoc((int)$docId);
            Session::flash('success', 'Documento enviado e processado com sucesso!');
        } catch (\Throwable $e) {
            Session::flash('error', 'Arquivo salvo, mas erro no processamento: ' . $e->getMessage());
        }

        AuditLog::tenant($user['id'], $tid, 'doc.uploaded', 'kb_docs', (int)$docId);
        Response::redirect('/app/docs');
    }

    public function reprocess(string $id): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid   = Auth::tenantId();
        $docId = (int)$id;
        $doc   = DB::fetchOne('SELECT * FROM kb_docs WHERE id = ? AND tenant_id = ?', [$docId, $tid]);
        if (!$doc) Response::abort(404);

        try {
            Chunker::processDoc($docId);
            Session::flash('success', 'Documento reprocessado!');
        } catch (\Throwable $e) {
            Session::flash('error', 'Erro ao reprocessar: ' . $e->getMessage());
        }

        Response::redirect('/app/docs');
    }

    public function destroy(string $id): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid   = Auth::tenantId();
        $user  = Auth::tenantUser();
        $docId = (int)$id;
        $doc   = DB::fetchOne('SELECT * FROM kb_docs WHERE id = ? AND tenant_id = ?', [$docId, $tid]);
        if (!$doc) Response::abort(404);

        // Remove file
        $filePath = UPLOAD_DIR . "/$tid/" . $doc['filename'];
        if (file_exists($filePath)) {
            unlink($filePath);
        }

        DB::delete('kb_docs', ['id' => $docId]);
        AuditLog::tenant($user['id'], $tid, 'doc.deleted', 'kb_docs', $docId);

        Session::flash('success', 'Documento removido.');
        Response::redirect('/app/docs');
    }
}
