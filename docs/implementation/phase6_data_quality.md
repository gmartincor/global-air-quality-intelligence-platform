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

## Tasks Breakdown

### 6.1 Great Expectations Setup

**Directory Structure**:
```
src/data_quality/
├── great_expectations/
│   ├── great_expectations.yml
│   ├── expectations/
│   │   ├── bronze_layer_suite.json
│   │   ├── silver_layer_suite.json
│   │   └── gold_layer_suite.json
│   ├── checkpoints/
│   │   ├── bronze_checkpoint.yml
│   │   ├── silver_checkpoint.yml
│   │   └── gold_checkpoint.yml
│   └── plugins/
└── validators/
    ├── __init__.py
    ├── schema_validator.py
    └── business_rules_validator.py
```

**File**: `src/data_quality/great_expectations/great_expectations.yml`

```yaml
config_version: 3.0

datasources:
  silver_layer_s3:
    class_name: Datasource
    execution_engine:
      class_name: SparkDFExecutionEngine
    data_connectors:
      default_runtime_data_connector:
        class_name: RuntimeDataConnector
        batch_identifiers:
          - default_identifier_name

  postgres_warehouse:
    class_name: Datasource
    execution_engine:
      class_name: SqlAlchemyExecutionEngine
      connection_string: postgresql://airflow:airflow@localhost:5432/air_quality_warehouse
    data_connectors:
      default_inferred_data_connector:
        class_name: InferredAssetSqlDataConnector

stores:
  expectations_store:
    class_name: ExpectationsStore
    store_backend:
      class_name: TupleFilesystemStoreBackend
      base_directory: expectations/

  validations_store:
    class_name: ValidationsStore
    store_backend:
      class_name: TupleFilesystemStoreBackend
      base_directory: validations/

expectations_store_name: expectations_store
validations_store_name: validations_store
```

---

### 6.2 Expectation Suites

**File**: `src/data_quality/expectations/bronze_suite.py`

```python
from great_expectations.core import ExpectationConfiguration


def create_bronze_layer_expectations() -> list[ExpectationConfiguration]:
    return [
        ExpectationConfiguration(
            expectation_type="expect_table_row_count_to_be_between",
            kwargs={
                "min_value": 1000,
                "max_value": 20000000
            }
        ),
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_not_be_null",
            kwargs={"column": "city_id"}
        ),
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_not_be_null",
            kwargs={"column": "timestamp"}
        ),
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_not_be_null",
            kwargs={"column": "pm25_value"}
        ),
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_match_regex",
            kwargs={
                "column": "city_id",
                "regex": "^[A-Z]{3}\\d{3}$"
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

**File**: `src/data_quality/expectations/silver_suite.py`

```python
from great_expectations.core import ExpectationConfiguration


def create_silver_layer_expectations() -> list[ExpectationConfiguration]:
    return [
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
            expectation_type="expect_column_values_to_be_between",
            kwargs={
                "column": "pm10_value",
                "min_value": 0,
                "max_value": 600,
                "mostly": 0.99
            }
        ),
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={
                "column": "latitude",
                "min_value": -90,
                "max_value": 90
            }
        ),
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={
                "column": "longitude",
                "min_value": -180,
                "max_value": 180
            }
        ),
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_in_set",
            kwargs={
                "column": "aqi_category",
                "value_set": [
                    "Good",
                    "Moderate",
                    "Unhealthy for Sensitive Groups",
                    "Unhealthy",
                    "Very Unhealthy",
                    "Hazardous"
                ]
            }
        ),
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_unique",
            kwargs={
                "column": ["city_id", "timestamp"],
                "mostly": 0.999
            }
        ),
        ExpectationConfiguration(
            expectation_type="expect_column_mean_to_be_between",
            kwargs={
                "column": "pm25_value",
                "min_value": 5,
                "max_value": 150
            }
        ),
    ]
```

**File**: `src/data_quality/expectations/gold_suite.py`

```python
from great_expectations.core import ExpectationConfiguration


