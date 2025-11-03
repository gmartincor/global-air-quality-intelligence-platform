# Global Air Quality Intelligence Platform - Architecture Design

## Project Overview

Real-time and batch data pipeline for air quality monitoring with Lambda Architecture, demonstrating production-grade Data Engineering practices using AWS services (LocalStack simulation), Infrastructure as Code (Terraform), and synthetic data generation.


**Key Differentiators**:
- Lambda Architecture with genuine streaming use case
- Synthetic data generation (configurable volume for GitHub/testing vs production-scale)
- LocalStack AWS simulation (S3, DynamoDB, Kinesis, Lambda)
- Terraform infrastructure provisioning
- Enterprise-grade code quality (SOLID, DRY, KISS, YAGNI)

---

## Architecture

### Lambda Architecture Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA GENERATION                          │
├─────────────────────────────────────────────────────────────────┤
│  Synthetic Data Generators (Python)                             │
│  ├─ Batch: Historical data (5 years, 300 cities)               │
│  │  └─ Command: --mode=full (10M records) or --mode=sample     │
│  └─ Stream: IoT sensor simulator (100-1000 sensors)            │
│     └─ Realistic patterns: rush hour, weather events           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         SPEED LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  Kinesis Stream → Flink/Kinesis Analytics                       │
│  ├─ Windowing (5-min tumbling)                                 │
│  ├─ Aggregations (avg/max AQI)                                 │
│  ├─ Anomaly detection (spike detection)                        │
│  └─ Alert triggering (AQI > 150)                               │
│                                                                  │
│  Output: DynamoDB (last 24 hours, low latency reads)           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         BATCH LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  Airflow → Spark (PySpark) → Delta Lake → dbt → PostgreSQL     │
│  ├─ Ingestion: S3 raw (Bronze)                                 │
│  ├─ Cleansing: Validation, deduplication (Silver)              │
│  ├─ Enrichment: AQI calculation, geolocation                   │
│  ├─ Transformation: dbt dimensional model (Gold)               │
│  └─ Testing: dbt tests + Great Expectations                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       SERVING LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  ├─ Real-time: DynamoDB → API/Dashboard (last 24h)            │
│  ├─ Historical: PostgreSQL → Metabase (analytics)              │
│  └─ Unified view: Merges both layers                           │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow: Medallion Architecture

**Bronze Layer** (Raw Zone)
- Location: S3 (`s3://bronze/air-quality/year=YYYY/month=MM/day=DD/`)
- Format: Parquet with Snappy compression
- Schema: None enforced (permissive)
- Partitioning: By ingestion date
- Retention: Indefinite (source of truth)

**Silver Layer** (Cleaned Zone)
- Location: S3 with Delta Lake (`s3://silver/air-quality/`)
- Format: Delta Lake (ACID transactions)
- Schema: Enforced and versioned
- Partitioning: By country and date
- Operations: Deduplication, validation, type casting
- Retention: Indefinite

**Gold Layer** (Business Zone)
- Location: PostgreSQL (dimensional model)
- Format: Star schema (fact + dimensions)
- Purpose: Analytics, BI, ML features
- SCD Type 2: dim_location for historical tracking
- Retention: Per regulatory requirements

---

## Technology Stack

### Infrastructure & IaC
- **Terraform**: Version-controlled infrastructure provisioning
- **LocalStack**: AWS services simulation (no cloud costs)
- **Docker Compose**: Consistent containerized environment

### Data Ingestion & Storage
- **AWS Kinesis** (LocalStack): Real-time streaming (100-1K msgs/sec)
- **AWS S3** (LocalStack): Scalable object storage (Bronze/Silver/Gold layers)
- **Delta Lake**: ACID transactions, schema evolution, time travel on S3

### Processing
- **Apache Airflow**: Workflow orchestration and DAG scheduling
- **Apache Spark (PySpark)**: Distributed batch processing (10M+ records)
- **Apache Flink**: Low-latency stream processing with windowing
- **dbt**: SQL-based transformations with built-in testing

