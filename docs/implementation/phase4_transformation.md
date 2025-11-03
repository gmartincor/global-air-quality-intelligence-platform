# Phase 4: Data Transformation & Modeling

**Duration**: 1.5 weeks  
**Prerequisites**: Phase 3 completed, Silver layer populated

## Objectives

- Implement dimensional model using dbt
- Apply DRY principle with reusable macros
- Build incremental models for performance
- Implement data quality tests

## Tasks Breakdown

### 4.1 Project Configuration

**Directory Structure**:
```
src/transformation/dbt/
├── dbt_project.yml          # Project configuration
├── profiles.yml             # Database connection
├── models/
│   ├── staging/             # Minimal transformations
│   │   └── stg_measurements.sql
│   └── marts/               # Business layer
│       ├── dim_location.sql
│       ├── dim_time.sql
│       ├── fact_measurements.sql
│       └── agg_daily.sql
├── macros/                  # Reusable logic (DRY)
│   ├── common.sql
│   └── aqi.sql
└── tests/                   # Data quality tests
    └── data_quality.sql
```

**Key Configuration** (`dbt_project.yml`):
- Models: staging → views, marts → tables
- Materialization strategy: views for staging (fast refresh), tables for marts (query performance)
- Tags: production models for selective runs

**Database Profile** (`profiles.yml`):
- Target environment: dev/prod
- Connection: PostgreSQL warehouse
- Threads: 4 parallel model builds

### 4.2 Reusable Macros (DRY Principle)

**Purpose**: Centralize repeated logic to avoid duplication across models

**Macros to Implement** (`macros/common.sql`):

1. **`generate_surrogate_key(columns)`**
   - Input: List of column names
   - Output: MD5 hash of concatenated values
   - Usage: Generate unique keys for dimensions/facts

2. **`incremental_filter(timestamp_col)`**
   - Input: Timestamp column name (default: 'measurement_timestamp')
   - Output: WHERE clause for incremental loads
   - Logic: Filter records newer than max timestamp in existing table
   - Usage: Efficient incremental processing

3. **`add_audit_columns()`**
   - Input: None
   - Output: SQL for processed_at, processing_date columns
   - Usage: Track data lineage

**Business Logic Macros** (`macros/aqi.sql`):

1. **`aqi_category(aqi_col)`**
   - Input: AQI value column
   - Output: CASE statement returning category (Good/Moderate/Unhealthy/...)
   - Ranges: 0-50 Good, 51-100 Moderate, 101-150 Unhealthy for Sensitive Groups, etc.

2. **`dominant_pollutant()`**
   - Input: Pollutant columns (pm25, pm10, no2, so2, co, o3)
   - Output: CASE statement returning pollutant with highest value
   - Logic: Compare all pollutant values, return max


### 4.3 Staging Layer

**Model**: `stg_measurements.sql`

**Purpose**: Minimal transformation layer - rename columns, basic type casting

**Transformations**:
- Source: Silver layer Delta table
- Select and rename columns to standardized names
- Apply incremental filter using `incremental_filter()` macro
- No business logic at this layer (SRP)

**Materialization**: View (fast refresh, used as source for marts)


### 4.4 Dimension Models

**Model**: `dim_location.sql` (SCD Type 2)

**Purpose**: Track location changes over time with version history

**Key Features**:
- Surrogate key: `location_key` (generated with `generate_surrogate_key()`)
- Business key: `city_id`
- Attributes: city_name, country_name, country_code, latitude, longitude
- SCD columns: valid_from, valid_to, is_current, version
- Incremental logic: Detect changes in attributes, create new version if changed
- Materialization: Incremental table

**Model**: `dim_time.sql`

**Purpose**: Pre-populated time dimension for fast joins

**Key Features**:
- Grain: Hourly (one row per hour from 2020-2030)
- Key: `time_key` (format: YYYYMMDDHH24 as integer)
- Attributes: year, quarter, month, week, day, hour, is_weekend, is_business_hour
- Generation: Recursive CTE generating all hours in range
- Materialization: Table (static, no incremental needed)
- Indexes: On date and full_datetime for query performance


### 4.5 Fact Tables

**Model**: `fact_measurements.sql`

**Purpose**: Core fact table with measurement data and foreign keys to dimensions

