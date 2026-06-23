# ContestForge backend — platform-agnostic container (ADR-003)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# API service. The ws-gateway and engine workers use different entrypoints
# (added per the delivery plan).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