### Storage & Serving
- **PostgreSQL**: Data warehouse with dimensional model and partitioning
- **DynamoDB** (LocalStack): Speed layer cache (<10ms reads)
- **Redis**: Query result caching (sub-millisecond responses)

### Data Quality & Testing
- **Great Expectations**: Automated data validation
- **dbt tests**: Transformation testing (generic + custom SQL)
- **pytest**: Python unit/integration testing

### Observability
- **Prometheus + Grafana**: Metrics collection and visualization
- **Airflow UI**: Built-in DAG/task monitoring

---


## Dimensional Model (Star Schema)

### Fact Table: `fact_air_quality_measurements`

**Grain**: One row per sensor measurement (city-hour level after aggregation)

| Column | Type | Description |
|--------|------|-------------|
| `measurement_key` | BIGSERIAL | Surrogate key (PK) |
| `location_key` | INTEGER | FK to dim_location |
| `time_key` | INTEGER | FK to dim_time |
| `pm25_value` | DECIMAL(6,2) | PM2.5 concentration (μg/m³) |
| `pm10_value` | DECIMAL(6,2) | PM10 concentration |
| `no2_value` | DECIMAL(6,2) | NO2 concentration |
| `so2_value` | DECIMAL(6,2) | SO2 concentration |
| `co_value` | DECIMAL(6,2) | CO concentration |
| `o3_value` | DECIMAL(6,2) | O3 concentration |
| `aqi_value` | SMALLINT | Calculated AQI (0-500) |
| `aqi_category` | VARCHAR(20) | Good/Moderate/Unhealthy/Hazardous |
| `dominant_pollutant` | VARCHAR(10) | Pollutant causing highest AQI |
| `temperature_c` | DECIMAL(4,2) | Temperature (Celsius) |
| `humidity_pct` | SMALLINT | Relative humidity (%) |
| `wind_speed_kmh` | DECIMAL(5,2) | Wind speed |
| `measurement_timestamp` | TIMESTAMP | Original measurement time |
| `source_system` | VARCHAR(50) | Data source identifier |

**Partitioning**: Range partitioning by `measurement_timestamp` (monthly partitions)

**Indexes**:
- Primary key: `measurement_key`
- Covering index: `(location_key, time_key, measurement_timestamp)`
- BRIN index: `measurement_timestamp` (for range scans)

### Dimension: `dim_location` (SCD Type 2)

**Purpose**: Track location attributes with history

| Column | Type | Description |
|--------|------|-------------|
| `location_key` | SERIAL | Surrogate key (PK) |
| `city_id` | VARCHAR(50) | Natural key (business key) |
| `city_name` | VARCHAR(100) | City name |
| `country_name` | VARCHAR(100) | Country name |
| `country_code` | CHAR(2) | ISO 3166-1 alpha-2 |
| `region` | VARCHAR(100) | Geographic region |
| `continent` | VARCHAR(50) | Continent |
| `latitude` | DECIMAL(9,6) | Latitude coordinate |
| `longitude` | DECIMAL(9,6) | Longitude coordinate |
| `timezone` | VARCHAR(50) | IANA timezone |
| `population` | INTEGER | City population |
| `gdp_per_capita` | DECIMAL(12,2) | Economic indicator |
| `urbanization_rate` | DECIMAL(5,2) | % urban population |
| `valid_from` | TIMESTAMP | SCD valid start date |
| `valid_to` | TIMESTAMP | SCD valid end date (NULL = current) |
| `is_current` | BOOLEAN | Current version flag |
| `version` | INTEGER | Version number |

**Indexes**:
- Primary key: `location_key`
- Unique: `(city_id, valid_from)`
- Filter index: `is_current = TRUE`
- Spatial index: `(latitude, longitude)` using PostGIS

### Dimension: `dim_time`

**Purpose**: Pre-populated calendar table for time intelligence

