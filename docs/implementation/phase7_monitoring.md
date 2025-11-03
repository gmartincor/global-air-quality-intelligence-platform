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

## Architecture & Design Principles

**Observability Stack**: Prometheus (metrics) → Grafana (visualization) → Alertmanager (notifications)

**Modular Monitoring**:
- Custom metrics exporter (application-level metrics)
- System exporters (PostgreSQL, infrastructure)
- Health check endpoint (liveness/readiness probes)

**SOLID Application**:
- **SRP**: Each exporter has single responsibility (pipeline metrics, database metrics, health checks)
- **OCP**: Add new metrics without modifying existing exporters
- **DIP**: Depend on Prometheus client abstraction, not implementation

**DRY**: Centralize metric definitions, reuse Prometheus client library patterns

**KISS**: Simple metric types (Counter, Gauge, Histogram), straightforward dashboard structure

---

## Tasks Breakdown

### 7.1 Prometheus Configuration

**Responsibility**: Configure Prometheus to scrape metrics from all system components

**Configuration File**: `infrastructure/monitoring/prometheus.yml`

**Required Scrape Jobs**:
- `prometheus`: Self-monitoring (localhost:9090)
- `airflow`: Airflow metrics (airflow-webserver:8080, path: /admin/metrics/)
- `spark`: Spark master metrics (spark-master:8080)
- `postgres`: PostgreSQL exporter (postgres-exporter:9187)
- `localstack`: LocalStack metrics (localstack:4566)
- `custom_pipeline_metrics`: Custom application metrics (pipeline-metrics:8000)

**Global Settings**:
- Scrape interval: 15 seconds
- Evaluation interval: 15 seconds

**Docker Compose Services** (`docker-compose.yml`):

**Prometheus Service**:
- Image: `prom/prometheus:latest`
- Port: 9090
- Volume: Mount prometheus.yml configuration
- Volume: Persistent storage for time-series data (prometheus-data)
- Command: Specify config file and storage path

**Grafana Service**:
- Image: `grafana/grafana:latest`
- Port: 3000
- Environment: Admin password (admin), disable sign-up
- Volumes: Persistent storage (grafana-data), provisioned dashboards and datasources
- Depends on: Prometheus

**PostgreSQL Exporter Service**:
- Image: `prometheuscommunity/postgres-exporter:latest`
- Port: 9187
- Environment: PostgreSQL connection string (DATA_SOURCE_NAME)
- Purpose: Export PostgreSQL-specific metrics

**Volumes**:
- `prometheus-data`: Persistent time-series database
- `grafana-data`: Persistent dashboard configurations

---

### 7.2 Custom Metrics Exporter

**Module**: `src/monitoring/metrics_exporter.py`

**Responsibility**: Expose custom application metrics in Prometheus format (SRP)

**Class**: `MetricsExporter`

**Metric Definitions** (using prometheus_client):

1. **pipeline_records_processed** (Counter):
   - Name: `pipeline_records_processed_total`
   - Description: Total records processed by pipeline
   - Labels: `layer` (bronze/silver/gold), `status` (success/failure)
   - Purpose: Track volume of processed data

2. **pipeline_execution_duration** (Histogram):
   - Name: `pipeline_execution_duration_seconds`
   - Description: Pipeline execution duration
   - Labels: `pipeline_name`
   - Purpose: Monitor pipeline performance, identify slowdowns

3. **data_quality_score** (Gauge):
   - Name: `data_quality_score`
   - Description: Current data quality score
   - Labels: `layer`
   - Purpose: Track quality degradation in real-time

4. **pipeline_lag_seconds** (Gauge):
   - Name: `pipeline_lag_seconds`
   - Description: Time lag between source and warehouse
   - Labels: `layer`
   - Purpose: Detect processing delays

5. **active_streaming_consumers** (Gauge):
   - Name: `active_streaming_consumers`
   - Description: Number of active streaming consumers
   - Purpose: Monitor streaming pipeline health

