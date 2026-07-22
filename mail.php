<?php
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    exit;
}

header('Content-Type: application/json');

// Sanitize helper
function clean($val) {
    return htmlspecialchars(strip_tags(trim($val)), ENT_QUOTES, 'UTF-8');
}

// Honeypot spam check (hidden field — bots fill it, humans don't)
if (!empty($_POST['website_url'])) {
    echo json_encode(['ok' => true]); // pretend success to fool bots
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

$to      = 'Info@lionsyssolutions.com';
$subject = 'New Contact Form Submission — Lionsys Solutions';

$body  = "You have a new contact form submission from lionsyssolutions.com\n";
$body .= "=============================================================\n\n";
$body .= "Name:             {$firstName} {$lastName}\n";
$body .= "Email:            {$email}\n";
$body .= "Phone:            " . ($phone ?: '—') . "\n";
$body .= "Organization:     " . ($org ?: '—') . "\n";
$body .= "Area of Interest: " . ($interest ?: '—') . "\n\n";
$body .= "Message:\n{$message}\n\n";
$body .= "=============================================================\n";
$body .= "Sent from lionsyssolutions.com contact form\n";

// FROM must be a real mailbox on Hostinger to avoid being blocked
$headers  = "From: Info@lionsyssolutions.com\r\n";
$headers .= "Reply-To: {$email}\r\n";
$headers .= "X-Mailer: PHP/" . phpversion();

$sent = mail($to, $subject, $body, $headers);

if ($sent) {
    echo json_encode(['ok' => true]);
} else {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Mail server error.']);
}
