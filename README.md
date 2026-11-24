# ae

Docker Compose стек:

| Сервис   | Контейнер | Адрес |
|----------|-----------|--------|
| Caddy    | reverse proxy + TLS | `ae.tedeshi.ru`, `adminer.ae.tedeshi.ru` |
| Backend  | FastAPI + Alembic | `https://ae.tedeshi.ru/api` |
| Frontend | React (Vite → nginx) | `https://ae.tedeshi.ru/` |
| DB       | PostgreSQL 16 | внутренний, volume `pgdata` |
| Adminer  | Adminer 4 | `https://adminer.ae.tedeshi.ru` |

## Аутентификация

Пользователь идентифицируется **TOTP-секретом** (без surrogate id). Один экран: QR слева, 6 цифр справа.

1. Сервер выдаёт свежий секрет (`POST /api/auth/start`), QR на экране.
2. Пользователь вводит 6 цифр (`POST /api/auth/verify`):
   - код совпал ровно с одним пользователем в базе → вход;
   - код подошёл 2+ пользователям → «введите повторно»;
   - 0 совпадений → код сверяется с QR-секретом: валиден → регистрация, иначе ошибка.
3. При первой успешной аутентификации выставляется `display_name` (случайное русское имя).

## Запуск

```bash
cp .env.example .env   # поменять SECRET_KEY и пароли
docker compose up -d --build
```

Миграции применяются автоматически при старте backend.

## Локальная разработка

```bash
# backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend
cd frontend
npm install
npm run dev   # прокси /api → localhost:8000
```

## Структура

```
Caddyfile
docker-compose.yml
backend/          FastAPI + Alembic (users, auth)
frontend/         React + Vite (auth page, theme toggle)
```
