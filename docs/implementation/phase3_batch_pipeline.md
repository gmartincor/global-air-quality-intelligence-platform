# Phase 3: Batch Pipeline - Ingestion & Processing

**Duration**: 2 weeks  
**Prerequisites**: Phase 1 & 2 completed, data generated

---

## Objectives

- Implement Bronze layer ingestion (S3 upload with partitioning)
- Build Spark jobs for Bronze→Silver transformation
- Create Airflow DAGs for orchestration
- Implement idempotency and incremental loading patterns

---

## Tasks Breakdown

### 3.1 S3 Upload (Bronze Layer Ingestion)

**File**: `src/ingestion/batch/s3_uploader.py`

```python
from datetime import datetime
from pathlib import Path
import pandas as pd
from botocore.exceptions import ClientError

from src.common.config import config
from src.common.logger import setup_logger
from src.common.aws_client import AWSClientFactory

logger = setup_logger(__name__)


class S3Uploader:
    
    def __init__(self):
        self.s3_client = AWSClientFactory.create_s3_client()
        self.bucket = config.s3.bronze_bucket
    
    def upload_parquet_partitioned(
        self,
        df: pd.DataFrame,
        base_prefix: str = "air-quality"
    ):
        logger.info(f"Uploading {len(df):,} records to S3 bronze layer")
        
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        df['year'] = pd.to_datetime(df['timestamp']).dt.year
        df['month'] = pd.to_datetime(df['timestamp']).dt.month
        df['day'] = pd.to_datetime(df['timestamp']).dt.day
        
        partition_groups = df.groupby(['year', 'month', 'day'])
        
        for (year, month, day), group_df in partition_groups:
            partition_path = f"{base_prefix}/year={year}/month={month:02d}/day={day:02d}/data.parquet"
            
            temp_file = Path(f"/tmp/{year}_{month}_{day}_data.parquet")
            group_df.drop(['date', 'year', 'month', 'day'], axis=1).to_parquet(
                temp_file,
                compression="snappy",
                index=False
            )
            
            try:
                self.s3_client.upload_file(
                    str(temp_file),
                    self.bucket,
                    partition_path
                )
                logger.info(f"Uploaded partition: {partition_path} ({len(group_df)} records)")
            except ClientError as e:
                logger.error(f"Failed to upload {partition_path}: {e}")
                raise
            finally:
                temp_file.unlink(missing_ok=True)
        
        logger.info("Upload completed")


def main():
    input_file = config.project_root / "data" / "generated" / "batch_sample.parquet"
    
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return
    
    df = pd.read_parquet(input_file)
    uploader = S3Uploader()
    uploader.upload_parquet_partitioned(df)


if __name__ == "__main__":
    main()
```

---

### 3.2 Spark Transformations

**File**: `src/processing/spark/transformations/cleansing.py`

```python
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def remove_nulls(df: DataFrame, critical_columns: list[str]) -> DataFrame:
    for col in critical_columns:
        df = df.filter(F.col(col).isNotNull())
    return df


def deduplicate(df: DataFrame, key_columns: list[str]) -> DataFrame:
    window_spec = Window.partitionBy(*key_columns).orderBy(F.col("timestamp").desc())
    return df.withColumn("row_num", F.row_number().over(window_spec)) \
             .filter(F.col("row_num") == 1) \
             .drop("row_num")


def normalize_strings(df: DataFrame, columns: list[str]) -> DataFrame:
    for col in columns:
        df = df.withColumn(col, F.upper(F.trim(F.col(col))))
    return df


def validate_ranges(df: DataFrame) -> DataFrame:
    return df.filter(
        (F.col("pm25_value") >= 0) & (F.col("pm25_value") <= 500) &
        (F.col("pm10_value") >= 0) & (F.col("pm10_value") <= 600) &
        (F.col("latitude") >= -90) & (F.col("latitude") <= 90) &
        (F.col("longitude") >= -180) & (F.col("longitude") <= 180)
    )


def add_processing_metadata(df: DataFrame) -> DataFrame:
    return df.withColumn("processed_at", F.current_timestamp()) \
             .withColumn("processing_date", F.current_date())
```

