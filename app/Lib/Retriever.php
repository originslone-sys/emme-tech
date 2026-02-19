<?php

declare(strict_types=1);

namespace App\Lib;

use App\Core\DB;

/**
 * Retriever — FULLTEXT search over kb_chunks for RAG context injection.
 */
class Retriever
{
    /**
     * Search for top-K relevant chunks for a query.
     *
     * @param int    $agentId
     * @param string $query
     * @param int    $topK
     * @return array Array of ['title', 'chunk_text', 'score']
     */
    public static function retrieve(int $agentId, string $query, int $topK = 3): array
    {
        if (trim($query) === '') {
            return [];
        }

        // Sanitize query for FULLTEXT (remove special chars)
        $clean = self::sanitizeQuery($query);

        if ($clean === '') {
            return [];
        }

        try {
            // Boolean mode FULLTEXT search
            $rows = DB::fetchAll(
                'SELECT title, chunk_text,
                        MATCH(title, chunk_text) AGAINST (? IN BOOLEAN MODE) AS score
                 FROM kb_chunks
                 WHERE agent_id = ?
                   AND MATCH(title, chunk_text) AGAINST (? IN BOOLEAN MODE)
                 ORDER BY score DESC
                 LIMIT ?',
                [$clean, $agentId, $clean, $topK]
            );
        } catch (\Throwable $e) {
            // Fallback to LIKE search if FULLTEXT fails
            Logger::warning('FULLTEXT search failed, falling back to LIKE', ['error' => $e->getMessage()]);
            $like = '%' . implode('%', array_slice(explode(' ', $query), 0, 3)) . '%';
            $rows = DB::fetchAll(
                'SELECT title, chunk_text, 1.0 AS score
                 FROM kb_chunks
                 WHERE agent_id = ?
                   AND (title LIKE ? OR chunk_text LIKE ?)
                 LIMIT ?',
                [$agentId, $like, $like, $topK]
            );
        }

        return $rows;
    }

    /**
     * Build the "Knowledge Context" string to inject into the system prompt.
     */
    public static function buildContext(int $agentId, string $query, int $topK = 3): string
    {
        $chunks = self::retrieve($agentId, $query, $topK);

        if (empty($chunks)) {
            return '';
        }

        $ctx = "=== Knowledge Context ===\n";
        foreach ($chunks as $i => $chunk) {
            $ctx .= "\n[" . ($i + 1) . "] " . ($chunk['title'] ?? '') . "\n";
            $ctx .= trim($chunk['chunk_text']) . "\n";
        }
        $ctx .= "=========================\n";

        return $ctx;
    }

    /**
     * Sanitize query for MySQL FULLTEXT boolean mode.
     */
    private static function sanitizeQuery(string $query): string
    {
        // Remove special FULLTEXT operators except spaces
        $clean = preg_replace('/[+\-><\(\)~*\"@]+/', ' ', $query);
        $clean = preg_replace('/\s+/', ' ', $clean);
        $clean = trim($clean);

        if ($clean === '') return '';

        // Wrap each word with + for AND search
        $words = array_filter(explode(' ', $clean), fn($w) => mb_strlen($w) >= 3);

        if (empty($words)) return $clean;

        return implode(' ', array_map(fn($w) => '+' . $w, array_slice($words, 0, 10)));
    }
}
