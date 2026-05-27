# АС «Наряды» — Система планирования и распределения нарядов

Автоматизированная система управления служебными нарядами для закрытой локальной сети (intranet).

## Run & Operate

- `cd artifacts/duty-scheduler && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` — запуск приложения
- Workflow: **Система нарядов** (порт 8000)
- База данных: `artifacts/duty-scheduler/duty_scheduler.db` (SQLite, создаётся при первом запуске)

## Stack

- Python 3.11
- FastAPI 0.111
- Jinja2 (серверный рендеринг, без React)
- SQLite (файловая БД)
- HTML + CSS (государственный минималистичный стиль)
- Vanilla JavaScript (минимально)

## Where things live

- `artifacts/duty-scheduler/app/main.py` — точка входа FastAPI, маршрут `/dashboard`
- `artifacts/duty-scheduler/app/routers/` — роутеры: staff, duties, schedule, settings
- `artifacts/duty-scheduler/app/scheduler/engine.py` — движок авторазбивки нарядов
- `artifacts/duty-scheduler/app/database.py` — инициализация БД, схема таблиц
- `artifacts/duty-scheduler/templates/` — Jinja2 шаблоны (base, dashboard, staff, duties, daily_plan, settings)
- `artifacts/duty-scheduler/static/style.css` — стили (гос-стиль, без анимаций)

## Pages

| Страница | URL | Назначение |
|---|---|---|
| Dashboard | `/dashboard` | Оперативная обстановка, статистика, недоборы |
| Личный состав | `/staff` | Список л/с, статусы, нагрузка |
| Наряды | `/duties` | Управление нарядами, типы нарядов, ручное назначение |
| Суточный план | `/daily-plan` | Полная картина: кто в наряде / обучении / отдыхе |
| Настройки | `/settings` | Нормы нарядов, правила распределения |

## Architecture decisions

- Служебные сутки 20:00–20:00, поддержка пересечения полуночи
- Лимит 8 ч/сут на сотрудника, минимум 4 ч отдыха между нарядами
- Статусы: available / sick / vacation / business_trip / rest / restricted / exempt
- Типы л/с: contract / conscript / exempt
- Автораспределение: обязательные наряды первыми, равномерная нагрузка (total_duty_hours ASC), свободные → activity/rest
- Выходные: ≥1/нед, ≥6/мес (кроме срочников)

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- Python-пакеты установлены через uv в `.pythonlibs/`
- После изменений в `app/` uvicorn перезагружается автоматически (`--reload`)
- `sqlite3.Row` используется для доступа к полям по имени