**File**: `src/processing/spark/transformations/enrichment.py`

```python
from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def calculate_aqi_pm25(pm25: float) -> int:
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 500.0, 301, 500)
    ]
    
    for c_low, c_high, i_low, i_high in breakpoints:
        if c_low <= pm25 <= c_high:
            return int(((i_high - i_low) / (c_high - c_low)) * (pm25 - c_low) + i_low)
    
    return 500


calculate_aqi_udf = F.udf(calculate_aqi_pm25, "integer")


def add_aqi_calculations(df: DataFrame) -> DataFrame:
    df = df.withColumn("aqi_value", calculate_aqi_udf(F.col("pm25_value")))
    
    df = df.withColumn(
        "aqi_category",
        F.when(F.col("aqi_value") <= 50, "Good")
         .when(F.col("aqi_value") <= 100, "Moderate")
         .when(F.col("aqi_value") <= 150, "Unhealthy for Sensitive Groups")
         .when(F.col("aqi_value") <= 200, "Unhealthy")
         .when(F.col("aqi_value") <= 300, "Very Unhealthy")
         .otherwise("Hazardous")
    )
    
    return df


def add_date_partitions(df: DataFrame) -> DataFrame:
    return df.withColumn("date", F.to_date(F.col("timestamp"))) \
             .withColumn("year", F.year(F.col("timestamp"))) \
             .withColumn("month", F.month(F.col("timestamp"))) \
             .withColumn("day", F.dayofmonth(F.col("timestamp")))
```

---

### 3.3 Spark Jobs

**File**: `src/processing/spark/jobs/bronze_to_silver.py`

```python
import sys
from pathlib import Path
from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.common.config import config
from src.common.logger import setup_logger
from src.processing.spark.transformations.cleansing import (
    remove_nulls,
    deduplicate,
    normalize_strings,
    validate_ranges,
    add_processing_metadata
)
from src.processing.spark.transformations.enrichment import (
    add_aqi_calculations,
    add_date_partitions
)

logger = setup_logger(__name__)


def create_spark_session() -> SparkSession:
    builder = (
        SparkSession.builder
        .appName("BronzeToSilver")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.hadoop.fs.s3a.endpoint", config.s3.endpoint_url)
        .config("spark.hadoop.fs.s3a.access.key", "test")
        .config("spark.hadoop.fs.s3a.secret.key", "test")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.shuffle.partitions", "200")
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()


def read_bronze_layer(spark: SparkSession, execution_date: str | None = None):
    base_path = f"s3a://{config.s3.bronze_bucket}/air-quality/"
    
    if execution_date:
        year, month, day = execution_date.split("-")
        path = f"{base_path}year={year}/month={month}/day={day}/"
    else:
        path = base_path
    
    logger.info(f"Reading from bronze layer: {path}")
    return spark.read.parquet(path)


def process_bronze_to_silver(df):
    logger.info(f"Processing {df.count():,} records")
    
    df = (
        df
        .transform(remove_nulls, critical_columns=["city_id", "timestamp", "pm25_value"])
        .transform(deduplicate, key_columns=["city_id", "timestamp"])
        .transform(normalize_strings, columns=["city_name", "country_name"])
        .transform(validate_ranges)
        .transform(add_aqi_calculations)
        .transform(add_date_partitions)
        .transform(add_processing_metadata)
    )
    
    logger.info(f"Processed records: {df.count():,}")
    return df


def write_silver_layer(df, mode: str = "append"):
    output_path = f"s3a://{config.s3.silver_bucket}/air-quality/"
    
    logger.info(f"Writing to silver layer: {output_path}")
    
    (
        df.write
        .format("delta")
        .mode(mode)
        .partitionBy("country_code", "date")
        .option("mergeSchema", "true")
        .option("overwriteSchema", "false")
        .save(output_path)
    )
    
    logger.info("Write completed")


def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-date", type=str, help="YYYY-MM-DD format")
    args = parser.parse_args()
    
    spark = create_spark_session()
    
    try:
        bronze_df = read_bronze_layer(spark, args.execution_date)
        silver_df = process_bronze_to_silver(bronze_df)
        write_silver_layer(silver_df)
        
        logger.info("Bronze to Silver job completed successfully")
    except Exception as e:
        logger.error(f"Job failed: {e}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
```