| Column | Type | Description |
|--------|------|-------------|
| `time_key` | INTEGER | Surrogate key (YYYYMMDDHH format) |
| `full_datetime` | TIMESTAMP | Full timestamp |
| `date` | DATE | Calendar date |
| `year` | SMALLINT | Year |
| `quarter` | SMALLINT | Quarter (1-4) |
| `month` | SMALLINT | Month (1-12) |
| `month_name` | VARCHAR(20) | Month name |
| `week_of_year` | SMALLINT | ISO week number |
| `day_of_month` | SMALLINT | Day (1-31) |
| `day_of_week` | SMALLINT | Day (1=Monday) |
| `day_name` | VARCHAR(20) | Day name |
| `hour` | SMALLINT | Hour (0-23) |
| `is_weekend` | BOOLEAN | Weekend flag |
| `is_holiday` | BOOLEAN | Holiday flag |
| `season` | VARCHAR(10) | Spring/Summer/Fall/Winter |
| `is_business_hour` | BOOLEAN | 8am-6pm flag |

**Population**: Pre-load 2020-2030 at hourly granularity

### Aggregate Table: `agg_daily_air_quality`

**Purpose**: Pre-computed daily aggregates for dashboard performance

| Column | Type | Description |
|--------|------|-------------|
| `location_key` | INTEGER | FK to dim_location |
| `date` | DATE | Calendar date |
| `avg_aqi` | DECIMAL(5,2) | Daily average AQI |
| `max_aqi` | SMALLINT | Daily maximum AQI |
| `min_aqi` | SMALLINT | Daily minimum AQI |
| `hours_good` | SMALLINT | Hours with Good AQI |
| `hours_moderate` | SMALLINT | Hours with Moderate AQI |
| `hours_unhealthy` | SMALLINT | Hours with Unhealthy AQI |
| `hours_hazardous` | SMALLINT | Hours with Hazardous AQI |
| `dominant_pollutant_mode` | VARCHAR(10) | Most frequent pollutant |

**Materialization**: Refreshed daily via dbt incremental model

---

## Data Generation Strategy

### Synthetic Data Requirements

**Realism Factors**:
- Geographic patterns (coastal cities cleaner, industrial areas worse)
- Temporal patterns (rush hour peaks, seasonal variations)
- Weather correlation (wind reduces pollution, rain cleans air)
- Event simulation (wildfires, factory shutdowns)
- Sensor noise (±5% random variation)

### Batch Data Generator

**Configuration**:
```python
# config/data_generation.yaml
batch:
  mode: sample  # or 'full'
  sample:
    cities: 50
    date_range: 2024-01-01 to 2024-12-31
    records: ~440K (50 cities × 365 days × 24 hours)
    file_size: ~50 MB (Parquet compressed)
  full:
    cities: 300
    date_range: 2020-01-01 to 2024-12-31
    records: ~13M (300 cities × 1826 days × 24 hours)
    file_size: ~1.5 GB (Parquet compressed)
```

**GitHub Default**: Sample mode (50 MB) for clone speed

**Testing/Demo Command**: 
```bash
make generate-data MODE=full
```

### Stream Data Generator

**Configuration**:
```python
streaming:
  mode: development  # or 'production'
  development:
    sensors: 10
    msg_rate: 1/sec
    runtime: continuous
  production:
    sensors: 1000
    msg_rate: 2/min per sensor = 33/sec aggregate
    runtime: continuous
```

**Simulator Features**:
- Realistic IoT sensor behavior (occasional failures, late messages)
- Configurable event injection (pollution spikes, sensor outages)
- Watermark generation for late data handling
- Duplicate message simulation for testing deduplication

---

## Design Patterns & Best Practices

### Software Engineering Principles

**SOLID**:
- **Single Responsibility**: Each module has one reason to change
  - `extractors/` - only data extraction
  - `transformers/` - only business logic
  - `loaders/` - only data persistence
- **Open/Closed**: Extensible via plugins (new data sources without modifying core)
- **Liskov Substitution**: Abstract interfaces for data sources
- **Interface Segregation**: Small, focused interfaces (IExtractor, ITransformer, ILoader)
- **Dependency Inversion**: Depend on abstractions, not concretions

