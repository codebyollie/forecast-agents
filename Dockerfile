FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY forecast_ai ./forecast_ai
RUN pip install --no-cache-dir .

COPY start.sh ./
RUN chmod +x /app/start.sh

EXPOSE 30000

CMD ["sh", "/app/start.sh"]
