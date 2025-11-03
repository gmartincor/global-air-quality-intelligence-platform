# Phase 6: Data Quality Framework

**Duration**: 1 week  
**Prerequisites**: Phase 3-4 completed, data flowing through pipeline

---

## Objectives

- Implement Great Expectations for data validation
- Create expectation suites for Bronze, Silver, Gold layers
- Add custom dbt tests
- Build data quality monitoring dashboard
- Achieve >95% quality score

---

## Architecture & Design Principles

**Modular Structure**: Separate concerns into distinct modules
- Expectation definitions (Bronze, Silver, Gold suites)
- Validation runner (orchestration)
- Metrics tracking (observability)
- Airflow integration (scheduling)

**SOLID Application**:
- **SRP**: Each module has single responsibility (expectation creation, validation execution, metrics storage)
- **OCP**: Add new expectations without modifying existing runner
- **DIP**: Depend on Great Expectations abstraction, not implementation details

**DRY**: Reuse validation logic across layers, centralize expectation configuration

---

## Tasks Breakdown

### 6.1 Great Expectations Setup

**Responsibility**: Configure Great Expectations context with datasources for Silver (S3) and Gold (PostgreSQL) layers

**Directory Structure**:
```
src/data_quality/
├── great_expectations/
│   ├── great_expectations.yml
│   ├── expectations/
│   ├── checkpoints/
│   └── plugins/
└── validators/
    ├── __init__.py
    ├── schema_validator.py
    └── business_rules_validator.py
```

**Configuration Requirements** (`great_expectations.yml`):
- Configure two datasources:
  - `silver_layer_s3`: SparkDFExecutionEngine for S3 data
  - `postgres_warehouse`: SqlAlchemyExecutionEngine for PostgreSQL
- Define stores for expectations and validations (filesystem-based)
- Enable RuntimeDataConnector for programmatic batch creation

---

### 6.2 Expectation Suites

**Module**: `src/data_quality/expectations/`

**Responsibility**: Define data validation rules for each medallion layer (Bronze, Silver, Gold)

**Bronze Layer Expectations** (`bronze_suite.py`):
- Function: `create_bronze_layer_expectations() -> list[ExpectationConfiguration]`
- Validations:
  - Row count between 1,000 and 20,000,000
  - NOT NULL: city_id, timestamp, pm25_value
  - Regex patterns: city_id format (^[A-Z]{3}\d{3}$), country_code format (^[A-Z]{2}$)

**Silver Layer Expectations** (`silver_suite.py`):
- Function: `create_silver_layer_expectations() -> list[ExpectationConfiguration]`
- Validations:
  - pm25_value range: [0, 500], 99% compliance
  - pm10_value range: [0, 600], 99% compliance
  - latitude/longitude ranges: [-90, 90], [-180, 180]
  - aqi_category values in set: ["Good", "Moderate", "Unhealthy for Sensitive Groups", "Unhealthy", "Very Unhealthy", "Hazardous"]
  - Composite uniqueness: (city_id, timestamp) 99.9% unique
  - pm25_value mean between 5 and 150

**Gold Layer Expectations** (`gold_suite.py`):
- Function: `create_gold_layer_expectations() -> list[ExpectationConfiguration]`
- Validations:
  - NOT NULL + UNIQUE: measurement_key
  - NOT NULL: location_key, time_key
  - aqi_value range: [0, 500]
  - Compound uniqueness: (location_key, measurement_timestamp)

---

### 6.3 Data Quality Runner

**Module**: `src/data_quality/quality_runner.py`

**Class**: `DataQualityRunner`

**Responsibilities**:
- Initialize Great Expectations context
- Create expectation suites programmatically
- Execute validations against datasources
- Return structured results (success rate, expectation counts)

**Key Methods**:
- `__init__()`: Load GE context from project directory
- `create_expectation_suite(suite_name, expectations)`: Create/update suite with expectation list
- `run_validation(datasource_name, asset_name, suite_name, batch_data=None)`: Execute validation, return statistics
- `setup_all_suites()`: Create Bronze, Silver, Gold suites using factory functions

**Return Contract** (validation results):
```python
{
    "success": bool,
    "success_rate": float,
    "evaluated_expectations": int,
    "successful_expectations": int,
    "unsuccessful_expectations": int
}
```

---

### 6.4 Custom dbt Tests

**Location**: `src/transformation/dbt/tests/`

**Purpose**: SQL-based data quality tests integrated with dbt workflow

**Test Files**:

