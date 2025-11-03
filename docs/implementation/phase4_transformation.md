# Phase 4: Data Transformation & Modeling

**Duration**: 1.5 weeks  
**Prerequisites**: Phase 3 completed, Silver layer populated

---

## Objectives

- Implement dbt dimensional model (star schema)
- Create staging, intermediate, and marts layers
- Build SCD Type 2 for dim_location
- Implement incremental models for performance
- Add dbt tests for data quality

---

## Tasks Breakdown

### 4.1 dbt Project Setup

**Directory Structure**:
```
src/transformation/dbt/
├── dbt_project.yml
├── profiles.yml
├── models/
│   ├── staging/
│   │   ├── _staging.yml
│   │   └── stg_air_quality_measurements.sql
│   ├── intermediate/
│   │   ├── _intermediate.yml
│   │   └── int_measurements_enriched.sql
│   └── marts/
│       ├── dimensions/
│       │   ├── dim_location.sql
│       │   ├── dim_time.sql
│       │   └── _dimensions.yml
│       └── facts/
│           ├── fact_air_quality_measurements.sql
│           ├── agg_daily_air_quality.sql
│           └── _facts.yml
├── macros/
│   ├── generate_schema_name.sql
│   ├── calculate_aqi.sql
│   └── aqi_category.sql
└── tests/
    └── assert_aqi_range.sql
```

**File**: `src/transformation/dbt/dbt_project.yml`

```yaml
name: 'air_quality_analytics'
version: '1.0.0'
config-version: 2

profile: 'air_quality'

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

target-path: "target"
clean-targets:
  - "target"
  - "dbt_packages"

models:
  air_quality_analytics:
    staging:
      +materialized: view
      +schema: staging
    intermediate:
      +materialized: view
      +schema: intermediate
    marts:
      +materialized: table
      dimensions:
        +schema: dimensions
      facts:
        +schema: facts
        +partition_by:
          field: measurement_timestamp
          data_type: timestamp
          granularity: month

vars:
  current_timestamp: "CURRENT_TIMESTAMP"
```

**File**: `src/transformation/dbt/profiles.yml`

```yaml
air_quality:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      user: airflow
      password: airflow
      port: 5432
      dbname: air_quality_warehouse
      schema: public
      threads: 4
      keepalives_idle: 0
```

---

### 4.2 Staging Models

**File**: `src/transformation/dbt/models/staging/stg_air_quality_measurements.sql`

```sql
WITH source AS (
    SELECT * FROM {{ source('silver_layer', 'air_quality') }}
),

renamed AS (
    SELECT
        city_id,
        city_name,
        country_name,
        country_code,
        latitude,
        longitude,
        timestamp AS measurement_timestamp,
        pm25_value,
        pm10_value,
        no2_value,
        so2_value,
        co_value,
        o3_value,
        aqi_value,
        aqi_category,
        temperature_c,
        humidity_pct,
        wind_speed_kmh,
        date,
        processed_at
    FROM source
)

SELECT * FROM renamed
```

**File**: `src/transformation/dbt/models/staging/_staging.yml`

```yaml
version: 2

sources:
  - name: silver_layer
    description: Delta Lake silver layer from S3
    tables:
      - name: air_quality
        identifier: air_quality
        columns:
          - name: city_id
            description: Unique identifier for city
            tests:
              - not_null
          - name: timestamp
            description: Measurement timestamp
            tests:
              - not_null

models:
  - name: stg_air_quality_measurements
    description: Staging layer for air quality measurements
    columns:
      - name: city_id
        tests:
          - not_null
      - name: measurement_timestamp
        tests:
          - not_null
      - name: pm25_value
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 500
```

---

### 4.3 Dimension Models

**File**: `src/transformation/dbt/models/marts/dimensions/dim_location.sql`

```sql
{{
    config(
        materialized='incremental',
        unique_key='location_key',
        on_schema_change='fail'
    )
}}

WITH source_data AS (
    SELECT DISTINCT
        city_id,
        city_name,
        country_name,
        country_code,
        latitude,
        longitude
    FROM {{ ref('stg_air_quality_measurements') }}
    {% if is_incremental() %}
    WHERE measurement_timestamp > (SELECT MAX(valid_from) FROM {{ this }})
    {% endif %}
),

existing_locations AS (
    {% if is_incremental() %}
    SELECT
        city_id,
        city_name,
        country_name,
        country_code,
        latitude,
        longitude
    FROM {{ this }}
    WHERE is_current = TRUE
    {% else %}
    SELECT NULL AS city_id LIMIT 0
    {% endif %}
),

changed_records AS (
    SELECT
        s.city_id,
        s.city_name,
        s.country_name,
        s.country_code,
        s.latitude,
        s.longitude
    FROM source_data s
    LEFT JOIN existing_locations e
        ON s.city_id = e.city_id
    WHERE e.city_id IS NULL
       OR s.city_name != e.city_name
       OR s.country_name != e.country_name
       OR s.latitude != e.latitude
       OR s.longitude != e.longitude
),

final AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['city_id', '{{ var("current_timestamp") }}']) }} AS location_key,
        city_id,
        city_name,
        country_name,
        country_code,
        latitude,
        longitude,
        {{ var("current_timestamp") }} AS valid_from,
        NULL::TIMESTAMP AS valid_to,
        TRUE AS is_current,
        1 AS version
    FROM changed_records
)

SELECT * FROM final
```

