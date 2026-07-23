<?php
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    exit;
}

header('Content-Type: application/json');

// Load PHPMailer
require_once __DIR__ . '/phpmailer/Exception.php';
require_once __DIR__ . '/phpmailer/PHPMailer.php';
require_once __DIR__ . '/phpmailer/SMTP.php';

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

// Sanitize helper
function clean($val) {
    return htmlspecialchars(strip_tags(trim($val)), ENT_QUOTES, 'UTF-8');
}

// Honeypot spam check
if (!empty($_POST['website_url'])) {
    echo json_encode(['ok' => true]);
    exit;
}

// Collect and sanitize fields
$firstName = clean($_POST['firstName'] ?? '');
$lastName  = clean($_POST['lastName']  ?? '');
$email     = filter_var(trim($_POST['email'] ?? ''), FILTER_SANITIZE_EMAIL);
$phone     = clean($_POST['phone']     ?? '');
$org       = clean($_POST['org']       ?? '');
$interest  = clean($_POST['interest']  ?? '');
$message   = clean($_POST['message']   ?? '');

// Basic validation
if (empty($firstName) || empty($lastName) || empty($email) || empty($message)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Required fields missing.']);
    exit;
}

if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Invalid email address.']);
    exit;
}

// ── SMTP CONFIG ──────────────────────────────────────────
$smtpUser     = 'Info@lionsyssolutions.com';
$smtpPassword = 'YOUR_EMAIL_PASSWORD_HERE'; // ← replace this
$smtpHost     = 'smtp.hostinger.com';
$smtpPort     = 587;
// ─────────────────────────────────────────────────────────

try {
    $mail = new PHPMailer(true);
    $mail->isSMTP();
    $mail->Host       = $smtpHost;
    $mail->SMTPAuth   = true;
    $mail->Username   = $smtpUser;
    $mail->Password   = $smtpPassword;
    $mail->SMTPSecure = PHPMailer::ENCRYPTION_STARTTLS;
    $mail->Port       = $smtpPort;

    $mail->setFrom('Info@lionsyssolutions.com', 'Lionsys Solutions Website');
    $mail->addAddress('Info@lionsyssolutions.com', 'Lionsys Solutions');
    $mail->addReplyTo($email, "{$firstName} {$lastName}");

    $mail->Subject = 'New Contact Form Submission — Lionsys Solutions';
    $mail->Body =
        "New contact form submission from lionsyssolutions.com\n" .
        "=============================================================\n\n" .
        "Name:             {$firstName} {$lastName}\n" .
        "Email:            {$email}\n" .
        "Phone:            " . ($phone ?: '—') . "\n" .
        "Organization:     " . ($org ?: '—') . "\n" .
        "Area of Interest: " . ($interest ?: '—') . "\n\n" .
        "Message:\n{$message}\n\n" .
        "=============================================================\n" .
        "Sent from lionsyssolutions.com contact form\n";

    $mail->send();
    echo json_encode(['ok' => true]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Mail error.']);
}