**Key Methods**:

- `__init__()`: Establish PostgreSQL connection to query metrics
- `collect_quality_metrics()`: Query avg quality score by layer (last 24h), update gauge
- `collect_pipeline_lag()`: Calculate time difference between now and latest measurement, update gauge
- `collect_record_counts()`: Count today's processed records, increment counter
- `run(port=8000)`: Start HTTP server, continuously collect metrics every 60 seconds

**SQL Queries Required**:
- Quality metrics: `SELECT layer, AVG(success_rate) FROM data_quality_metrics WHERE execution_timestamp >= NOW() - INTERVAL '1 day' GROUP BY layer`
- Pipeline lag: `SELECT EXTRACT(EPOCH FROM (NOW() - MAX(measurement_timestamp))) FROM facts.fact_air_quality_measurements`
- Record counts: `SELECT COUNT(*) FROM facts.fact_air_quality_measurements WHERE DATE(measurement_timestamp) = CURRENT_DATE`

**Error Handling**: Log errors, continue collection loop (resilience)

---

### 7.3 Grafana Datasource Configuration

**File**: `infrastructure/monitoring/grafana/datasources/prometheus.yml`

**Responsibility**: Provision datasources automatically when Grafana starts

**Datasources Required**:

1. **Prometheus Datasource**:
   - Name: Prometheus
   - Type: prometheus
   - Access mode: proxy (server-side requests)
   - URL: http://prometheus:9090
   - Default: true
   - Editable: true

2. **PostgreSQL Datasource**:
   - Name: PostgreSQL
   - Type: postgres
   - URL: postgres:5432
   - Database: air_quality_warehouse
   - User: airflow
   - Password: airflow (secureJsonData)
   - SSL mode: disable
   - PostgreSQL version: 15.0 (1500)

**Purpose**: Enable direct SQL queries for complex analytics and quality metrics visualization

---

### 7.4 Grafana Dashboards

**Responsibility**: Visualize pipeline health, data quality, and system performance

**Dashboard 1: Pipeline Overview** (`pipeline_overview.json`)

**Title**: Air Quality Pipeline Overview  
**Tags**: pipeline, overview

**Panels**:

1. **Records Processed (24h)** - Stat Panel:
   - Query: `sum(increase(pipeline_records_processed_total[24h]))`
   - Position: Top-left (0,0), size 6x4
   - Purpose: Show total volume processed in last 24 hours

2. **Data Quality Score** - Gauge Panel:
   - Query: `avg(data_quality_score)`
   - Position: Top-center (6,0), size 6x4
   - Thresholds: Red (0-80), Yellow (80-95), Green (95-100)
   - Purpose: Visual indicator of overall quality health

3. **Pipeline Lag** - Graph Panel:
   - Query: `pipeline_lag_seconds` (grouped by layer)
   - Position: Middle-left (0,4), size 12x8
   - Purpose: Track processing delays over time

4. **Pipeline Execution Duration (p95)** - Graph Panel:
   - Query: `histogram_quantile(0.95, pipeline_execution_duration_seconds_bucket)`
   - Position: Middle-right (12,4), size 12x8
   - Purpose: Identify performance degradation

**Dashboard 2: Data Quality Monitoring** (`data_quality.json`)

**Title**: Data Quality Monitoring  
**Tags**: data-quality

**Panels**:

1. **Quality Score by Layer** - Graph Panel:
   - Query: `data_quality_score` (all layers)
   - Position: Left (0,0), size 12x8
   - Purpose: Compare quality across Bronze/Silver/Gold layers

2. **Failed Expectations (7 days)** - Table Panel:
   - Datasource: PostgreSQL
   - Query: Select layer, suite_name, failed_expectations, execution_timestamp from data_quality_metrics WHERE failed_expectations > 0 (last 7 days, limit 20)
   - Position: Right (12,0), size 12x8
   - Purpose: Drill-down into specific quality failures

