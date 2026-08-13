# 🏢 IndoScraping Enterprise Production Deployment Guide

This guide details the production architecture, proxy management, observability, containerization, and orchestration required to run **IndoScraping** in high-throughput enterprise environments.

---

## 🏗️ Enterprise Architecture Overview

```
                                  ┌────────────────────────┐
                                  │   Airflow / K8s Cron   │
                                  └───────────┬────────────┘
                                              │
                                              ▼
                                  ┌────────────────────────┐
                                  │ Docker Container Pool  │
                                  └───────────┬────────────┘
                                              │
                     ┌────────────────────────┼────────────────────────┐
                     ▼                        ▼                        ▼
        ┌────────────────────────┐┌───────────────────────┐┌────────────────────────┐
        │   Proxy Pool Gateway   ││  Pydantic Data Schema ││  Datadog / CloudWatch  │
        │ (BrightData / Oxylabs) ││ Drift Alerting Engine ││ Structured JSON Logs   │
        └────────────────────────┘└───────────────────────┘└────────────────────────┘
```

---

## 🔑 Key Enterprise Capabilities

### 1. Proxy Rotation & Anti-Bot Mimicry
IndoScraping supports residential proxy rotation via standard environment variables:

```bash
# Set HTTP/HTTPS residential proxy endpoints
export HTTP_PROXY="http://user:pass@pr.oxylabs.io:7777"
export HTTPS_PROXY="http://user:pass@pr.oxylabs.io:7777"

# Execute scraper using proxy pool automatically
uv run indoscraping run alfagift
```

### 2. Structured JSON Logging for Observability
For integration with Datadog, AWS CloudWatch, Grafana Loki, or Kibana:

```bash
# Enable structured JSON logging
export JSON_LOGGING=true
export LOG_LEVEL=INFO

uv run indoscraping run detik
```

Output:
```json
{
  "timestamp": "2026-08-13T19:30:00Z",
  "level": "INFO",
  "service": "indoscraping",
  "logger": "detik",
  "message": "Scraping complete. Saved 50 articles to data/news/detik/latest.json",
  "count": 50
}
```

### 3. Automated Schema Drift Alerting
If target website layouts change, `detect_schema_drift` logs null-rate reports and raises `SchemaDriftError` to alert CI/CD and Slack/PagerDuty Webhooks:

```python
from indoscraping_core import detect_schema_drift, EcommerceProductModel

# Raises SchemaDriftError if key fields exceed null threshold
detect_schema_drift(payload, EcommerceProductModel, scraper_id="tokopedia", strict_raise=True)
```

### 4. Container Deployment (Docker & Kubernetes)

#### Docker Run:
```bash
# Build production image
docker build -t indoscraping:latest .

# Run headless container with data volume mount
docker run --rm \
  -e HTTP_PROXY="http://proxy:8080" \
  -v $(pwd)/data:/app/data \
  indoscraping:latest run blibli-search
```

#### Kubernetes CronJob Example:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: indoscraping-daily-ecommerce
spec:
  schedule: "0 2 * * *"  # Daily at 02:00 AM UTC
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: scraper
            image: indoscraping:latest
            command: ["uv", "run", "indoscraping", "run", "indomaret"]
            env:
            - name: JSON_LOGGING
              value: "true"
            volumeMounts:
            - name: data-volume
              mountPath: /app/data
          volumes:
          - name: data-volume
            persistentVolumeClaim:
              claimName: indoscraping-pvc
          restartPolicy: OnFailure
```