---

### 3.4 Airflow DAG

**File**: `src/orchestration/airflow/dags/batch_pipeline_dag.py`

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
}


def validate_bronze_layer(**context):
    from src.common.logger import setup_logger
    from src.common.aws_client import AWSClientFactory
    from src.common.config import config
    
    logger = setup_logger(__name__)
    s3_client = AWSClientFactory.create_s3_client()
    
    execution_date = context["ds"]
    year, month, day = execution_date.split("-")
    prefix = f"air-quality/year={year}/month={month}/day={day}/"
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=config.s3.bronze_bucket,
            Prefix=prefix
        )
        
        if "Contents" not in response:
            raise ValueError(f"No data found in bronze layer for {execution_date}")
        
        logger.info(f"Validated bronze layer: {len(response['Contents'])} files found")
        return True
        
    except Exception as e:
        logger.error(f"Bronze layer validation failed: {e}")
        raise


with DAG(
    dag_id="batch_air_quality_pipeline",
    default_args=default_args,
    description="Daily batch processing of air quality data",
    schedule_interval="0 2 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["batch", "air-quality", "production"],
    max_active_runs=1,
) as dag:
    
    validate_raw = PythonOperator(
        task_id="validate_bronze_layer",
        python_callable=validate_bronze_layer,
        provide_context=True,
    )
    
    bronze_to_silver = SparkSubmitOperator(
        task_id="bronze_to_silver_transformation",
        application="/opt/airflow/src/processing/spark/jobs/bronze_to_silver.py",
        name="bronze-to-silver",
        conf={
            "spark.sql.shuffle.partitions": "200",
            "spark.sql.adaptive.enabled": "true",
            "spark.executor.memory": "4g",
            "spark.driver.memory": "2g",
        },
        application_args=["--execution-date", "{{ ds }}"],
        conn_id="spark_default",
        verbose=True,
    )
    
    validate_raw >> bronze_to_silver
```

---

### 3.5 Makefile Updates

Add to `Makefile`:

```makefile
.PHONY: upload-data spark-submit airflow-init pipeline-run

upload-data:
	poetry run python -m src.ingestion.batch.s3_uploader

spark-submit:
	docker exec spark-master spark-submit \
		--master spark://spark-master:7077 \
		--deploy-mode client \
		/opt/spark/src/processing/spark/jobs/$(JOB).py

airflow-init:
	docker exec airflow-webserver airflow db init
	docker exec airflow-webserver airflow users create \
		--username airflow \
		--firstname Admin \
		--lastname User \
		--role Admin \
		--email admin@example.com \
		--password airflow

pipeline-run:
	docker exec airflow-webserver airflow dags trigger batch_air_quality_pipeline
```

---

## Validation Steps

### 1. Upload Data to Bronze Layer
```bash
make upload-data
aws --endpoint-url=http://localhost:4566 s3 ls s3://dev-air-quality-bronze/air-quality/ --recursive
```

### 2. Test Spark Job Manually
```bash
make spark-submit JOB=bronze_to_silver
```

### 3. Verify Silver Layer
```bash
aws --endpoint-url=http://localhost:4566 s3 ls s3://dev-air-quality-silver/air-quality/ --recursive
```

### 4. Initialize Airflow
```bash
make airflow-init
```

### 5. Trigger Pipeline
```bash
make pipeline-run
```

### 6. Monitor Airflow UI
Visit http://localhost:8080 and check DAG execution

---

## Deliverables Checklist

- [ ] S3 uploader with partitioning
- [ ] Spark cleansing transformations
- [ ] Spark enrichment transformations
- [ ] Bronze to Silver Spark job
- [ ] Airflow DAG for orchestration
- [ ] Data uploaded to Bronze layer
- [ ] Silver layer populated via Spark
- [ ] Airflow pipeline running successfully

---

## Next Phase

Proceed to [Phase 4: Data Transformation](./phase4_transformation.md)
