FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install the package itself in editable mode
RUN pip install -e .

EXPOSE 30000

CMD ["uvicorn", "forecast_ai.api.server:app", "--host", "0.0.0.0", "--port", "30000"]
