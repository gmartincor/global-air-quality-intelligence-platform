# Phase 3: Batch Pipeline - Ingestion & Processing

**Duration**: 2 weeks  
**Prerequisites**: Phase 1 & 2 completed, data generated

---

## Objectives

- Implement Bronze layer ingestion with partitioning strategy
- Build composable Spark transformation pipeline
- Create orchestration layer with Airflow
- Apply idempotency and incremental patterns

---

## Tasks Breakdown

### 3.1 File Structure

```
src/
├── ingestion/batch/
│   └── s3_uploader.py
├── processing/spark/
│   ├── base.py
│   ├── transformations.py
│   └── jobs/
│       └── bronze_to_silver.py
└── orchestration/airflow/dags/
    └── batch_pipeline_dag.py
```

---

### 3.2 Base Transformation Abstraction (Chain of Responsibility Pattern)

**File**: `src/processing/spark/base.py`

**Requirements**:
- Abstract base class `Transformation` using ABC
- Constructor accepts optional `next_transform` for chaining
- Abstract method `transform(df: DataFrame) -> DataFrame`
- Implement `__call__` to enable chaining: execute transform, then call next if exists
- Pattern allows composable transformations: `Transform1(Transform2(Transform3()))`

**Purpose**: Enable flexible, reusable transformation pipeline without tight coupling

---

### 3.3 Transformation Components

**File**: `src/processing/spark/transformations.py`

**Implementation Requirements**:

**1. RemoveNulls Transformation**:
- Accepts list of critical columns
- Filters out rows where any specified column is null
- Uses PySpark `filter(col.isNotNull())`

**2. Deduplicate Transformation**:
- Accepts key columns (e.g., city_id, timestamp) and order column
- Uses Window function with `row_number()` ordered by timestamp descending
- Keeps only first row per partition, drops temporary row number column

**3. NormalizeStrings Transformation**:
- Accepts list of string columns to normalize
- Applies `UPPER(TRIM(col))` to each specified column

**4. ValidateRanges Transformation**:
- Define class constant `VALIDATIONS` dict with column: (min, max) ranges
  - pm25_value: (0, 500)
  - pm10_value: (0, 600)
  - latitude: (-90, 90)
  - longitude: (-180, 180)
- Filter rows where all values are within valid ranges
- Only validate columns present in DataFrame

**5. AddAQI Transformation**:
- Define EPA AQI breakpoints as class constant (PM2.5 concentration ranges to AQI)
  - Breakpoints: [(0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150), ...]
- Define AQI categories: Good (0-50), Moderate (51-100), Unhealthy for Sensitive Groups (101-150), etc.
- Implement UDF `_calculate_aqi(pm25: float) -> int` using linear interpolation formula
- Add columns: `aqi_value` (int), `aqi_category` (string)
- Use case/when for category assignment

**6. AddTimestampColumns Transformation**:
- Extract date, year, month, day from timestamp column
- Uses PySpark date functions: `to_date()`, `year()`, `month()`, `dayofmonth()`

**7. AddProcessingMetadata Transformation**:
- Add `processed_at` (current timestamp) and `processing_date` (current date)
- Uses `current_timestamp()` and `current_date()` functions

---

### 3.4 S3 Uploader (Bronze Layer Ingestion)

**File**: `src/ingestion/batch/s3_uploader.py`

**Requirements**:
- Class `S3Uploader` with constructor accepting bucket name
- Method `upload_partitioned(df, base_prefix)`:
  - Extract year, month, day from timestamp column
  - Group DataFrame by (year, month, day)
  - For each partition, call `_upload_partition()`
- Method `_upload_partition(df, prefix, year, month, day)`:
  - Create partition path: `{prefix}/year={year}/month={month:02d}/day={day:02d}/data.parquet`
  - Write to temporary file (Parquet + Snappy compression)
  - Upload to S3 using boto3 client
  - Delete temporary file
- Main function: read generated data, upload to bronze bucket

**Partitioning Strategy**: Hive-style partitions by year/month/day for efficient querying

---

### 3.5 Spark Job (Template Method Pattern)

**File**: `src/processing/spark/jobs/bronze_to_silver.py`

**Requirements**:

**SparkJobBase Class**:
- Constructor creates SparkSession with Delta Lake configuration
- Configurations:
  - Delta extensions enabled
  - S3A endpoint, credentials (LocalStack compatible)
  - Adaptive query execution enabled
- Implement context manager (`__enter__`, `__exit__`) for automatic cleanup
- `__exit__` stops Spark session

**BronzeToSilverJob Class** (inherits SparkJobBase):
- Constructor builds transformation pipeline using chaining
- Method `_build_pipeline()`: chain all transformations in correct order
  - RemoveNulls → Deduplicate → NormalizeStrings → ValidateRanges → AddAQI → AddTimestampColumns → AddProcessingMetadata
- Method `read_bronze(execution_date)`: read Parquet from Bronze layer
  - If execution_date provided, read specific partition
  - Otherwise, read all data
- Method `write_silver(df)`: write Delta Lake to Silver layer
  - Format: delta
  - Mode: append
  - Partition by: country_code, date
  - Enable schema merging
- Method `run(execution_date)`: orchestrate read → transform → write