**DRY (Don't Repeat Yourself)**:
- Shared utilities in `common/` module
- Configuration-driven behavior (no hardcoded values)
- Reusable Spark transformations as functions
- dbt macros for repeated SQL logic

**KISS (Keep It Simple, Stupid)**:
- Avoid premature optimization
- Prefer clarity over cleverness
- Simple data structures (avoid complex nested objects)

**YAGNI (You Aren't Gonna Need It)**:
- Implement features when needed, not speculatively
- No generic frameworks "for future use"
- Delete unused code aggressively

### Data Engineering Patterns

#### 1. Idempotency Pattern

**Problem**: Re-running pipelines produces different results

**Solution**:
- Deterministic IDs: `hash(city_id + timestamp)` for measurement keys
- Partition overwrite: Replace only affected date partitions
- Upsert strategy: `INSERT ON CONFLICT UPDATE` in PostgreSQL

**Implementation**:
```python
def generate_deterministic_id(city_id: str, timestamp: datetime) -> str:
    content = f"{city_id}_{timestamp.isoformat()}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

#### 2. Incremental Loading (Watermark Pattern)

**Problem**: Avoid reprocessing entire dataset

**Solution**:
- Metadata table: `pipeline_watermarks(pipeline_id, last_processed_timestamp)`
- Each run: `WHERE created_at > (SELECT last_watermark FROM watermarks)`
- Update watermark only on success

**dbt Implementation**:
```sql
{% if is_incremental() %}
  WHERE measurement_timestamp > (SELECT MAX(measurement_timestamp) FROM {{ this }})
{% endif %}
```

#### 3. Slowly Changing Dimension (SCD Type 2)

**Implementation**: dim_location tracks population/economic changes

```sql
-- Close existing record
UPDATE dim_location 
SET valid_to = CURRENT_TIMESTAMP, is_current = FALSE
WHERE city_id = '{{ city_id }}' AND is_current = TRUE;

-- Insert new record
INSERT INTO dim_location (city_id, population, ..., valid_from, is_current)
VALUES ('{{ city_id }}', {{ new_population }}, ..., CURRENT_TIMESTAMP, TRUE);
```

#### 4. Circuit Breaker Pattern

**Use Case**: External API failures (if future integration)

**Implementation**:
- After 3 consecutive failures → OPEN state (fail fast)
- After timeout → HALF_OPEN (test recovery)
- Success → CLOSED (normal operation)

#### 5. Dead Letter Queue

**Use Case**: Invalid streaming messages

**Implementation**:
- Kinesis Consumer catches exceptions
- Failed messages → DynamoDB `dlq_table`
- Alerting on DLQ depth > threshold
- Manual review/reprocessing workflow

#### 6. Schema Evolution

**Strategy**:
- Delta Lake `mergeSchema` option for additive changes
- Breaking changes → new version, parallel processing
- Schema registry pattern (Avro schemas in S3)

---

## Project Structure

```
global-air-quality/
├── infrastructure/
│   ├── terraform/
│   │   ├── main.tf              # Root module
│   │   ├── modules/
│   │   │   ├── s3/              # S3 buckets
│   │   │   ├── kinesis/         # Kinesis streams
│   │   │   ├── dynamodb/        # DynamoDB tables
│   │   │   └── networking/      # VPC, security groups
│   │   ├── environments/
│   │   │   ├── dev.tfvars
│   │   │   └── prod.tfvars
│   │   └── backend.tf           # State management
│   └── docker/
│       ├── docker-compose.yml   # All services
│       ├── airflow/
│       ├── spark/
│       └── localstack/
├── src/
│   ├── data_generation/
│   │   ├── batch_generator.py
│   │   ├── stream_simulator.py
│   │   └── generators/
│   │       ├── sensor.py
│   │       ├── weather.py
│   │       └── events.py
│   ├── ingestion/
│   │   ├── batch/
│   │   │   └── s3_loader.py
│   │   └── streaming/
│   │       ├── kinesis_producer.py
│   │       └── kinesis_consumer.py
│   ├── processing/
│   │   ├── spark/
│   │   │   ├── jobs/
│   │   │   │   ├── bronze_to_silver.py
│   │   │   │   ├── silver_enrichment.py
│   │   │   │   └── aggregations.py
│   │   │   └── transformations/
│   │   │       ├── cleansing.py
│   │   │       ├── validation.py
│   │   │       └── aqi_calculator.py
│   │   └── flink/
│   │       └── streaming_job.py
│   ├── orchestration/
│   │   └── airflow/
│   │       ├── dags/
│   │       │   ├── batch_pipeline_dag.py
│   │       │   └── dbt_dag.py
│   │       ├── operators/
│   │       └── sensors/
│   ├── transformation/
│   │   └── dbt/
│   │       ├── models/
│   │       │   ├── staging/
│   │       │   ├── intermediate/
│   │       │   └── marts/
│   │       │       ├── dimensions/
│   │       │       └── facts/
│   │       ├── tests/
│   │       ├── macros/
│   │       └── dbt_project.yml
│   ├── data_quality/
│   │   ├── great_expectations/
│   │   │   ├── expectations/
│   │   │   └── checkpoints/
│   │   └── validators/
│   └── common/
│       ├── config.py
│       ├── logger.py
│       ├── exceptions.py
│       └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── config/
│   ├── airflow.cfg
│   ├── spark-defaults.conf
│   └── data_generation.yaml
├── docs/
│   └── adr/                     # Architecture Decision Records
├── Makefile
├── pyproject.toml               # Poetry dependency management
├── .pre-commit-config.yaml
└── README.md
```

---

## Code Quality Standards

### Naming Conventions

**Files & Modules**:
- Python: `snake_case.py`
- Directories: `lowercase_with_underscores/`
- SQL: `snake_case.sql`
- YAML: `kebab-case.yaml`

**Variables & Functions**:
```python
# Constants
MAX_RETRY_ATTEMPTS = 3
AWS_REGION = "us-east-1"

# Functions
def calculate_aqi(pm25_value: float) -> int:
    pass

# Classes
class AirQualityProcessor:
    pass

# Private methods
def _internal_helper(self):
    pass
```

**Database Objects**:
- Tables: `snake_case` (e.g., `fact_air_quality_measurements`)
- Columns: `snake_case` (e.g., `measurement_timestamp`)
- Indexes: `idx_{table}_{columns}` (e.g., `idx_fact_location_time`)
- Constraints: `{type}_{table}_{detail}` (e.g., `pk_fact_measurements`)

### Code Organization

**Module Structure**:
```python
# module.py

from typing import Protocol, List
import pandas as pd

class IDataExtractor(Protocol):
    def extract(self) -> pd.DataFrame:
        ...

class S3Extractor:
    def __init__(self, bucket: str, prefix: str):
        self._bucket = bucket
        self._prefix = prefix
    
    def extract(self) -> pd.DataFrame:
        pass

def main():
    pass

if __name__ == "__main__":
    main()
```

**No Comments Policy**: Code must be self-documenting
- Descriptive names over comments
- Type hints for clarity
- Docstrings for public APIs only (not inline comments)

### Testing Strategy

**Unit Tests** (70% coverage target):
- Pure functions (transformations, calculations)
- Business logic (AQI calculation, validation rules)
- Utilities (config parsing, logging)

**Integration Tests** (20%):
- Spark jobs with sample data
- Database operations (with test DB)
- S3 operations (LocalStack)

**End-to-End Tests** (10%):
- Full pipeline run with synthetic data
- Data quality validation
- Output verification

**Test Structure**:
```python
# tests/unit/processing/test_aqi_calculator.py

import pytest
from src.processing.spark.transformations.aqi_calculator import calculate_aqi

class TestAQICalculator:
    def test_pm25_good_range(self):
        assert calculate_aqi(pm25=10.5) == 44
    
    def test_pm25_hazardous_range(self):
        assert calculate_aqi(pm25=350.5) == 458
    
    def test_invalid_negative_value(self):
        with pytest.raises(ValueError):
            calculate_aqi(pm25=-10)
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
  
  - repo: https://github.com/psf/black
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    hooks:
      - id: flake8
        args: [--max-line-length=100]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
        args: [--strict]
```

---

## Infrastructure Setup

### Terraform Modules

**S3 Buckets**:
```hcl
# infrastructure/terraform/modules/s3/main.tf

resource "aws_s3_bucket" "bronze" {
  bucket = "${var.environment}-air-quality-bronze"
  
  lifecycle_rule {
    enabled = true
    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
  }
}

resource "aws_s3_bucket" "silver" {
  bucket = "${var.environment}-air-quality-silver"
}

resource "aws_s3_bucket" "gold" {
  bucket = "${var.environment}-air-quality-gold"
}
```

**Kinesis Stream**:
```hcl
# infrastructure/terraform/modules/kinesis/main.tf

resource "aws_kinesis_stream" "air_quality_stream" {
  name             = "air-quality-measurements"
  shard_count      = var.shard_count
  retention_period = 24
  
  shard_level_metrics = [
    "IncomingBytes",
    "OutgoingBytes",
  ]
}
```

**DynamoDB**:
```hcl
# infrastructure/terraform/modules/dynamodb/main.tf

resource "aws_dynamodb_table" "speed_layer" {
  name           = "air-quality-realtime"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "city_id"
  range_key      = "timestamp"
  
  attribute {
    name = "city_id"
    type = "S"
  }
  
  attribute {
    name = "timestamp"
    type = "N"
  }
  
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}
```

### LocalStack Configuration

```yaml
# infrastructure/docker/docker-compose.yml

services:
  localstack:
    image: localstack/localstack:latest
    ports:
      - "4566:4566"
    environment:
      - SERVICES=s3,kinesis,dynamodb,lambda
      - DEBUG=1
      - DATA_DIR=/tmp/localstack/data
      - LAMBDA_EXECUTOR=docker
      - DOCKER_HOST=unix:///var/run/docker.sock
    volumes:
      - "./localstack-data:/tmp/localstack"
      - "/var/run/docker.sock:/var/run/docker.sock"
  
  airflow-webserver:
    image: apache/airflow:2.7.0-python3.10
    depends_on:
      - postgres
      - redis
    environment:
      - AIRFLOW__CORE__EXECUTOR=CeleryExecutor
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow
      - AIRFLOW__CELERY__BROKER_URL=redis://:@redis:6379/0
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./airflow/logs:/opt/airflow/logs
      - ./airflow/plugins:/opt/airflow/plugins
    ports:
      - "8080:8080"
  
  spark-master:
    image: bitnami/spark:3.5.0
    environment:
      - SPARK_MODE=master
      - SPARK_MASTER_HOST=spark-master
    ports:
      - "8081:8080"
      - "7077:7077"
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=airflow
      - POSTGRES_PASSWORD=airflow
      - POSTGRES_DB=airflow
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres-data:
```

---

## Pipeline Implementation

### Airflow DAG: Batch Pipeline

```python
# src/orchestration/airflow/dags/batch_pipeline_dag.py

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

default_args = {
    "owner": "data-engineering",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
}

with DAG(
    dag_id="batch_air_quality_pipeline",
    default_args=default_args,
    description="Daily batch processing of air quality data",
    schedule_interval="0 2 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["batch", "air-quality"],
) as dag:
    
    validate_raw_data = PythonOperator(
        task_id="validate_raw_data",
        python_callable=validate_bronze_layer,
    )
    
    bronze_to_silver = SparkSubmitOperator(
        task_id="bronze_to_silver",
        application="src/processing/spark/jobs/bronze_to_silver.py",
        conf={
            "spark.sql.shuffle.partitions": "200",
            "spark.sql.adaptive.enabled": "true",
        },
    )
    
    data_quality_checks = PythonOperator(
        task_id="data_quality_checks",
        python_callable=run_great_expectations,
    )
    
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="cd src/transformation/dbt && dbt run --profiles-dir .",
    )
    
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="cd src/transformation/dbt && dbt test --profiles-dir .",
    )
    
    validate_raw_data >> bronze_to_silver >> data_quality_checks >> dbt_run >> dbt_test
