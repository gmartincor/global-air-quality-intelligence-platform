# Phase 7: Monitoring & Observability

**Duration**: 1 week  
**Prerequisites**: All previous phases completed

---

## Objectives

- Set up Prometheus for metrics collection
- Create Grafana dashboards for visualization
- Implement alerting for critical failures
- Monitor pipeline health, data quality, and system resources
- Achieve end-to-end observability

---

## Tasks Breakdown

### 7.1 Prometheus Configuration

**File**: `infrastructure/monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'airflow'
    static_configs:
      - targets: ['airflow-webserver:8080']
    metrics_path: '/admin/metrics/'

  - job_name: 'spark'
    static_configs:
      - targets: ['spark-master:8080']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'localstack'
    static_configs:
      - targets: ['localstack:4566']

  - job_name: 'custom_pipeline_metrics'
    static_configs:
      - targets: ['pipeline-metrics:8000']
```

**Update docker-compose.yml**:
```yaml
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ../../infrastructure/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - "9090:9090"
    networks:
      - air-quality-network

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    depends_on:
      - prometheus
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
      - ../../infrastructure/monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ../../infrastructure/monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    ports:
      - "3000:3000"
    networks:
      - air-quality-network

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: postgres-exporter
    environment:
      - DATA_SOURCE_NAME=postgresql://airflow:airflow@postgres:5432/air_quality_warehouse?sslmode=disable
    ports:
      - "9187:9187"
    networks:
      - air-quality-network

volumes:
  prometheus-data:
  grafana-data:
```

---

### 7.2 Custom Metrics Exporter

**File**: `src/monitoring/metrics_exporter.py`

```python
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import time
import psycopg2

from src.common.config import config
from src.common.logger import setup_logger

logger = setup_logger(__name__)


pipeline_records_processed = Counter(
    'pipeline_records_processed_total',
    'Total records processed by pipeline',
    ['layer', 'status']
)

pipeline_execution_duration = Histogram(
    'pipeline_execution_duration_seconds',
    'Pipeline execution duration',
    ['pipeline_name']
)

data_quality_score = Gauge(
    'data_quality_score',
    'Current data quality score',
    ['layer']
)

pipeline_lag_seconds = Gauge(
    'pipeline_lag_seconds',
    'Time lag between source and warehouse',
    ['layer']
)

active_streaming_consumers = Gauge(
    'active_streaming_consumers',
    'Number of active streaming consumers'
)


class MetricsExporter:
    
    def __init__(self):
        self.conn = psycopg2.connect(
            host=config.database.host,
            port=config.database.port,
            database=config.database.database,
            user=config.database.user,
            password=config.database.password
        )
    
    def collect_quality_metrics(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT
                    layer,
                    AVG(success_rate) as avg_score
                FROM data_quality_metrics
                WHERE execution_timestamp >= NOW() - INTERVAL '1 day'
                GROUP BY layer
            """)
            
            for layer, score in cur.fetchall():
                data_quality_score.labels(layer=layer).set(score)
    
    def collect_pipeline_lag(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT
                    EXTRACT(EPOCH FROM (NOW() - MAX(measurement_timestamp))) as lag_seconds
                FROM facts.fact_air_quality_measurements
            """)
            
            result = cur.fetchone()
            if result and result[0]:
                pipeline_lag_seconds.labels(layer='gold').set(result[0])
    
    def collect_record_counts(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM facts.fact_air_quality_measurements
                WHERE DATE(measurement_timestamp) = CURRENT_DATE
            """)
            
            count = cur.fetchone()[0]
            pipeline_records_processed.labels(layer='gold', status='success').inc(count)
    
    def run(self, port: int = 8000):
        start_http_server(port)
        logger.info(f"Metrics server started on port {port}")
        
        while True:
            try:
                self.collect_quality_metrics()
                self.collect_pipeline_lag()
                self.collect_record_counts()
                logger.debug("Metrics collected")
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
            
            time.sleep(60)


def main():
    exporter = MetricsExporter()
    exporter.run()


if __name__ == "__main__":
    main()
```

---

### 7.3 Grafana Datasource Configuration

**File**: `infrastructure/monitoring/grafana/datasources/prometheus.yml`

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true

  - name: PostgreSQL
    type: postgres
    url: postgres:5432
    database: air_quality_warehouse
    user: airflow
    secureJsonData:
      password: airflow
    jsonData:
      sslmode: disable
      postgresVersion: 1500
