<?php

declare(strict_types=1);

namespace App\Lib;

use App\Core\DB;

/**
 * Chunker — splits uploaded documents into chunks and stores in kb_chunks.
 */
class Chunker
{
    private const CHUNK_SIZE    = 800;  // ~tokens approximation (chars / 4)
    private const CHUNK_OVERLAP = 100;

    /**
     * Process a document: read file, split into chunks, store in DB.
     */
    public static function processDoc(int $docId): void
    {
        $doc = DB::fetchOne('SELECT * FROM kb_docs WHERE id = ?', [$docId]);
        if (!$doc) {
            throw new \RuntimeException("Doc $docId not found.");
        }

        DB::query('UPDATE kb_docs SET status = ? WHERE id = ?', ['processing', $docId]);

        $path = UPLOAD_DIR . '/' . $doc['tenant_id'] . '/' . $doc['filename'];
        if (!file_exists($path)) {
            DB::query('UPDATE kb_docs SET status = ?, error = ? WHERE id = ?', ['error', 'File not found', $docId]);
            throw new \RuntimeException("File not found: $path");
        }

        $text = self::extractText($path, $doc['file_type']);
        $text = self::normalizeWhitespace($text);

        // Delete old chunks
        DB::query('DELETE FROM kb_chunks WHERE doc_id = ?', [$docId]);

        $chunks = self::splitIntoChunks($text, $doc['original_name']);
        $count  = 0;

        foreach ($chunks as $idx => $chunk) {
            DB::insert('kb_chunks', [
                'tenant_id'   => $doc['tenant_id'],
                'agent_id'    => $doc['agent_id'],
                'doc_id'      => $docId,
                'chunk_index' => $idx,
                'title'       => $chunk['title'],
                'chunk_text'  => $chunk['text'],
                'token_count' => (int)ceil(mb_strlen($chunk['text']) / 4),
            ]);
            $count++;
        }

        DB::query(
            'UPDATE kb_docs SET status = ?, chunk_count = ?, updated_at = NOW() WHERE id = ?',
            ['ready', $count, $docId]
        );
    }

    /**
     * Extract plain text from file.
     */
    private static function extractText(string $path, string $type): string
    {
        return match (strtolower($type)) {
            'pdf'   => self::extractPdf($path),
            default => file_get_contents($path) ?: '',
        };
    }

    /**
     * Basic PDF text extraction without external libs.
     */
    private static function extractPdf(string $path): string
    {
        $content = file_get_contents($path) ?: '';
        // Extract text streams from PDF (very basic, works for simple PDFs)
        preg_match_all('/stream(.*?)endstream/s', $content, $matches);
        $text = '';
        foreach ($matches[1] as $stream) {
            $decoded = @gzuncompress(trim($stream));
            if ($decoded !== false) {
                $text .= $decoded . "\n";
            } else {
                // Raw stream — try to extract readable text
                $text .= preg_replace('/[^\x20-\x7E\n\r\t]/', ' ', $stream) . "\n";
            }
        }
        return $text ?: $content;
    }

    /**
     * Split text into overlapping chunks.
     */
    private static function splitIntoChunks(string $text, string $docName): array
    {
        $chunkSizeChars    = self::CHUNK_SIZE * 4;
        $overlapChars      = self::CHUNK_OVERLAP * 4;
        $chunks            = [];
        $len               = mb_strlen($text);
        $pos               = 0;
        $idx               = 0;

        while ($pos < $len) {
            $end  = min($pos + $chunkSizeChars, $len);
            $part = mb_substr($text, $pos, $end - $pos);

            // Try to break at sentence boundary
            if ($end < $len) {
                $breakAt = mb_strrpos($part, '. ');
                if ($breakAt !== false && $breakAt > $chunkSizeChars / 2) {
                    $part = mb_substr($part, 0, $breakAt + 1);
                }
            }

            $part = trim($part);
            if ($part !== '') {
                // Title: first 80 chars of the chunk or doc name
                $firstLine = trim(explode("\n", $part)[0]);
                $title     = mb_strlen($firstLine) > 5 ? mb_substr($firstLine, 0, 80) : $docName;

                $chunks[] = ['title' => $title, 'text' => $part];
                $idx++;
            }

            $pos += mb_strlen($part) - $overlapChars;
            if ($pos >= $len) break;
        }

        return $chunks;
    }

    private static function normalizeWhitespace(string $text): string
    {
        // Normalize line endings and collapse excessive blank lines
        $text = str_replace("\r\n", "\n", $text);
        $text = preg_replace('/\n{3,}/', "\n\n", $text);
        return trim($text);
    }
}