**Main Function**:
- Parse CLI argument: `--execution-date` (format: YYYY-MM-DD)
- Execute job with context manager
- Enables idempotent reruns for specific dates

---

### 3.6 Airflow DAG (Orchestration)

**File**: `src/orchestration/airflow/dags/batch_pipeline_dag.py`

**Requirements**:

**Validation Function** (`validate_bronze_layer`):
- Get execution date from Airflow context
- List S3 objects for specific partition
- Raise error if partition empty
- Return True if data exists

**DAG Configuration**:
- dag_id: `batch_air_quality_pipeline`
- Schedule: daily at 2 AM (`0 2 * * *`)
- Start date: 2024-01-01
- Catchup: False (only run current date)
- Max active runs: 1 (prevent parallel executions)
- Retries: 3 with 5-minute delay

**Tasks**:
1. `validate_bronze_layer`: PythonOperator calling validation function
2. `bronze_to_silver`: SparkSubmitOperator
   - Application path to bronze_to_silver.py
   - Executor/driver memory configuration
   - Pass `{{ ds }}` (execution date) as argument
   - Connection: spark_default

**Task Dependencies**: validate_raw >> bronze_to_silver

---

### 3.7 Makefile Commands

Add to existing `Makefile`:
```makefile
upload-data:
	poetry run python -m src.ingestion.batch.s3_uploader

spark-submit:
	docker exec spark-master spark-submit \
		--master spark://spark-master:7077 \
		/opt/spark/src/processing/spark/jobs/$(JOB).py

airflow-init:
	docker exec airflow-webserver airflow db init
	docker exec airflow-webserver airflow users create \
		--username airflow --password airflow \
		--firstname Admin --lastname User --role Admin \
		--email admin@example.com

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
**Expected**: Hive-partitioned structure with Parquet files

### 2. Run Spark Job Manually
```bash
make spark-submit JOB=bronze_to_silver
```
**Expected**: Job completes successfully, logs show transformations applied

### 3. Verify Silver Layer
```bash
aws --endpoint-url=http://localhost:4566 s3 ls s3://dev-air-quality-silver/air-quality/ --recursive
```
**Expected**: Delta Lake format files partitioned by country_code/date

### 4. Initialize Airflow
```bash
make airflow-init
```
**Expected**: Database initialized, admin user created

### 5. Trigger Pipeline
```bash
make pipeline-run
```
**Expected**: DAG runs successfully, both tasks green

### 6. Monitor Execution
Visit http://localhost:8080 → batch_air_quality_pipeline DAG

---

## Design Patterns Applied

### Chain of Responsibility
- Transformations linked in sequence via constructor chaining
- Each transformation independent and testable in isolation
- Easy to reorder or add new transformations without modifying existing code
- Promotes Single Responsibility Principle

### Template Method
- `SparkJobBase` defines skeleton algorithm (session creation, cleanup)
- `BronzeToSilverJob` implements specific pipeline logic
- Promotes code reuse across multiple Spark jobs
- Common configuration centralized in base class

### Strategy Pattern
- Pipeline composition defined at runtime via chaining
- Easily swap transformation implementations
- Configuration-driven behavior

---

## SOLID Principles Applied

**Single Responsibility**:
- Each transformation: one specific data operation (null removal, deduplication, etc.)
- S3Uploader: exclusively handles Bronze layer uploads with partitioning
- Spark job: orchestrates pipeline execution only

**Open/Closed**:
- Add new transformations by creating new classes (open for extension)
- No need to modify base Transformation class or existing transformations (closed for modification)
- Extend pipeline by adding to chain

**Liskov Substitution**:
- All transformations implement same `Transformation` interface
- Can swap any Transformation subclass without breaking pipeline
- Polymorphism enables flexible composition

**Interface Segregation**:
- Transformation interface minimal (single `transform` method)
- No forced implementations of unused methods
- Classes only depend on methods they use

**Dependency Inversion**:
- `BronzeToSilverJob` depends on `Transformation` abstraction
- Concrete transformations injected via constructor chaining
- High-level modules independent of low-level details

---

## Data Engineering Patterns Applied

### Idempotency
- Same input produces identical output (deterministic execution)
- Partition-based processing enables reruns without duplicates
- `execution_date` parameter allows reprocessing specific dates
- Delta Lake append mode with partitioning ensures consistency

### Incremental Loading
- Process only specific date partitions (not entire dataset)
- Watermark pattern via `execution_date` parameter
- Efficient for backfills and late-arriving data
- Reduces processing time and costs

### Schema Evolution
- Delta Lake `mergeSchema` option enabled
- Handles additive schema changes (new columns) gracefully
- Version tracking automatic with Delta Lake
- Backward compatibility maintained

---

## Deliverables Checklist

- [ ] Transformation base class and 7 concrete implementations
- [ ] S3 uploader with Hive-style partitioning
- [ ] Spark job with Delta Lake integration
- [ ] Airflow DAG with validation and retry logic
- [ ] Makefile automation commands
- [ ] Bronze layer populated with partitioned data
- [ ] Silver layer verified with Delta format
- [ ] Pipeline orchestration working end-to-end

---

## Next Phase

[Phase 4: Data Transformation](./phase4_transformation.md)
