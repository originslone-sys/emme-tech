<?php

declare(strict_types=1);

namespace App\Core;

use PDO;
use PDOException;
use PDOStatement;
use RuntimeException;

/**
 * DB — PDO singleton wrapper with helpers.
 */
class DB
{
    private static ?PDO $pdo = null;

    public static function connect(): PDO
    {
        if (self::$pdo !== null) {
            return self::$pdo;
        }

        $host    = env('DB_HOST', '127.0.0.1');
        $port    = env('DB_PORT', '3306');
        $dbname  = env('DB_NAME', '');
        $user    = env('DB_USER', '');
        $pass    = env('DB_PASS', '');
        $charset = env('DB_CHARSET', 'utf8mb4');

        $dsn = "mysql:host=$host;port=$port;dbname=$dbname;charset=$charset";

        try {
            self::$pdo = new PDO($dsn, $user, $pass, [
                PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES   => false,
                PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES $charset COLLATE {$charset}_unicode_ci",
            ]);
        } catch (PDOException $e) {
            throw new RuntimeException('Database connection failed: ' . $e->getMessage());
        }

        return self::$pdo;
    }

    public static function pdo(): PDO
    {
        return self::connect();
    }

    /**
     * Execute a query and return the PDOStatement.
     */
    public static function query(string $sql, array $params = []): PDOStatement
    {
        $stmt = self::pdo()->prepare($sql);
        $stmt->execute($params);
        return $stmt;
    }

    /**
     * Fetch all rows.
     */
    public static function fetchAll(string $sql, array $params = []): array
    {
        return self::query($sql, $params)->fetchAll();
    }

    /**
     * Fetch single row.
     */
    public static function fetchOne(string $sql, array $params = []): array|false
    {
        return self::query($sql, $params)->fetch();
    }

    /**
     * Fetch single column value.
     */
    public static function fetchColumn(string $sql, array $params = []): mixed
    {
        return self::query($sql, $params)->fetchColumn();
    }

    /**
     * Insert a row and return last insert ID.
     */
    public static function insert(string $table, array $data): int|string
    {
        $cols   = array_keys($data);
        $places = array_map(fn($c) => ":$c", $cols);
        $sql    = sprintf(
            'INSERT INTO `%s` (%s) VALUES (%s)',
            $table,
            implode(', ', array_map(fn($c) => "`$c`", $cols)),
            implode(', ', $places)
        );
        self::query($sql, $data);
        return self::pdo()->lastInsertId();
    }

    /**
     * Update rows and return affected count.
     */
    public static function update(string $table, array $data, array $where): int
    {
        $sets = implode(', ', array_map(fn($c) => "`$c` = :set_$c", array_keys($data)));
        $conds = implode(' AND ', array_map(fn($c) => "`$c` = :wh_$c", array_keys($where)));

        $params = [];
        foreach ($data  as $k => $v) $params["set_$k"] = $v;
        foreach ($where as $k => $v) $params["wh_$k"]  = $v;

        $sql = "UPDATE `$table` SET $sets WHERE $conds";
        $stmt = self::query($sql, $params);
        return $stmt->rowCount();
    }

    /**
     * Delete rows and return affected count.
     */
    public static function delete(string $table, array $where): int
    {
        $conds = implode(' AND ', array_map(fn($c) => "`$c` = :$c", array_keys($where)));
        $sql   = "DELETE FROM `$table` WHERE $conds";
        return self::query($sql, $where)->rowCount();
    }

    public static function beginTransaction(): void
    {
        self::pdo()->beginTransaction();
    }

    public static function commit(): void
    {
        self::pdo()->commit();
    }

    public static function rollBack(): void
    {
        if (self::pdo()->inTransaction()) {
            self::pdo()->rollBack();
        }
    }

    public static function lastInsertId(): string
    {
        return self::pdo()->lastInsertId();
    }
}