def create_gold_layer_expectations() -> list[ExpectationConfiguration]:
    return [
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_not_be_null",
            kwargs={"column": "measurement_key"}
        ),
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_unique",
            kwargs={"column": "measurement_key"}
        ),
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_not_be_null",
            kwargs={"column": "location_key"}
        ),
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_not_be_null",
            kwargs={"column": "time_key"}
        ),
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={
                "column": "aqi_value",
                "min_value": 0,
                "max_value": 500
            }
        ),
        ExpectationConfiguration(
            expectation_type="expect_compound_columns_to_be_unique",
            kwargs={
                "column_list": ["location_key", "measurement_timestamp"]
            }
        ),
    ]
```

---

### 6.3 Data Quality Runner

**File**: `src/data_quality/quality_runner.py`

```python
from pathlib import Path
from typing import Dict, Any
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest

from src.common.config import config
from src.common.logger import setup_logger
from src.data_quality.expectations.bronze_suite import create_bronze_layer_expectations
from src.data_quality.expectations.silver_suite import create_silver_layer_expectations
from src.data_quality.expectations.gold_suite import create_gold_layer_expectations

logger = setup_logger(__name__)


class DataQualityRunner:
    
    def __init__(self):
        ge_root = Path(__file__).parent / "great_expectations"
        self.context = gx.get_context(context_root_dir=str(ge_root))
    
    def create_expectation_suite(
        self,
        suite_name: str,
        expectations: list
    ):
        try:
            self.context.delete_expectation_suite(suite_name)
        except:
            pass
        
        suite = self.context.create_expectation_suite(
            expectation_suite_name=suite_name,
            overwrite_existing=True
        )
        
        for expectation in expectations:
            suite.add_expectation(expectation)
        
        self.context.save_expectation_suite(suite)
        logger.info(f"Created expectation suite: {suite_name}")
    
    def run_validation(
        self,
        datasource_name: str,
        asset_name: str,
        suite_name: str,
        batch_data: Any = None
    ) -> Dict:
        
        if batch_data is not None:
            batch_request = RuntimeBatchRequest(
                datasource_name=datasource_name,
                data_connector_name="default_runtime_data_connector",
                data_asset_name=asset_name,
                runtime_parameters={"batch_data": batch_data},
                batch_identifiers={"default_identifier_name": "default_identifier"}
            )
            
            validator = self.context.get_validator(
                batch_request=batch_request,
                expectation_suite_name=suite_name
            )
        else:
            validator = self.context.get_validator(
                datasource_name=datasource_name,
                data_asset_name=asset_name,
                expectation_suite_name=suite_name
            )
        
        results = validator.validate()
        
        success_rate = results.statistics["success_percent"]
        logger.info(f"Validation complete: {success_rate:.2f}% success")
        
        return {
            "success": results.success,
            "success_rate": success_rate,
            "evaluated_expectations": results.statistics["evaluated_expectations"],
            "successful_expectations": results.statistics["successful_expectations"],
            "unsuccessful_expectations": results.statistics["unsuccessful_expectations"]
        }
    
    def setup_all_suites(self):
        self.create_expectation_suite(
            "bronze_layer_suite",
            create_bronze_layer_expectations()
        )
        self.create_expectation_suite(
            "silver_layer_suite",
            create_silver_layer_expectations()
        )
        self.create_expectation_suite(
            "gold_layer_suite",
            create_gold_layer_expectations()
        )


def main():
    runner = DataQualityRunner()
    runner.setup_all_suites()
    
    logger.info("All expectation suites created successfully")


if __name__ == "__main__":
    main()
```

---

### 6.4 Custom dbt Tests

**File**: `src/transformation/dbt/tests/assert_aqi_range.sql`

```sql
SELECT *
FROM {{ ref('fact_air_quality_measurements') }}
WHERE aqi_value < 0 OR aqi_value > 500
```

**File**: `src/transformation/dbt/tests/assert_no_future_dates.sql`

```sql
SELECT *
FROM {{ ref('fact_air_quality_measurements') }}
WHERE measurement_timestamp > CURRENT_TIMESTAMP
```

**File**: `src/transformation/dbt/tests/assert_location_consistency.sql`

```sql
WITH location_changes AS (
    SELECT
        city_id,
        COUNT(DISTINCT latitude) AS lat_count,
        COUNT(DISTINCT longitude) AS lon_count
    FROM {{ ref('stg_air_quality_measurements') }}
    GROUP BY city_id
)

SELECT *
FROM location_changes
WHERE lat_count > 1 OR lon_count > 1
```

**File**: `src/transformation/dbt/macros/test_accepted_ratio.sql`

```sql
{% test accepted_ratio(model, column_name, condition, threshold=0.95) %}

