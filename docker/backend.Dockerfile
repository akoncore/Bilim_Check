FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --system --uid 10001 bilim
COPY backend/ .
USER bilim
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_questions && exec gunicorn bilim.wsgi:application --bind 0.0.0.0:8000 --workers 2"]
