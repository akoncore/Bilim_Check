FROM python:3.12-slim
WORKDIR /app
RUN useradd --system --uid 10001 --create-home school && mkdir /data && chown school /data
COPY app.py question-bank.json ./
COPY web/ web/
ENV HOST=0.0.0.0 PORT=8000 DB_PATH=/data/school.sqlite3 PYTHONUNBUFFERED=1
USER school
EXPOSE 8000
CMD ["python", "app.py"]
