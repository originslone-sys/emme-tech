<?php
require_once __DIR__ . '/../config.php';

function registerUser($name, $email, $password, $pdo) {
    $name = sanitize($name);
    $email = sanitize($email);

    // Validate
    if (empty($name) || empty($email) || empty($password)) {
        return ['success' => false, 'message' => 'Todos os campos são obrigatórios.'];
    }

    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        return ['success' => false, 'message' => 'E-mail inválido.'];
    }

    if (strlen($password) < 6) {
        return ['success' => false, 'message' => 'A senha deve ter no mínimo 6 caracteres.'];
    }

    // Check if email exists
    $stmt = $pdo->prepare("SELECT id FROM users WHERE email = ?");
    $stmt->execute([$email]);
    if ($stmt->fetch()) {
        return ['success' => false, 'message' => 'Este e-mail já está cadastrado.'];
    }

    // Insert user
    $hashedPassword = password_hash($password, PASSWORD_DEFAULT);
    $stmt = $pdo->prepare("INSERT INTO users (name, email, password, email_verified_at) VALUES (?, ?, ?, NOW())");
    $stmt->execute([$name, $email, $hashedPassword]);

    $userId = $pdo->lastInsertId();

    // Create welcome notification
    $stmt = $pdo->prepare("INSERT INTO notifications (user_id, title, message, type) VALUES (?, ?, ?, 'success')");
    $stmt->execute([
        $userId,
        'Bem-vindo ao PagueContas!',
        'Sua conta foi criada com sucesso. Recarregue seu saldo e comece a pagar contas com 5% de cashback!'
    ]);

    return ['success' => true, 'message' => 'Conta criada com sucesso!', 'user_id' => $userId];
}

function loginUser($email, $password, $pdo) {
    $email = sanitize($email);

    if (empty($email) || empty($password)) {
        return ['success' => false, 'message' => 'E-mail e senha são obrigatórios.'];
    }

    $stmt = $pdo->prepare("SELECT * FROM users WHERE email = ?");
    $stmt->execute([$email]);
    $user = $stmt->fetch();

    if (!$user || !password_verify($password, $user['password'])) {
        return ['success' => false, 'message' => 'E-mail ou senha incorretos.'];
    }

    if ($user['status'] !== 'active') {
        return ['success' => false, 'message' => 'Sua conta está bloqueada. Entre em contato com o suporte.'];
    }

    // Set session
    $_SESSION['user_id'] = $user['id'];
    $_SESSION['user_name'] = $user['name'];
    $_SESSION['user_email'] = $user['email'];
    $_SESSION['is_admin'] = (bool)$user['is_admin'];

    return ['success' => true, 'message' => 'Login realizado com sucesso!', 'is_admin' => (bool)$user['is_admin']];
}

function logoutUser() {
    session_destroy();
    redirect('login.php');
}

function getCurrentUser($pdo) {
    if (!isLoggedIn()) return null;

    $stmt = $pdo->prepare("SELECT id, name, email, cpf, phone, balance, cashback_balance, is_admin, status, avatar, created_at FROM users WHERE id = ?");
    $stmt->execute([$_SESSION['user_id']]);
    return $stmt->fetch();
}

function requireLogin() {
    if (!isLoggedIn()) {
        redirect('login.php');
    }
}

function requireAdmin() {
    if (!isLoggedIn() || !isAdmin()) {
        redirect('login.php');
    }
}