**JSON Structure Requirements**:
- Use Grafana dashboard schema version (apiVersion: 1)
- Include gridPos for all panels (x, y, w, h)
- Specify panel types: stat, gauge, graph, table
- Define targets with PromQL expressions or SQL queries

---

### 7.5 Alerting Rules

**File**: `infrastructure/monitoring/alert_rules.yml`

**Responsibility**: Define alert conditions for critical pipeline failures

**Alert Group**: pipeline_alerts  
**Evaluation Interval**: 1 minute

**Alert Rules**:

1. **PipelineLagHigh**:
   - Condition: `pipeline_lag_seconds > 3600`
   - Duration: 5 minutes
   - Severity: warning
   - Purpose: Detect when pipeline is >1 hour behind

2. **DataQualityLow**:
   - Condition: `data_quality_score < 90`
   - Duration: 10 minutes
   - Severity: critical
   - Purpose: Alert when quality drops below acceptable threshold (90%)

3. **PipelineExecutionFailed**:
   - Condition: `increase(airflow_task_failed_total[5m]) > 0`
   - Duration: immediate
   - Severity: critical
   - Purpose: Immediate notification of Airflow task failures

4. **NoRecentData**:
   - Condition: `time() - pipeline_lag_seconds > 7200`
   - Duration: 5 minutes
   - Severity: critical
   - Purpose: Alert when no data ingested in last 2 hours

**Annotation Template Variables**:
- `{{ $value }}`: Metric value triggering alert
- `{{ $labels.layer }}`: Layer label from metric
- `{{ $labels.task_id }}`, `{{ $labels.dag_id }}`: Airflow task context

---

### 7.6 Health Check Endpoint

**Module**: `src/monitoring/health_check.py`

**Responsibility**: Provide HTTP endpoints for liveness and readiness probes (Kubernetes-compatible)

**Framework**: Flask

**Endpoints**:

1. **GET /health** (Health Check):
   - Purpose: Overall system health status
   - Response codes: 200 (healthy), 503 (unhealthy)
   - Checks performed:
     - Database connection (`check_database_connection()`)
     - Data freshness (`check_data_freshness()`)
   
   **Response Schema**:
   ```json
   {
     "status": "healthy|unhealthy",
     "checks": {
       "database": true|false,
       "data_freshness": true|false
     },
     "timestamp": "ISO-8601 timestamp"
   }
   ```

2. **GET /metrics** (Summary Metrics):
   - Purpose: Quick metrics snapshot without Prometheus
   - Response code: 200 (success), 500 (error)
   
   **Response Schema**:
   ```json
   {
     "total_measurements": int,
     "avg_quality_score": float
   }
   ```

**Check Functions**:

- `check_database_connection()`: Attempt PostgreSQL connection, return boolean
- `check_data_freshness()`: Query max measurement_timestamp, verify <2 hours old

**SQL Queries**:
- Freshness check: `SELECT MAX(measurement_timestamp) FROM facts.fact_air_quality_measurements`
- Metrics summary: Join total measurements count with avg quality score (last 24h)

**Server Configuration**: Listen on 0.0.0.0:8000 for external access

---

### 7.7 Makefile Automation

**File**: `Makefile`

**Targets to Add**:

- `monitoring-up`: Start monitoring stack (Prometheus, Grafana, PostgreSQL exporter)
  - Command: `docker-compose -f infrastructure/docker/docker-compose.yml up -d prometheus grafana postgres-exporter`
  
- `monitoring-down`: Stop monitoring services
  - Command: `docker-compose -f infrastructure/docker/docker-compose.yml stop prometheus grafana postgres-exporter`
  
- `metrics-exporter`: Run custom metrics exporter in foreground
  - Command: `poetry run python -m src.monitoring.metrics_exporter`

- `health-check`: Run health check server
  - Command: `poetry run python -m src.monitoring.health_check`

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
