# MySQL x PHP API (docker-compose)

## 起動

```bash
docker compose up --build
```

- API: http://localhost:8080
- DB: localhost:3306 (user: app / pass: apppass / db: app)
- UI: http://localhost:8080/ui.html

## エンドポイント

- `GET /health`
- `GET /questions?domain_name=&topic_name=&is_active=&limit=&offset=&include=choices`
- `POST /questions`
- `GET /questions/{id}`
- `PUT /questions/{id}`
- `DELETE /questions/{id}`
- `GET /questions/{id}/choices`
- `PUT /questions/{id}/choices`
- `POST /answers`
- `GET /answers?user_id=&question_id=&limit=&offset=`

## 例

### 問題作成

```bash
curl -X POST http://localhost:8080/questions \
  -H 'Content-Type: application/json' \
  -d '{
    "domain_name": "テクノロジ系",
    "topic_name": "ネットワーク",
    "title": "第1問",
    "stem": "TCP/IPの説明として正しいものはどれか",
    "correct_label": "A",
    "choices": [
      {"choice_label": "A", "choice_text": "..."},
      {"choice_label": "B", "choice_text": "..."},
      {"choice_label": "C", "choice_text": "..."},
      {"choice_label": "D", "choice_text": "..."}
    ]
  }'
```

### 回答送信

```bash
curl -X POST http://localhost:8080/answers \
  -H 'Content-Type: application/json' \
  -d '{"user_id": 1, "question_id": 1, "selected_label": "A", "elapsed_ms": 1200}'
```