**File**: `src/transformation/dbt/models/marts/dimensions/dim_time.sql`

```sql
{{
    config(
        materialized='table',
        post_hook=[
            "CREATE INDEX IF NOT EXISTS idx_dim_time_date ON {{ this }} (date)",
            "CREATE INDEX IF NOT EXISTS idx_dim_time_datetime ON {{ this }} (full_datetime)"
        ]
    )
}}

WITH date_spine AS (
    {{ dbt_utils.date_spine(
        datepart="hour",
        start_date="'2020-01-01'::timestamp",
        end_date="'2030-12-31'::timestamp"
    )}}
),

final AS (
    SELECT
        TO_CHAR(date_hour, 'YYYYMMDDHH24')::INTEGER AS time_key,
        date_hour AS full_datetime,
        DATE(date_hour) AS date,
        EXTRACT(YEAR FROM date_hour)::INTEGER AS year,
        EXTRACT(QUARTER FROM date_hour)::INTEGER AS quarter,
        EXTRACT(MONTH FROM date_hour)::INTEGER AS month,
        TO_CHAR(date_hour, 'Month') AS month_name,
        EXTRACT(WEEK FROM date_hour)::INTEGER AS week_of_year,
        EXTRACT(DAY FROM date_hour)::INTEGER AS day_of_month,
        EXTRACT(ISODOW FROM date_hour)::INTEGER AS day_of_week,
        TO_CHAR(date_hour, 'Day') AS day_name,
        EXTRACT(HOUR FROM date_hour)::INTEGER AS hour,
        CASE WHEN EXTRACT(ISODOW FROM date_hour) IN (6, 7) THEN TRUE ELSE FALSE END AS is_weekend,
        FALSE AS is_holiday,
        CASE
            WHEN EXTRACT(MONTH FROM date_hour) IN (12, 1, 2) THEN 'Winter'
            WHEN EXTRACT(MONTH FROM date_hour) IN (3, 4, 5) THEN 'Spring'
            WHEN EXTRACT(MONTH FROM date_hour) IN (6, 7, 8) THEN 'Summer'
            ELSE 'Fall'
        END AS season,
        CASE
            WHEN EXTRACT(HOUR FROM date_hour) BETWEEN 8 AND 18
            AND EXTRACT(ISODOW FROM date_hour) < 6 THEN TRUE
            ELSE FALSE
        END AS is_business_hour
    FROM date_spine
)

SELECT * FROM final
```

**File**: `src/transformation/dbt/models/marts/dimensions/_dimensions.yml`

```yaml
version: 2

models:
  - name: dim_location
    description: Location dimension with SCD Type 2
    columns:
      - name: location_key
        description: Surrogate key
        tests:
          - unique
          - not_null
      - name: city_id
        description: Natural key
        tests:
          - not_null
      - name: is_current
        description: Current version flag
        tests:
          - not_null

  - name: dim_time
    description: Pre-populated time dimension
    columns:
      - name: time_key
        description: Surrogate key (YYYYMMDDHH format)
        tests:
          - unique
          - not_null
```

---

### 4.4 Fact Models

**File**: `src/transformation/dbt/models/marts/facts/fact_air_quality_measurements.sql`

```sql
{{
    config(
        materialized='incremental',
        unique_key='measurement_key',
        partition_by={
            "field": "measurement_timestamp",
            "data_type": "timestamp",
            "granularity": "month"
        }
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
        {{ dbt_utils.generate_surrogate_key(['s.city_id', 's.measurement_timestamp']) }} AS measurement_key,
        l.location_key,
        t.time_key,
        s.pm25_value,
        s.pm10_value,
        s.no2_value,
        s.so2_value,
        s.co_value,
        s.o3_value,
        s.aqi_value,
        s.aqi_category,
        CASE
            WHEN s.pm25_value >= s.pm10_value AND s.pm25_value >= s.no2_value AND s.pm25_value >= s.so2_value THEN 'PM25'
            WHEN s.pm10_value >= s.no2_value AND s.pm10_value >= s.so2_value THEN 'PM10'
            WHEN s.no2_value >= s.so2_value THEN 'NO2'
            ELSE 'SO2'
        END AS dominant_pollutant,
        s.temperature_c,
        s.humidity_pct,
        s.wind_speed_kmh,
        s.measurement_timestamp,
        'silver_layer' AS source_system
    FROM source s
    LEFT JOIN {{ ref('dim_location') }} l
        ON s.city_id = l.city_id
        AND s.measurement_timestamp >= l.valid_from
        AND (l.valid_to IS NULL OR s.measurement_timestamp < l.valid_to)
        AND l.is_current = TRUE
    LEFT JOIN {{ ref('dim_time') }} t
        ON DATE_TRUNC('hour', s.measurement_timestamp) = t.full_datetime
)

SELECT * FROM enriched
```

