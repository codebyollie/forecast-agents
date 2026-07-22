# Deployment Reference

Deploy Forecast AI as an API Server inside a Docker container:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e ".[ws]"
EXPOSE 30000
CMD ["forecast", "run"]
```