1. **assert_aqi_range.sql**: Validate AQI values within [0, 500]
   - Select invalid records from fact_air_quality_measurements
   - Test fails if any rows returned

2. **assert_no_future_dates.sql**: Prevent future timestamps
   - Filter measurements with timestamp > CURRENT_TIMESTAMP
   - Ensures data integrity

3. **assert_location_consistency.sql**: Detect location coordinate changes
   - Identify cities with multiple lat/lon values (invalid state)
   - Uses CTE to count distinct coordinates per city_id

**Custom Macro** (`macros/test_accepted_ratio.sql`):
- Test: `accepted_ratio(model, column_name, condition, threshold=0.95)`
- Purpose: Validate percentage of rows meeting condition exceeds threshold
- Implementation: CTE-based ratio calculation with configurable threshold

---

### 6.5 Airflow Integration

**Module**: `src/orchestration/airflow/dags/data_quality_dag.py`

**Responsibility**: Schedule and orchestrate daily data quality validations

**DAG Configuration**:
- ID: `data_quality_validation`
- Schedule: Daily at 4 AM (`0 4 * * *`)
- Start date: 2024-01-01
- Catchup: False
- Retries: 1 (5-minute delay)

**Tasks**:

1. **validate_silver_layer** (PythonOperator):
   - Function: `run_silver_validation()`
   - Action: Execute Silver layer expectation suite
   - Failure handling: Raise ValueError if success_rate < threshold

2. **validate_gold_layer** (PythonOperator):
   - Function: `run_gold_validation()`
   - Action: Execute Gold layer expectation suite against PostgreSQL
   - Failure handling: Raise ValueError if validation fails

**Dependencies**: validate_silver >> validate_gold

---

### 6.6 Quality Metrics Tracking

**Module**: `src/data_quality/metrics_tracker.py`

**Class**: `QualityMetricsTracker`

**Responsibilities**:
- Create PostgreSQL table for quality metrics history
- Record validation results with metadata
- Query quality trends over time

**Database Schema** (`data_quality_metrics`):
```
id SERIAL PRIMARY KEY
layer VARCHAR(50)
suite_name VARCHAR(100)
execution_timestamp TIMESTAMP
success BOOLEAN
success_rate DECIMAL(5,2)
total_expectations INTEGER
successful_expectations INTEGER
failed_expectations INTEGER
```

**Key Methods**:
- `__init__()`: Connect to PostgreSQL, create metrics table if not exists
- `record_validation_result(layer, suite_name, results)`: Insert validation outcome
- `get_quality_trend(layer, days=7)`: Query average/min/max quality scores by day

---

## Validation Steps

### 1. Setup Expectation Suites
```bash
poetry run python -m src.data_quality.quality_runner
```

### 2. Run Quality Checks
```bash
poetry run python -m src.data_quality.quality_runner
```

### 3. Trigger Quality DAG
```bash
docker exec airflow-webserver airflow dags trigger data_quality_validation
```

### 4. Check Quality Metrics
```sql
SELECT * FROM data_quality_metrics ORDER BY execution_timestamp DESC LIMIT 10;
```

---

## Deliverables Checklist

- [ ] Great Expectations configured
- [ ] Expectation suites (Bronze, Silver, Gold)
- [ ] Custom dbt tests
- [ ] Quality metrics tracking
- [ ] Airflow quality validation DAG
- [ ] Quality checks running successfully
- [ ] Quality score >95%

---

## Next Phase

Proceed to [Phase 7: Monitoring & Observability](./phase7_monitoring.md)

---

## Validation Steps

### 1. Setup Expectation Suites
```bash
poetry run python -m src.data_quality.quality_runner
```

### 2. Run Quality Checks
```bash
poetry run python -m src.data_quality.quality_runner
```

### 3. Trigger Quality DAG
```bash
docker exec airflow-webserver airflow dags trigger data_quality_validation
```

### 4. Check Quality Metrics
```sql
SELECT * FROM data_quality_metrics ORDER BY execution_timestamp DESC LIMIT 10;
```

---

## Deliverables Checklist

- [ ] Great Expectations configured
- [ ] Expectation suites (Bronze, Silver, Gold)
- [ ] Custom dbt tests
- [ ] Quality metrics tracking
- [ ] Airflow quality validation DAG
- [ ] Quality checks running successfully
- [ ] Quality score >95%

---

## Next Phase

Proceed to [Phase 7: Monitoring & Observability](./phase7_monitoring.md)
