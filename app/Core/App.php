<?php

declare(strict_types=1);

namespace App\Core;

/**
 * App — front controller / router.
 * Routes map to controllers in App\Controllers\*.
 */
class App
{
    private array $routes = [];

    public function get(string $pattern, callable|array $handler): void
    {
        $this->routes[] = ['GET', $pattern, $handler];
    }

    public function post(string $pattern, callable|array $handler): void
    {
        $this->routes[] = ['POST', $pattern, $handler];
    }

    public function any(string $pattern, callable|array $handler): void
    {
        $this->routes[] = ['ANY', $pattern, $handler];
    }

    public function run(): void
    {
        $method = Request::method();
        $path   = Request::path();

        foreach ($this->routes as [$routeMethod, $pattern, $handler]) {
            if ($routeMethod !== 'ANY' && $routeMethod !== $method) {
                continue;
            }

            $regex  = $this->patternToRegex($pattern);
            $params = [];

            if (preg_match($regex, $path, $matches)) {
                array_shift($matches);
                $params = $matches;

                if (is_array($handler)) {
                    [$class, $action] = $handler;
                    $controller = new $class();
                    $controller->$action(...$params);
                } else {
                    $handler(...$params);
                }
                return;
            }
        }

        Response::abort(404, 'Page Not Found');
    }

    private function patternToRegex(string $pattern): string
    {
        // Convert :param segments to capture groups
        $regex = preg_replace('#:([a-zA-Z_]+)#', '([^/]+)', $pattern);
        // Escape dots
        $regex = str_replace('.', '\.', $regex);
        return '#^' . $regex . '$#';
    }
}
