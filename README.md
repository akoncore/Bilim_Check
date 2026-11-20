# Bilim Check

Математическая диагностика на казахском языке. Ученик вводит имя и класс, решает задачи и видит результат. Учитель видит регистрации, ход тестов, ответы и разбор по классам и темам.

| Папка | Назначение |
| --- | --- |
| `backend/` | Django REST Framework, модели, миграции PostgreSQL и банк задач |
| `frontend/` | React, Vite и устанавливаемая PWA |
| `docker/` | Dockerfiles и Compose для PostgreSQL, Redis, Django и Nginx |
| `nginx/` | Раздача React, проксирование API и HTTPS |

## Запуск

Скопируйте `.env.example` в `.env`. Задайте случайные значения `DJANGO_SECRET_KEY` и `POSTGRES_PASSWORD`. Выполните из корня проекта:

```sh
docker compose --env-file .env -f docker/compose.yaml up -d --build --wait
docker compose --env-file .env -f docker/compose.yaml exec backend python manage.py createsuperuser
```

- Ученик — [http://localhost:8080/](http://localhost:8080/)
- Учитель — [http://localhost:8080/admin/](http://localhost:8080/admin/). Введите имя пользователя и пароль из `createsuperuser`.

Миграции и загрузка 66 примеров выполняются при запуске backend. Данные PostgreSQL сохраняются в томе `postgres-data`. Существующие локальные записи старого SQLite-файла автоматически не переносятся.

## Диагностика

Ученик может выбрать раздел, включающий его класс. Например, ученик 7-го класса в разделе «5–9» получает задачи 5-го, 6-го и 7-го классов. Из каждого класса выбираются три темы и по 2–3 задачи на тему. Ответ сохраняется после выбора. Учитель видит как завершённые, так и незавершённые тесты. После оценки всех задач класса результат ниже 70% считается пробелом. Рекомендация начинается с самого младшего класса с пробелом.

## Как загрузить свои задачи

Откройте **Мұғалім кабинеті → Есептер банкі** и загрузите JSON в UTF-8. Полный пример находится в [backend/question-bank.json](backend/question-bank.json).

```json
{
  "questions": [
    {
      "id": "grade-6-rational-03",
      "grade": 6,
      "topic": "Рационал сандар",
      "prompt": "−8 + 3 = ?",
      "options": ["−11", "−5", "5", "11"],
      "correct_index": 1
    }
  ]
}
```

`correct_index` начинается с 0. Здесь правильный ответ — «−5». Повторный импорт того же `id` обновляет задачу для будущих тестов. Тесты, начатые до импорта, хранят свои формулировки и правильные ответы. Для участия в тесте в теме должно быть минимум две задачи.

## Frontend и PWA

- `frontend/src/pages/` — страницы ученика и учителя.
- `frontend/src/layouts/` — общий каркас сайта и навигация кабинета.
- `frontend/src/components/` — формы, результаты и импорт.
- `frontend/src/hooks/` — отмена устаревших запросов, отправка форм, состояние сети и установка приложения.

Установка PWA доступна в поддерживаемых браузерах на HTTPS или localhost. Production-сборка Vite генерирует `sw.js` с версией и списком статических файлов. При открытии страницы без сети отображается офлайн-экран. Для сдачи тестов и просмотра результатов нужна сеть. Service worker хранит только файлы интерфейса и офлайн-страницу. Регистрации, ответы и отчёты в кэш браузера не записываются.

## API

Основной префикс REST API — `/api/v1/`. Префикс `/api/` сохранён для существующих клиентов. Маршруты в таблице показаны в совместимом виде.

Запросы на запись используют JSON и заголовок `X-CSRFToken`. Токен возвращается в `GET /api/csrf/`. Доступ к данным учителя требует Django-сессии с `is_staff`.

| Метод | Путь | Назначение |
| --- | --- | --- |
| POST | `/api/login/` | Регистрация ученика |
| GET | `/api/home/` | Доступные разделы и активный тест |
| POST | `/api/test/` | Начало или продолжение теста |
| GET | `/api/test/<id>/` | Задачи и сохранённые ответы |
| POST | `/api/test/<id>/answer/` | Сохранение ответа |
| POST | `/api/test/<id>/finish/` | Завершение теста |
| GET | `/api/test/<id>/result/` | Отчёт ученика |
| POST | `/api/admin/login/` | Вход учителя |
| GET | `/api/admin/results/` | Список результатов |
| GET | `/api/admin/students/` | Список учеников, поиск по `q` |
| GET | `/api/admin/student/<id>/result/` | История ученика |
| GET | `/api/admin/results/<id>/` | Подробный отчёт теста |
| POST | `/api/admin/questions/import/` | Импорт банка |

Списки возвращают `items`, `total`, `page`, `page_size`, `next` и `previous`. По умолчанию выдаётся 20 записей, максимум — 100. Фильтры `grade` и `q` доступны для учеников и результатов. Для результатов также доступен `status=completed|in_progress`.

Пример: `GET /api/v1/admin/results/?grade=7&status=completed&page=2&page_size=20`.

Redis хранит список тем по версии банка в течение часа. Успешный импорт меняет версию. При недоступности Redis Django читает темы из PostgreSQL. Результаты и данные пользователей в Redis не кэшируются. Лимиты записи хранятся в PostgreSQL и применяются ко всем экземплярам Django. Ответ `429` содержит заголовок `Retry-After`.

## Домен, HTTPS и CI/CD

На VPS разместите проект в `/opt/bilim-check`. Направьте DNS-запись `A` на IP сервера, укажите свой `DOMAIN` и `HTTP_PORT=80` в `.env`. Откройте порты 80 и 443. Выполните из корня проекта, заменив пример на свой домен:

```sh
mkdir -p nginx/acme
docker compose --env-file .env -f docker/compose.yaml up -d --build --wait
sudo certbot certonly --webroot -w /opt/bilim-check/nginx/acme -d diagnostic.example.kz
docker compose --env-file .env -f docker/compose.yaml -f docker/compose.https.yaml up -d --wait
curl --fail https://diagnostic.example.kz/health
```

Настройте обновление сертификата через Certbot с перезагрузкой Nginx в deploy-hook:

```sh
cd /opt/bilim-check
docker compose --env-file .env -f docker/compose.yaml -f docker/compose.https.yaml exec -T nginx nginx -s reload
```

GitHub Actions проверяет Django с PostgreSQL, собирает React в Docker и проверяет маршруты через Nginx. Для автоматического деплоя с основной ветки после первичной настройки VPS задайте переменную репозитория `DEPLOY_ENABLED=true` и секреты окружения `production`: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`, `DEPLOY_KNOWN_HOSTS`.

Макеты экранов доступны в [Figma](https://www.figma.com/design/sEpgxt0xrSFVYlLI7l2Yfw).
