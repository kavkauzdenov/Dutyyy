FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY artifacts/duty-scheduler/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY artifacts/duty-scheduler/app ./app
COPY artifacts/duty-scheduler/templates ./templates
COPY artifacts/duty-scheduler/static ./static

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