```

### Spark Job: Bronze to Silver

```python
# src/processing/spark/jobs/bronze_to_silver.py

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from delta import configure_spark_with_delta_pip

from src.common.config import Config
from src.processing.spark.transformations.cleansing import (
    remove_nulls,
    deduplicate,
    normalize_strings,
    validate_ranges,
)

def create_spark_session() -> SparkSession:
    builder = (
        SparkSession.builder
        .appName("BronzeToSilver")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()

def read_bronze_layer(spark: SparkSession, execution_date: str) -> DataFrame:
    path = f"{Config.S3_BRONZE_PATH}/year={execution_date[:4]}/month={execution_date[5:7]}/day={execution_date[8:10]}/"
    return spark.read.parquet(path)

def process_bronze_to_silver(df: DataFrame) -> DataFrame:
    return (
        df
        .transform(remove_nulls, critical_columns=["city_id", "timestamp", "pm25_value"])
        .transform(deduplicate, key_columns=["city_id", "timestamp"])
        .transform(normalize_strings, columns=["city_name", "country_name"])
        .transform(validate_ranges)
    )

def write_silver_layer(df: DataFrame, mode: str = "append"):
    (
        df.write
        .format("delta")
        .mode(mode)
        .partitionBy("country_code", "date")
        .option("mergeSchema", "true")
        .save(Config.S3_SILVER_PATH)
    )

def main():
    spark = create_spark_session()
    execution_date = spark.conf.get("spark.execution_date")
    
    bronze_df = read_bronze_layer(spark, execution_date)
    silver_df = process_bronze_to_silver(bronze_df)
    write_silver_layer(silver_df)

if __name__ == "__main__":
    main()
```

### dbt Model: Fact Table

```sql
-- src/transformation/dbt/models/marts/facts/fact_air_quality_measurements.sql

{{
    config(
        materialized='incremental',
        unique_key='measurement_key',
        partition_by={
            "field": "measurement_timestamp",
            "data_type": "timestamp",
            "granularity": "month"
        },
        on_schema_change='fail'
    )
}}

WITH source AS (
    SELECT * FROM {{ ref('stg_air_quality_measurements') }}
    {% if is_incremental() %}
    WHERE measurement_timestamp > (SELECT MAX(measurement_timestamp) FROM {{ this }})
    {% endif %}
),

enriched AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['city_id', 'measurement_timestamp']) }} AS measurement_key,
        l.location_key,
        t.time_key,
        s.pm25_value,
        s.pm10_value,
        s.no2_value,
        s.so2_value,
        s.co_value,
        s.o3_value,
        {{ calculate_aqi('s.pm25_value', 's.pm10_value', 's.no2_value', 's.so2_value', 's.co_value', 's.o3_value') }} AS aqi_value,
        {{ aqi_category('aqi_value') }} AS aqi_category,
        {{ dominant_pollutant('s.pm25_value', 's.pm10_value', 's.no2_value', 's.so2_value', 's.co_value', 's.o3_value') }} AS dominant_pollutant,
        s.temperature_c,
        s.humidity_pct,
        s.wind_speed_kmh,
        s.measurement_timestamp,
        s.source_system
    FROM source s
    LEFT JOIN {{ ref('dim_location') }} l
        ON s.city_id = l.city_id
        AND s.measurement_timestamp BETWEEN l.valid_from AND COALESCE(l.valid_to, '9999-12-31')
    LEFT JOIN {{ ref('dim_time') }} t
        ON DATE_TRUNC('hour', s.measurement_timestamp) = t.full_datetime
)