**Design**:
- Grain: One row per measurement (city + timestamp)
- Keys: measurement_key (surrogate), location_key, time_key (foreign keys)
- Measures: pm25, pm10, no2, so2, co, o3, aqi_value, temperature, humidity, wind_speed
- Derived columns: aqi_category (using `aqi_category()` macro), dominant_pollutant (using macro)
- Joins: Left join to dim_location and dim_time
- Incremental: Filter by timestamp using `incremental_filter()` macro
- Partition: By measurement_timestamp (monthly) for query performance
- Materialization: Incremental table

**Model**: `agg_daily.sql`

**Purpose**: Pre-aggregated daily metrics for faster analytics

**Design**:
- Grain: One row per location per day
- Keys: location_key, date
- Aggregations: avg/max/min AQI, count of hours by category (good/moderate/unhealthy)
- Derived: dominant_pollutant_mode (most frequent pollutant each day)
- Source: Aggregated from fact_measurements
- Incremental: Process only new days
- Materialization: Incremental table with composite unique key


### 4.6 Data Quality Tests

**Built-in dbt Tests** (via schema.yml):
- not_null: city_id, measurement_timestamp, pm25_value in staging
- unique: location_key, time_key, measurement_key
- relationships: fact foreign keys to dimension primary keys

**Custom SQL Test** (`tests/data_quality.sql`):
- Purpose: Validate AQI value range and timestamp sanity
- Logic: Select invalid records (AQI <0 or >500, future timestamps)
- Execution: Fails if any rows returned


### 4.7 Airflow DAG Integration

**Purpose**: Orchestrate dbt transformation runs daily

**Tasks**:
1. **dbt_run**: Execute all models (BashOperator)
   - Command: `dbt run --profiles-dir .`
   - Working directory: dbt project root
   
2. **dbt_test**: Run all tests (BashOperator)
   - Command: `dbt test --profiles-dir .`
   - Dependency: Runs after dbt_run

**Schedule**: Daily at 3 AM (after batch pipeline completes)
**Retry**: 2 attempts with 5-min delay


### 4.8 Automation

**Makefile Commands**:
```makefile
dbt-run:
	cd src/transformation/dbt && dbt run --profiles-dir .

dbt-test:
	cd src/transformation/dbt && dbt test --profiles-dir .
```

**Usage**:
- `make dbt-run`: Execute all transformations locally
- `make dbt-test`: Validate data quality

## Validation Steps

### 1. Run dbt Models
```bash
make dbt-run
```
**Expected**: All models build successfully, staging → dimensions → facts

### 2. Run dbt Tests
```bash
make dbt-test
```
**Expected**: All tests pass (0 failures)

### 3. Verify Tables
```sql
SELECT COUNT(*) FROM marts.dim_location;
SELECT COUNT(*) FROM marts.dim_time;
SELECT COUNT(*) FROM marts.fact_measurements;
SELECT COUNT(*) FROM marts.agg_daily;
```
**Expected**: Non-zero counts, fact > daily aggregates



## Design Principles Applied

**SOLID**:
- **SRP**: Each model has one purpose (staging, dimension, fact, aggregate)
- **OCP**: Add new models without modifying existing ones
- **DIP**: Models depend on dbt `ref()` abstraction, not hardcoded tables

**DRY**:
- Macros eliminate SQL duplication (surrogate keys, incremental logic, AQI categorization)
- Common audit columns centralized in macro
- Shared incremental pattern across all models

**KISS**:
- Simple model structure (source → staging → marts)
- Clear naming conventions (stg_, dim_, fact_, agg_)
- Minimal configuration overhead

**YAGNI**:
- No unnecessary intermediate layers
- No complex schemas where simple works
- SCD Type 2 only for location (where needed)
- Removed verbose YAML documentation

## Deliverables

- [ ] dbt project configured (dbt_project.yml, profiles.yml)
- [ ] Reusable macros implemented (common, AQI logic)
- [ ] Staging layer (minimal transformations)
- [ ] Dimension models (location with SCD2, time with hourly grain)
- [ ] Fact tables (measurements, daily aggregates)
- [ ] Data quality tests (built-in + custom SQL)
- [ ] Airflow DAG for orchestration
- [ ] All models running successfully
- [ ] Tests passing

## Next Phase

[Phase 5: Streaming Pipeline](./phase5_streaming.md)
````