WITH validation AS (
    SELECT
        SUM(CASE WHEN {{ condition }} THEN 1 ELSE 0 END) AS valid_count,
        COUNT(*) AS total_count
    FROM {{ model }}
),

ratio AS (
    SELECT
        valid_count::FLOAT / NULLIF(total_count, 0) AS success_ratio
    FROM validation
)

SELECT *
FROM ratio
WHERE success_ratio < {{ threshold }}

{% endtest %}
```

---

### 6.5 Airflow Integration

**File**: `src/orchestration/airflow/dags/data_quality_dag.py`

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


default_args = {
    "owner": "data-quality",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def run_silver_validation(**context):
    from src.data_quality.quality_runner import DataQualityRunner
    
    runner = DataQualityRunner()
    results = runner.run_validation(
        datasource_name="silver_layer_s3",
        asset_name="air_quality",
        suite_name="silver_layer_suite"
    )
    
    if not results["success"]:
        raise ValueError(f"Data quality check failed: {results['success_rate']}% success")
    
    return results


def run_gold_validation(**context):
    from src.data_quality.quality_runner import DataQualityRunner
    
    runner = DataQualityRunner()
    results = runner.run_validation(
        datasource_name="postgres_warehouse",
        asset_name="facts.fact_air_quality_measurements",
        suite_name="gold_layer_suite"
    )
    
    if not results["success"]:
        raise ValueError(f"Data quality check failed: {results['success_rate']}% success")
    
    return results


with DAG(
    dag_id="data_quality_validation",
    default_args=default_args,
    description="Data quality validation pipeline",
    schedule_interval="0 4 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["data-quality"],
) as dag:
    
    validate_silver = PythonOperator(
        task_id="validate_silver_layer",
        python_callable=run_silver_validation,
        provide_context=True,
    )
    
    validate_gold = PythonOperator(
        task_id="validate_gold_layer",
        python_callable=run_gold_validation,
        provide_context=True,
    )
    
    validate_silver >> validate_gold
```

---

### 6.6 Quality Metrics Tracking

**File**: `src/data_quality/metrics_tracker.py`

```python
from datetime import datetime
from typing import Dict
import psycopg2

from src.common.config import config
from src.common.logger import setup_logger

logger = setup_logger(__name__)


class QualityMetricsTracker:
    
    def __init__(self):
        self.conn = psycopg2.connect(
            host=config.database.host,
            port=config.database.port,
            database=config.database.database,
            user=config.database.user,
            password=config.database.password
        )
        self._create_metrics_table()
    
    def _create_metrics_table(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS data_quality_metrics (
                    id SERIAL PRIMARY KEY,
                    layer VARCHAR(50) NOT NULL,
                    suite_name VARCHAR(100) NOT NULL,
                    execution_timestamp TIMESTAMP NOT NULL,
                    success BOOLEAN NOT NULL,
                    success_rate DECIMAL(5, 2) NOT NULL,
                    total_expectations INTEGER NOT NULL,
                    successful_expectations INTEGER NOT NULL,
                    failed_expectations INTEGER NOT NULL
                )
            """)
            self.conn.commit()
    
    def record_validation_result(
        self,
        layer: str,
        suite_name: str,
        results: Dict
    ):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO data_quality_metrics (
                    layer,
                    suite_name,
                    execution_timestamp,
                    success,
                    success_rate,
                    total_expectations,
                    successful_expectations,
                    failed_expectations
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                layer,
                suite_name,
                datetime.utcnow(),
                results["success"],
                results["success_rate"],
                results["evaluated_expectations"],
                results["successful_expectations"],
                results["unsuccessful_expectations"]
            ))
            self.conn.commit()
        
        logger.info(f"Recorded quality metrics for {layer}/{suite_name}")
    
    def get_quality_trend(self, layer: str, days: int = 7):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT
                    DATE(execution_timestamp) AS date,
                    AVG(success_rate) AS avg_success_rate,
                    MIN(success_rate) AS min_success_rate,
                    MAX(success_rate) AS max_success_rate
                FROM data_quality_metrics
                WHERE layer = %s
                  AND execution_timestamp >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(execution_timestamp)
                ORDER BY date DESC
            """, (layer, days))
            
            return cur.fetchall()
```

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