SELECT * FROM enriched
```

---

## Data Quality Framework

### Great Expectations Expectation Suite

```python
# src/data_quality/great_expectations/expectations/silver_layer_suite.py

from great_expectations.core import ExpectationConfiguration

expectations = [
    ExpectationConfiguration(
        expectation_type="expect_table_row_count_to_be_between",
        kwargs={"min_value": 100000, "max_value": 15000000}
    ),
    ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "city_id"}
    ),
    ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_between",
        kwargs={
            "column": "pm25_value",
            "min_value": 0,
            "max_value": 500,
            "mostly": 0.99
        }
    ),
    ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={
            "column": "aqi_category",
            "value_set": ["Good", "Moderate", "Unhealthy for Sensitive Groups", "Unhealthy", "Very Unhealthy", "Hazardous"]
        }
    ),
    ExpectationConfiguration(
        expectation_type="expect_column_values_to_match_regex",
        kwargs={
            "column": "country_code",
            "regex": "^[A-Z]{2}$"
        }
    ),
]
```

### dbt Tests

```yaml
# src/transformation/dbt/models/marts/facts/fact_air_quality_measurements.yml

version: 2

models:
  - name: fact_air_quality_measurements
    description: "Fact table for air quality measurements"
    columns:
      - name: measurement_key
        description: "Surrogate key"
        tests:
          - unique
          - not_null
      
      - name: location_key
        description: "Foreign key to dim_location"
        tests:
          - not_null
          - relationships:
              to: ref('dim_location')
              field: location_key
      
      - name: aqi_value
        description: "Air Quality Index (0-500)"
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= 0 AND <= 500"
      
      - name: aqi_category
        description: "AQI category label"
        tests:
          - accepted_values:
              values: ['Good', 'Moderate', 'Unhealthy for Sensitive Groups', 'Unhealthy', 'Very Unhealthy', 'Hazardous']
