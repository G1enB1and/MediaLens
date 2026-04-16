<?php
declare(strict_types=1);

/*
 * MediaLens debugging-log upload endpoint.
 *
 * Deployment model:
 * - Put this file under your HTTPS subdomain, for example:
 *   https://medialens.glenbland.com/api/submit-debug-log.php
 * - Set SUPPORT_EMAIL and SHARED_TOKEN below before deploying.
 * - Uploaded bundles are stored outside the web root by default.
 */

const SUPPORT_EMAIL = 'you@example.com';
const SHARED_TOKEN = 'replace-with-a-long-random-secret';
const MAX_UPLOAD_BYTES = 26214400; // 25 MiB

function respond(int $status, array $payload): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($payload, JSON_UNESCAPED_SLASHES);
    exit;
}

function bearer_token(): string
{
    $header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    if ($header === '' && function_exists('apache_request_headers')) {
        $headers = apache_request_headers();
        $header = $headers['Authorization'] ?? $headers['authorization'] ?? '';
    }
    if (stripos($header, 'Bearer ') !== 0) {
        return '';
    }
    return trim(substr($header, 7));
}

function safe_text(string $value, int $max): string
{
    $value = trim(str_replace(["\r", "\0"], '', $value));
    if (strlen($value) > $max) {
        $value = substr($value, 0, $max);
    }
    return $value;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond(405, ['ok' => false, 'error' => 'POST required']);
}

if (SHARED_TOKEN === 'replace-with-a-long-random-secret') {
    respond(500, ['ok' => false, 'error' => 'Upload endpoint is not configured']);
}

$token = bearer_token();
if ($token === '' || !hash_equals(SHARED_TOKEN, $token)) {
    respond(401, ['ok' => false, 'error' => 'Unauthorized']);
}

if (empty($_FILES['debug_bundle']) || !is_array($_FILES['debug_bundle'])) {
    respond(400, ['ok' => false, 'error' => 'Missing debug_bundle upload']);
}

$file = $_FILES['debug_bundle'];
if (($file['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
    respond(400, ['ok' => false, 'error' => 'Upload failed', 'code' => $file['error'] ?? null]);
}

$size = (int)($file['size'] ?? 0);
if ($size <= 0 || $size > MAX_UPLOAD_BYTES) {
    respond(413, ['ok' => false, 'error' => 'Upload size is not allowed']);
}

$originalName = (string)($file['name'] ?? '');
if (strtolower(pathinfo($originalName, PATHINFO_EXTENSION)) !== 'zip') {
    respond(400, ['ok' => false, 'error' => 'Only zip bundles are accepted']);
}

$storageRoot = dirname(__DIR__, 2) . DIRECTORY_SEPARATOR . 'medialens-debug-uploads';
$bundleDir = $storageRoot . DIRECTORY_SEPARATOR . 'bundles';
if (!is_dir($bundleDir) && !mkdir($bundleDir, 0700, true)) {
    respond(500, ['ok' => false, 'error' => 'Could not create upload directory']);
}

$reportId = gmdate('Ymd-His') . '-' . bin2hex(random_bytes(8));
$targetPath = $bundleDir . DIRECTORY_SEPARATOR . $reportId . '.zip';
if (!move_uploaded_file((string)$file['tmp_name'], $targetPath)) {
    respond(500, ['ok' => false, 'error' => 'Could not store upload']);
}
chmod($targetPath, 0600);

$metadata = [
    'report_id' => $reportId,
    'received_utc' => gmdate('c'),
    'remote_addr' => $_SERVER['REMOTE_ADDR'] ?? '',
    'user_agent' => $_SERVER['HTTP_USER_AGENT'] ?? '',
    'app_version' => safe_text((string)($_POST['app_version'] ?? ''), 80),
    'contact' => safe_text((string)($_POST['contact'] ?? ''), 200),
    'note' => safe_text((string)($_POST['note'] ?? ''), 4000),
    'bundle_bytes' => $size,
    'stored_as' => basename($targetPath),
];

$indexPath = $storageRoot . DIRECTORY_SEPARATOR . 'index.jsonl';
file_put_contents($indexPath, json_encode($metadata, JSON_UNESCAPED_SLASHES) . PHP_EOL, FILE_APPEND | LOCK_EX);
@chmod($indexPath, 0600);

if (SUPPORT_EMAIL !== 'you@example.com') {
    $subject = 'MediaLens debugging log: ' . $reportId;
    $body = "A MediaLens debugging log was submitted.\n\n"
        . "Report ID: {$reportId}\n"
        . "Version: {$metadata['app_version']}\n"
        . "Bundle bytes: {$size}\n"
        . "Contact: {$metadata['contact']}\n\n"
        . "Note:\n{$metadata['note']}\n";
    @mail(SUPPORT_EMAIL, $subject, $body, 'From: MediaLens <no-reply@' . ($_SERVER['HTTP_HOST'] ?? 'localhost') . '>');
}

respond(200, ['ok' => true, 'message' => "Debugging logs submitted. Report ID: {$reportId}", 'report_id' => $reportId]);

