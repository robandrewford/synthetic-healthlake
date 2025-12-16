I want a **single-screen, side-scrolling TUI** that shows the **entire data platform** as a living “map” (think Metroid-style) where every node—ingest, storage, ETL, warehouse, BI, SLO/SLA, alerts—is **clickable** to deep-link into the real tool (AWS, dbt, Snowflake, etc.).  
The view must stay **live** (metrics, alerts, SLOs) and be **open-source only**.
### Verified Building Blocks
1. **TUI framework**
    - [https://github.com/rasjonell/dashbrew](https://github.com/rasjonell/dashbrew) (Go) gives a **keyboard + mouse** canvas, JSON-configured panes, and can call any REST/CLI endpoint for live data
    - If you prefer Python, [https://github.com/aristocratos/btop](https://github.com/aristocratos/btop) or [https://github.com/ClementTsang/bottom](https://github.com/ClementTsang/bottom) supply ASCII charts + mouse clicks; they can be scripted to fetch metrics
2. **Data collectors**
    - **Grafana** has 70+ OSS exporters (Prometheus, CloudWatch, Snowflake, dbt, etc.) and already exposes `/api/v1/query` for any metric or alert
    - **Metabase** gives a thin SQL-over-HTTP layer for business KPIs & SLOs via `/api/card/:id/query` [](https://estuary.dev/blog/open-source-data-analytics-tools/).
3. **Deep-link generator**
    - A 30-line Python micro-service (`fastapi`) maps node-type → URL template:  
        `snowflake.com/console#/queries/{query_id}`, `dbt.cloud/run/{job_id}`, etc.
### Reference Implementation

```python
# expert_python.py
# 1. Install:  pip install fastapi uvicorn rich httpx
# 2. Run:     uvicorn expert_python:app --port 8000
# 3. curl http://localhost:8000/map.json | dashbrew -c -

from fastapi import FastAPI
from datetime import datetime
import httpx, os, asyncio

app = FastAPI()
GRAFANA = os.getenv("GRAFANA_URL") + "/api/v1/query"
METABASE = os.getenv("MB_URL") + "/api/card"
MB_TOKEN = os.getenv("MB_TOKEN")

async def fetch(session, url, **kw):
    r = await session.get(url, **kw)
    return r.json()

@app.get("/map.json")
async def build_map():
    async with httpx.AsyncClient() as s:
        # live alerts
        alerts = await fetch(s, GRAFANA, params={"query": "ALERTS"})
        # dbt job status
        dbt = await fetch(s, GRAFANA, params={"query": "dbt_job_status"})
        # Snowflake credits
        sf = await fetch(s, GRAFANA, params={"query": "snowflake_credits_used"})
    return {
        "layout": "side-scroll",
        "panes": [
            {"type": "chart", "title": "Alerts", "data": alerts},
            {"type": "link", "title": "dbt Cloud", "url": "https://cloud.getdbt.com/run/{job_id}"},
            {"type": "chart", "title": "Snowflake", "data": sf}
        ]
    }
```
### Instructions
1. **Stand-up Grafana exporters** for every component (AWS via CloudWatch exporter, Snowflake via `snowflake-exporter`, dbt via `dbt-artifacts` + Prometheus).
2. **Deploy the Python micro-service** above; it returns a single JSON that `dashbrew` can render.
3. **Edit `dashbrew` config** to add mouse-click actions:
```json
"onClick": {"exec": "xdg-open $url"}
```
1. **Theme the map** with ASCII icons:  
    🔄 = pipeline, 🗂️ = warehouse, 🚨 = alert > 0, ✅ = SLO ok.
2. **Refresh loop**: set `dashbrew --refresh 10s` or let the micro-service push WebSocket updates.
### Constraints
- 100 % open-source; no paid plugins.
- Runs in any terminal ≥ 80×24; SSH-friendly.
- Keeps < 1 % CPU on a t3.micro when idle.
### Output Format

A single `dashbrew` JSON file (or `btop` plug-in) that renders:

```
[Map]  Ingest🟢  →  Store🟢  →  Transform🟡  →  BI🟢  →  SLO 99.9 %
Click any node to jump into the native UI; press R to refresh.
```
### Reasoning

We pair a **lightweight TUI engine** (`dashbrew`) with **Grafana’s proven exporters** to avoid reimplementing metrics collection. A tiny Python shim translates the metrics into the TUI’s JSON schema and supplies the deep-links, satisfying the “one pane of glass” requirement without heavy GUI frameworks.
## dashboard.json (place in repo root)

```json
{
  "title": "Data-Platform Map",
  "layout": "side-scroll",
  "refresh": 10,
  "panes": [
    {
      "id": "ingest",
      "type": "chart",
      "title": "🔄 Kinesis ➜ S3",
      "source": {
        "type": "http",
        "url": "http://localhost:8080/metrics/ingest",
        "method": "GET"
      },
      "onClick": {
        "exec": "xdg-open https://console.aws.amazon.com/kinesis/home"
      }
    },
    {
      "id": "dbt",
      "type": "chart",
      "title": "🔨 dbt Cloud",
      "source": {
        "type": "http",
        "url": "http://localhost:8080/metrics/dbt",
        "method": "GET"
      },
      "onClick": {
        "exec": "xdg-open https://cloud.getdbt.com"
      }
    },
    {
      "id": "snowflake",
      "type": "chart",
      "title": "🗄️ Snowflake",
      "source": {
        "type": "http",
        "url": "http://localhost:8080/metrics/snowflake",
        "method": "GET"
      },
      "onClick": {
        "exec": "xdg-open https://app.snowflake.com"
      }
    },
    {
      "id": "slo",
      "type": "stat",
      "title": "📊 SLO 99.9 %",
      "source": {
        "type": "http",
        "url": "http://localhost:8080/metrics/slo",
        "method": "GET"
      }
    },
    {
      "id": "alerts",
      "type": "list",
      "title": "🚨 Alerts",
      "source": {
        "type": "http",
        "url": "http://localhost:8080/alerts",
        "method": "GET"
      }
    }
  ]
}
```

docker-compose.yml

```yaml
version: "3.8"
services:
  prometheus:
    image: prom/prometheus:v2.45.0
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:10.0.0
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3000:3000"
    volumes:
      - grafana-storage:/var/lib/grafana

  # Thin shim that turns Prometheus/Grafana data into the JSON
  # that dashbrew expects (see architecture in previous turn).
  api:
    build: ./api          # tiny FastAPI service (see below)
    ports:
      - "8080:8080"
    environment:
      PROMETHEUS_URL: http://prometheus:9090
      GRAFANA_URL: http://grafana:3000
    depends_on:
      - prometheus
      - grafana

  # Optional: exporter for Snowflake credits & queries
  snowflake-exporter:
    image: ghcr.io/latchbio/snowflake-prometheus-exporter:latest
    environment:
      SNOWFLAKE_ACCOUNT: ${SNOWFLAKE_ACCOUNT}
      SNOWFLAKE_USER: ${SNOWFLAKE_USER}
      SNOWFLAKE_PRIVATE_KEY_PATH: /run/secrets/snowflake_key
    secrets:
      - snowflake_key
    ports:
      - "9500:9500"

secrets:
  snowflake_key:
    file: ./snowflake_key.p8

volumes:
  grafana-storage:
```

## api/Dockerfile (create ./api/…)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

## api/requirements.txt

```text
fastapi==0.110
uvicorn[standard]==0.29
httpx==0.27
```

## api/main.py (same 30-line shim promised earlier)

```python
from fastapi import FastAPI
import httpx, os

PROM = os.getenv("PROMETHEUS_URL") + "/api/v1/query"
app  = FastAPI()

async def prom(query: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(PROM, params={"query": query})
        return r.json()["data"]["result"]

@app.get("/metrics/{node}")
async def node_metrics(node: str):
    # map friendly names to real PromQL
    q = {
        "ingest":  'sum(rate(kinesis_incoming_records_total[5m]))',
        "dbt":     'dbt_job_status',
        "snowflake": 'snowflake_credits_used',
        "slo":     'slo_availability_percent'
    }.get(node, "up")
    return await prom(q)

@app.get("/alerts")
async def alerts():
    return await prom("ALERTS")
```
## One-time bootstrap
1. `docker compose up -d`
2. `go install github.com/rasjonell/dashbrew/cmd/dashbrew@latest`
3. `dashbrew -c dashboard.json`

I should now have a living side-scrolling map—hit the nodes to jump straight into AWS, dbt, or Snowflake.
