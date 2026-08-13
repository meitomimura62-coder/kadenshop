<?php

declare(strict_types=1);

require __DIR__ . '/../src/Db.php';

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
$path = rtrim($path, '/');
if ($path === '') {
    $path = '/';
}

function jsonResponse($data, int $status = 200): void
{
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function errorResponse(string $message, int $status = 400, array $details = []): void
{
    $payload = ['error' => $message];
    if ($details !== []) {
        $payload['details'] = $details;
    }
    jsonResponse($payload, $status);
}

function readJsonBody(): array
{
    $raw = file_get_contents('php://input');
    if ($raw === false || trim($raw) === '') {
        return [];
    }
    $data = json_decode($raw, true);
    if (!is_array($data)) {
        errorResponse('Invalid JSON body', 400);
    }
    return $data;
}

function normalizeLabel(?string $label): ?string
{
    if ($label === null) {
        return null;
    }
    $label = strtoupper(trim($label));
    return $label;
}

function ensureLabel(?string $label): string
{
    $label = normalizeLabel($label);
    if (!in_array($label, ['A', 'B', 'C', 'D'], true)) {
        errorResponse('Label must be one of A, B, C, D', 422);
    }
    return $label;
}

function toInt($value, int $default = 0): int
{
    if ($value === null || $value === '') {
        return $default;
    }
    return (int)$value;
}

function fetchChoices(PDO $pdo, array $questionIds): array
{
    if ($questionIds === []) {
        return [];
    }

    $placeholders = implode(',', array_fill(0, count($questionIds), '?'));
    $stmt = $pdo->prepare("SELECT question_id, choice_label, choice_text FROM question_choices WHERE question_id IN ($placeholders) ORDER BY choice_label");
    $stmt->execute($questionIds);
    $rows = $stmt->fetchAll();

    $grouped = [];
    foreach ($rows as $row) {
        $qid = (int)$row['question_id'];
        $grouped[$qid][] = [
            'choice_label' => $row['choice_label'],
            'choice_text' => $row['choice_text'],
        ];
    }

    return $grouped;
}

function validateChoices(array $choices): array
{
    $seen = [];
    $normalized = [];

    foreach ($choices as $choice) {
        if (!is_array($choice)) {
            errorResponse('Choices must be an array of objects', 422);
        }
        $label = ensureLabel($choice['choice_label'] ?? null);
        $text = trim((string)($choice['choice_text'] ?? ''));
        if ($text === '') {
            errorResponse('choice_text is required', 422);
        }
        if (isset($seen[$label])) {
            errorResponse('Duplicate choice_label', 422);
        }
        $seen[$label] = true;
        $normalized[] = [
            'choice_label' => $label,
            'choice_text' => $text,
        ];
    }

    return $normalized;
}

try {
    $pdo = Db::pdo();
} catch (Throwable $e) {
    errorResponse('Database connection failed', 500);
}

if ($path === '/health' && $method === 'GET') {
    jsonResponse(['status' => 'ok']);
}

if ($path === '/questions' && $method === 'GET') {
    $where = [];
    $params = [];

    if (isset($_GET['domain_name'])) {
        $where[] = 'domain_name = ?';
        $params[] = $_GET['domain_name'];
    }
    if (isset($_GET['topic_name'])) {
        $where[] = 'topic_name = ?';
        $params[] = $_GET['topic_name'];
    }
    if (isset($_GET['is_active'])) {
        $where[] = 'is_active = ?';
        $params[] = (int)$_GET['is_active'];
    }

    $limit = max(1, min(200, toInt($_GET['limit'] ?? 50, 50)));
    $offset = max(0, toInt($_GET['offset'] ?? 0, 0));

    $sql = 'SELECT * FROM questions';
    if ($where !== []) {
        $sql .= ' WHERE ' . implode(' AND ', $where);
    }
    $sql .= ' ORDER BY question_id DESC LIMIT ? OFFSET ?';
    $params[] = $limit;
    $params[] = $offset;

    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $rows = $stmt->fetchAll();

    $includeChoices = ($_GET['include'] ?? '') === 'choices';
    if ($includeChoices && $rows !== []) {
        $ids = array_map(static fn($row) => (int)$row['question_id'], $rows);
        $choicesMap = fetchChoices($pdo, $ids);
        foreach ($rows as &$row) {
            $row['choices'] = $choicesMap[(int)$row['question_id']] ?? [];
        }
        unset($row);
    }

    jsonResponse(['items' => $rows, 'limit' => $limit, 'offset' => $offset]);
}

if ($path === '/questions' && $method === 'POST') {
    $body = readJsonBody();

    $domain = trim((string)($body['domain_name'] ?? ''));
    $stem = trim((string)($body['stem'] ?? ''));
    $correctLabel = ensureLabel($body['correct_label'] ?? null);

    if ($domain === '' || $stem === '') {
        errorResponse('domain_name and stem are required', 422);
    }

    $choices = [];
    if (isset($body['choices'])) {
        if (!is_array($body['choices'])) {
            errorResponse('choices must be an array', 422);
        }
        $choices = validateChoices($body['choices']);
        $labels = array_column($choices, 'choice_label');
        if (!in_array($correctLabel, $labels, true)) {
            errorResponse('correct_label must match one of the choices', 422);
        }
    }

    $pdo->beginTransaction();
    try {
        $stmt = $pdo->prepare(
            'INSERT INTO questions (exam_name, domain_name, topic_name, title, stem, explanation, correct_label, difficulty, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
        );
        $stmt->execute([
            $body['exam_name'] ?? '基本情報技術者試験',
            $domain,
            $body['topic_name'] ?? null,
            $body['title'] ?? null,
            $stem,
            $body['explanation'] ?? null,
            $correctLabel,
            $body['difficulty'] ?? null,
            isset($body['is_active']) ? (int)$body['is_active'] : 1,
        ]);
        $questionId = (int)$pdo->lastInsertId();

        if ($choices !== []) {
            $stmt = $pdo->prepare('INSERT INTO question_choices (question_id, choice_label, choice_text) VALUES (?, ?, ?)');
            foreach ($choices as $choice) {
                $stmt->execute([$questionId, $choice['choice_label'], $choice['choice_text']]);
            }
        }

        $pdo->commit();
    } catch (Throwable $e) {
        $pdo->rollBack();
        errorResponse('Failed to create question', 500);
    }

    jsonResponse(['question_id' => $questionId], 201);
}

if (preg_match('#^/questions/(\d+)$#', $path, $matches)) {
    $questionId = (int)$matches[1];

    if ($method === 'GET') {
        $stmt = $pdo->prepare('SELECT * FROM questions WHERE question_id = ?');
        $stmt->execute([$questionId]);
        $row = $stmt->fetch();
        if (!$row) {
            errorResponse('Question not found', 404);
        }
        $choicesMap = fetchChoices($pdo, [$questionId]);
        $row['choices'] = $choicesMap[$questionId] ?? [];
        jsonResponse($row);
    }

    if ($method === 'PUT') {
        $body = readJsonBody();
        $fields = [];
        $params = [];

        $allowed = ['exam_name', 'domain_name', 'topic_name', 'title', 'stem', 'explanation', 'correct_label', 'difficulty', 'is_active'];
        foreach ($allowed as $key) {
            if (array_key_exists($key, $body)) {
                $value = $body[$key];
                if ($key === 'correct_label') {
                    $value = ensureLabel($value);
                }
                if ($key === 'domain_name' || $key === 'stem') {
                    if (trim((string)$value) === '') {
                        errorResponse($key . ' cannot be empty', 422);
                    }
                }
                $fields[] = "$key = ?";
                $params[] = $value;
            }
        }

        $choices = null;
        if (array_key_exists('choices', $body)) {
            if (!is_array($body['choices'])) {
                errorResponse('choices must be an array', 422);
            }
            $choices = validateChoices($body['choices']);
        }

        if ($fields === [] && $choices === null) {
            errorResponse('No updatable fields provided', 422);
        }

        $pdo->beginTransaction();
        try {
            if ($fields !== []) {
                $params[] = $questionId;
                $sql = 'UPDATE questions SET ' . implode(', ', $fields) . ' WHERE question_id = ?';
                $stmt = $pdo->prepare($sql);
                $stmt->execute($params);
            }

            if ($choices !== null) {
                $stmt = $pdo->prepare('DELETE FROM question_choices WHERE question_id = ?');
                $stmt->execute([$questionId]);
                if ($choices !== []) {
                    $stmt = $pdo->prepare('INSERT INTO question_choices (question_id, choice_label, choice_text) VALUES (?, ?, ?)');
                    foreach ($choices as $choice) {
                        $stmt->execute([$questionId, $choice['choice_label'], $choice['choice_text']]);
                    }
                }
            }

            $pdo->commit();
        } catch (Throwable $e) {
            $pdo->rollBack();
            errorResponse('Failed to update question', 500);
        }

        jsonResponse(['question_id' => $questionId]);
    }

    if ($method === 'DELETE') {
        $stmt = $pdo->prepare('DELETE FROM questions WHERE question_id = ?');
        $stmt->execute([$questionId]);
        if ($stmt->rowCount() === 0) {
            errorResponse('Question not found', 404);
        }
        jsonResponse(['deleted' => true]);
    }
}

if (preg_match('#^/questions/(\d+)/choices$#', $path, $matches)) {
    $questionId = (int)$matches[1];

    if ($method === 'GET') {
        $choicesMap = fetchChoices($pdo, [$questionId]);
        jsonResponse(['question_id' => $questionId, 'choices' => $choicesMap[$questionId] ?? []]);
    }

    if ($method === 'PUT') {
        $body = readJsonBody();
        if (!isset($body['choices']) || !is_array($body['choices'])) {
            errorResponse('choices must be provided', 422);
        }
        $choices = validateChoices($body['choices']);

        $pdo->beginTransaction();
        try {
            $stmt = $pdo->prepare('DELETE FROM question_choices WHERE question_id = ?');
            $stmt->execute([$questionId]);
            if ($choices !== []) {
                $stmt = $pdo->prepare('INSERT INTO question_choices (question_id, choice_label, choice_text) VALUES (?, ?, ?)');
                foreach ($choices as $choice) {
                    $stmt->execute([$questionId, $choice['choice_label'], $choice['choice_text']]);
                }
            }
            $pdo->commit();
        } catch (Throwable $e) {
            $pdo->rollBack();
            errorResponse('Failed to update choices', 500);
        }

        jsonResponse(['question_id' => $questionId]);
    }
}

if ($path === '/answers' && $method === 'POST') {
    $body = readJsonBody();

    $userId = toInt($body['user_id'] ?? null, 0);
    $questionId = toInt($body['question_id'] ?? null, 0);
    $selectedLabel = ensureLabel($body['selected_label'] ?? null);

    if ($userId <= 0 || $questionId <= 0) {
        errorResponse('user_id and question_id are required', 422);
    }

    $stmt = $pdo->prepare('SELECT correct_label FROM questions WHERE question_id = ?');
    $stmt->execute([$questionId]);
    $row = $stmt->fetch();
    if (!$row) {
        errorResponse('Question not found', 404);
    }

    $isCorrect = (int)($row['correct_label'] === $selectedLabel);

    $stmt = $pdo->prepare(
        'INSERT INTO answers (user_id, question_id, selected_label, is_correct, elapsed_ms)
        VALUES (?, ?, ?, ?, ?)'
    );
    $stmt->execute([
        $userId,
        $questionId,
        $selectedLabel,
        $isCorrect,
        $body['elapsed_ms'] ?? null,
    ]);

    jsonResponse(['answer_id' => (int)$pdo->lastInsertId(), 'is_correct' => (bool)$isCorrect], 201);
}

if ($path === '/answers' && $method === 'GET') {
    $where = [];
    $params = [];

    if (isset($_GET['user_id'])) {
        $where[] = 'user_id = ?';
        $params[] = (int)$_GET['user_id'];
    }
    if (isset($_GET['question_id'])) {
        $where[] = 'question_id = ?';
        $params[] = (int)$_GET['question_id'];
    }

    $limit = max(1, min(200, toInt($_GET['limit'] ?? 50, 50)));
    $offset = max(0, toInt($_GET['offset'] ?? 0, 0));

    $sql = 'SELECT * FROM answers';
    if ($where !== []) {
        $sql .= ' WHERE ' . implode(' AND ', $where);
    }
    $sql .= ' ORDER BY answer_id DESC LIMIT ? OFFSET ?';
    $params[] = $limit;
    $params[] = $offset;

    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $rows = $stmt->fetchAll();

    jsonResponse(['items' => $rows, 'limit' => $limit, 'offset' => $offset]);
}

errorResponse('Not found', 404);