**File**: `src/transformation/dbt/models/marts/facts/agg_daily_air_quality.sql`

```sql
{{
    config(
        materialized='incremental',
        unique_key=['location_key', 'date']
    )
}}

WITH daily_aggregates AS (
    SELECT
        location_key,
        DATE(measurement_timestamp) AS date,
        AVG(aqi_value) AS avg_aqi,
        MAX(aqi_value) AS max_aqi,
        MIN(aqi_value) AS min_aqi,
        SUM(CASE WHEN aqi_category = 'Good' THEN 1 ELSE 0 END) AS hours_good,
        SUM(CASE WHEN aqi_category = 'Moderate' THEN 1 ELSE 0 END) AS hours_moderate,
        SUM(CASE WHEN aqi_category IN ('Unhealthy for Sensitive Groups', 'Unhealthy', 'Very Unhealthy') THEN 1 ELSE 0 END) AS hours_unhealthy,
        SUM(CASE WHEN aqi_category = 'Hazardous' THEN 1 ELSE 0 END) AS hours_hazardous,
        MODE() WITHIN GROUP (ORDER BY dominant_pollutant) AS dominant_pollutant_mode
    FROM {{ ref('fact_air_quality_measurements') }}
    {% if is_incremental() %}
    WHERE DATE(measurement_timestamp) > (SELECT MAX(date) FROM {{ this }})
    {% endif %}
    GROUP BY location_key, DATE(measurement_timestamp)
)

SELECT * FROM daily_aggregates
```

**File**: `src/transformation/dbt/models/marts/facts/_facts.yml`

```yaml
version: 2

models:
  - name: fact_air_quality_measurements
    description: Fact table for air quality measurements
    columns:
      - name: measurement_key
        description: Surrogate key
        tests:
          - unique
          - not_null
      - name: location_key
        description: FK to dim_location
        tests:
          - not_null
          - relationships:
              to: ref('dim_location')
              field: location_key
      - name: time_key
        description: FK to dim_time
        tests:
          - relationships:
              to: ref('dim_time')
              field: time_key
      - name: aqi_value
        description: Air Quality Index
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 500

  - name: agg_daily_air_quality
    description: Pre-aggregated daily air quality metrics
    tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - location_key
            - date
```

---

### 4.5 dbt Macros

**File**: `src/transformation/dbt/macros/generate_schema_name.sql`

```sql
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
```

---

### 4.6 Airflow Integration

**File**: `src/orchestration/airflow/dags/dbt_transformation_dag.py`

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="dbt_transformation_pipeline",
    default_args=default_args,
    description="dbt transformations for dimensional model",
    schedule_interval="0 3 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["dbt", "transformation"],
) as dag:
    
    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command="cd /opt/airflow/src/transformation/dbt && dbt deps --profiles-dir .",
    )
    
    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command="cd /opt/airflow/src/transformation/dbt && dbt seed --profiles-dir .",
    )
    
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="cd /opt/airflow/src/transformation/dbt && dbt run --profiles-dir .",
    )
    
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="cd /opt/airflow/src/transformation/dbt && dbt test --profiles-dir .",
    )
    
    dbt_deps >> dbt_seed >> dbt_run >> dbt_test
```

---

### 4.7 Makefile Updates

```makefile
.PHONY: dbt-init dbt-run dbt-test

dbt-init:
	cd src/transformation/dbt && dbt deps --profiles-dir .
	cd src/transformation/dbt && dbt seed --profiles-dir .

dbt-run:
	cd src/transformation/dbt && dbt run --profiles-dir .

dbt-test:
	cd src/transformation/dbt && dbt test --profiles-dir .
```

---

## Validation Steps

### 1. Install dbt Dependencies
```bash
make dbt-init
```

### 2. Run dbt Models
```bash
make dbt-run
```

### 3. Run dbt Tests
```bash
make dbt-test
```

### 4. Verify Dimensional Model
```sql
SELECT COUNT(*) FROM dimensions.dim_location;
SELECT COUNT(*) FROM dimensions.dim_time;
SELECT COUNT(*) FROM facts.fact_air_quality_measurements;
SELECT COUNT(*) FROM facts.agg_daily_air_quality;
```

---

## Deliverables Checklist

- [ ] dbt project initialized
- [ ] Staging models created
- [ ] Dimension models (dim_location SCD Type 2, dim_time)
- [ ] Fact models (fact measurements, daily aggregates)
- [ ] Incremental models configured
- [ ] dbt tests implemented
- [ ] Airflow DAG for dbt
- [ ] Models running successfully
- [ ] Tests passing

---

## Next Phase

Proceed to [Phase 5: Streaming Pipeline](./phase5_streaming.md)