```

---

### 7.4 Grafana Dashboards

**File**: `infrastructure/monitoring/grafana/dashboards/pipeline_overview.json`

```json
{
  "dashboard": {
    "title": "Air Quality Pipeline Overview",
    "tags": ["pipeline", "overview"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Records Processed (24h)",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(increase(pipeline_records_processed_total[24h]))",
            "legendFormat": "Total Records"
          }
        ],
        "gridPos": {
          "h": 4,
          "w": 6,
          "x": 0,
          "y": 0
        }
      },
      {
        "id": 2,
        "title": "Data Quality Score",
        "type": "gauge",
        "targets": [
          {
            "expr": "avg(data_quality_score)",
            "legendFormat": "Quality Score"
          }
        ],
        "gridPos": {
          "h": 4,
          "w": 6,
          "x": 6,
          "y": 0
        },
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {"value": 0, "color": "red"},
                {"value": 80, "color": "yellow"},
                {"value": 95, "color": "green"}
              ]
            },
            "min": 0,
            "max": 100
          }
        }
      },
      {
        "id": 3,
        "title": "Pipeline Lag",
        "type": "graph",
        "targets": [
          {
            "expr": "pipeline_lag_seconds",
            "legendFormat": "{{layer}}"
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 4
        }
      },
      {
        "id": 4,
        "title": "Pipeline Execution Duration",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, pipeline_execution_duration_seconds_bucket)",
            "legendFormat": "p95 - {{pipeline_name}}"
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 4
        }
      }
    ]
  }
}
```

**File**: `infrastructure/monitoring/grafana/dashboards/data_quality.json`

```json
{
  "dashboard": {
    "title": "Data Quality Monitoring",
    "tags": ["data-quality"],
    "panels": [
      {
        "id": 1,
        "title": "Quality Score by Layer",
        "type": "graph",
        "targets": [
          {
            "expr": "data_quality_score",
            "legendFormat": "{{layer}}"
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 0
        }
      },
      {
        "id": 2,
        "title": "Failed Expectations (7 days)",
        "type": "table",
        "targets": [
          {
            "rawSql": "SELECT layer, suite_name, failed_expectations, execution_timestamp FROM data_quality_metrics WHERE execution_timestamp >= NOW() - INTERVAL '7 days' AND failed_expectations > 0 ORDER BY execution_timestamp DESC LIMIT 20"
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 0
        }
      }
    ]
  }
}
```

---

### 7.5 Alerting Rules

**File**: `infrastructure/monitoring/alert_rules.yml`

```yaml
groups:
  - name: pipeline_alerts
    interval: 1m
    rules:
      - alert: PipelineLagHigh
        expr: pipeline_lag_seconds > 3600
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pipeline lag is high"
          description: "Pipeline is {{ $value }} seconds behind"

      - alert: DataQualityLow
        expr: data_quality_score < 90
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Data quality score below threshold"
          description: "Quality score is {{ $value }}% for {{ $labels.layer }}"

      - alert: PipelineExecutionFailed
        expr: increase(airflow_task_failed_total[5m]) > 0
        labels:
          severity: critical
        annotations:
          summary: "Pipeline execution failed"
          description: "Task {{ $labels.task_id }} failed in DAG {{ $labels.dag_id }}"

      - alert: NoRecentData
        expr: time() - pipeline_lag_seconds > 7200
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "No recent data ingested"
          description: "No data ingested in the last 2 hours"
```

---

### 7.6 Health Check Endpoint

**File**: `src/monitoring/health_check.py`

```python
from flask import Flask, jsonify
import psycopg2
from datetime import datetime, timedelta

from src.common.config import config
from src.common.logger import setup_logger

app = Flask(__name__)
logger = setup_logger(__name__)


def check_database_connection():
    try:
        conn = psycopg2.connect(
            host=config.database.host,
            port=config.database.port,
            database=config.database.database,
            user=config.database.user,
            password=config.database.password
        )
        conn.close()
        return True
    except:
        return False


def check_data_freshness():
    try:
        conn = psycopg2.connect(
            host=config.database.host,
            port=config.database.port,
            database=config.database.database,
            user=config.database.user,
            password=config.database.password
        )
        with conn.cursor() as cur:
            cur.execute("""
                SELECT MAX(measurement_timestamp)
                FROM facts.fact_air_quality_measurements
            """)
            latest = cur.fetchone()[0]
            conn.close()
            
            if latest:
                age = datetime.utcnow() - latest
                return age < timedelta(hours=2)
        return False
    except:
        return False


@app.route('/health')
def health():
    db_ok = check_database_connection()
    data_fresh = check_data_freshness()
    
    status = "healthy" if (db_ok and data_fresh) else "unhealthy"
    
    return jsonify({
        "status": status,
        "checks": {
            "database": db_ok,
            "data_freshness": data_fresh
        },
        "timestamp": datetime.utcnow().isoformat()
    }), 200 if status == "healthy" else 503


@app.route('/metrics')
def metrics():
    try:
        conn = psycopg2.connect(
            host=config.database.host,
            port=config.database.port,
            database=config.database.database,
            user=config.database.user,
            password=config.database.password
        )
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM facts.fact_air_quality_measurements) as total_measurements,
                    (SELECT AVG(success_rate) FROM data_quality_metrics WHERE execution_timestamp >= NOW() - INTERVAL '1 day') as avg_quality_score
            """)
            
            result = cur.fetchone()
            conn.close()
            
            return jsonify({
                "total_measurements": result[0],
                "avg_quality_score": float(result[1]) if result[1] else 0
            })
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        return jsonify({"error": str(e)}), 500


def main():
    app.run(host='0.0.0.0', port=8000)


if __name__ == "__main__":
    main()
```

---

### 7.7 Makefile Updates

```makefile
.PHONY: monitoring-up monitoring-down metrics-exporter

monitoring-up:
	docker-compose -f infrastructure/docker/docker-compose.yml up -d prometheus grafana postgres-exporter

monitoring-down:
	docker-compose -f infrastructure/docker/docker-compose.yml stop prometheus grafana postgres-exporter

metrics-exporter:
	poetry run python -m src.monitoring.metrics_exporter
```

---

## Validation Steps

### 1. Start Monitoring Stack
```bash
make monitoring-up
```

### 2. Access Prometheus
Visit http://localhost:9090 and verify targets are up

### 3. Access Grafana
- URL: http://localhost:3000
- Login: admin/admin
- Import dashboards from `infrastructure/monitoring/grafana/dashboards/`

### 4. Test Health Endpoint
```bash
curl http://localhost:8000/health
```

### 5. Verify Metrics Collection
```bash
curl http://localhost:9090/api/v1/query?query=pipeline_records_processed_total
```

---

## Deliverables Checklist

- [ ] Prometheus configured
- [ ] Grafana dashboards created
- [ ] Custom metrics exporter running
- [ ] Alert rules defined
- [ ] Health check endpoint implemented
- [ ] All services monitored
- [ ] Dashboards showing real-time data

---

## Next Phase

Proceed to [Phase 8: Testing & CI/CD](./phase8_testing.md)