```

---

## Monitoring & Observability

### Metrics to Track

**Pipeline Health**:
- DAG success rate (target: >99%)
- Task duration (p50, p95, p99)
- Data freshness (max lag from source to warehouse)
- Backfill duration

**Data Quality**:
- Completeness score (% non-null critical fields)
- Validity score (% values in expected ranges)
- Uniqueness score (% duplicate records)
- Timeliness (% on-time arrivals)

**System Resources**:
- Spark job memory/CPU utilization
- Database connection pool usage
- S3 request rate and latency
- Kinesis shard utilization

### Grafana Dashboard Panels

**Panel 1: Pipeline Overview**
- Success/Failure rate (last 30 days)
- Average task duration by DAG
- Active DAG runs

**Panel 2: Data Volume**
- Records processed per day
- Bronze/Silver/Gold layer sizes
- Stream throughput (msgs/sec)

**Panel 3: Data Quality**
- Quality score trend
- Failed expectations by type
- Anomaly detection alerts

**Panel 4: System Health**
- CPU/Memory usage by service
- Database query latency
- S3 operation latency

---

## Setup Instructions

### Prerequisites

- Docker Desktop 4.20+
- Terraform 1.5+
- Python 3.10+
- AWS CLI (configured for LocalStack)
- Make

### Quick Start

```bash
# Clone repository
git clone <repo-url>
cd global-air-quality

# Install Python dependencies
make install

# Start infrastructure (LocalStack, Airflow, Spark, PostgreSQL)
make infra-up

# Provision AWS resources with Terraform
make terraform-apply

# Generate sample data (50 MB, suitable for GitHub)
make generate-data MODE=sample

# Upload data to S3 (LocalStack)
make upload-data

# Initialize dbt
make dbt-init

# Run full pipeline
make pipeline-run

# Access UIs
# Airflow: http://localhost:8080
# Spark: http://localhost:8081
# Grafana: http://localhost:3000
```

### Full-Scale Testing

```bash
# Generate full dataset (1.5 GB, ~13M records)
make generate-data MODE=full

# Upload to S3
make upload-data

# Run Spark job (will utilize distributed processing)
make spark-submit JOB=bronze_to_silver

# Verify PySpark performance improvement over Pandas
make benchmark
```

### Cleanup

```bash
# Stop all containers
make infra-down

# Destroy Terraform resources
make terraform-destroy

# Clean generated data
make clean-data
```

---


---
