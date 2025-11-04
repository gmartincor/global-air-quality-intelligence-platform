# Phase 8: Testing & CI/CD

**Duration**: 1 week  
**Prerequisites**: All previous phases completed

---

## Objectives

- Implement comprehensive test suite (unit, integration, E2E)
- Set up pre-commit hooks for code quality
- Create GitHub Actions CI/CD pipeline
- Achieve >80% test coverage
- Automate quality gates

---

## Architecture & Design Principles

**Testing Pyramid**: 70% unit tests, 20% integration tests, 10% E2E tests

**Test Strategy**:
- Unit: Test individual functions in isolation (mocks/stubs)
- Integration: Test component interactions (real services)
- E2E: Test complete user workflows (full stack)

**Quality Gates**:
- Code formatting: Black, isort
- Linting: Flake8
- Type checking: mypy
- Security: Trivy image scanning
- Coverage threshold: 80%

**SOLID Application in Tests**:
- **SRP**: Each test class tests one component
- **DIP**: Use fixtures for dependencies, not hardcoded instances
- **OCP**: Parameterized tests extend coverage without modifying test logic

**DRY in Tests**: Reusable fixtures, shared test utilities, parameterized test cases

---

## Tasks Breakdown

### 8.1 Unit Tests

**Test Module**: `tests/unit/processing/test_aqi_calculator.py`

**Class**: `TestAQICalculator`

**Responsibility**: Verify AQI calculation logic for PM2.5 values across all EPA ranges

**Test Cases Required**:
- `test_good_range`: PM2.5 = 10.5 → AQI ≈ 44
- `test_moderate_range`: PM2.5 = 25.0 → AQI ≈ 79
- `test_unhealthy_range`: PM2.5 = 45.0 → AQI ≈ 112
- `test_very_unhealthy_range`: PM2.5 = 200.0 → AQI ≈ 250
- `test_hazardous_range`: PM2.5 = 350.5 → AQI ≈ 458
- `test_boundary_low`: PM2.5 = 0.0 → AQI = 0
- `test_boundary_high`: PM2.5 = 500.0 → AQI = 500

**Parameterized Test**: `test_boundary_values`
- Test EPA breakpoint boundaries: (12.0→50), (35.4→100), (55.4→150), (150.4→200), (250.4→300)
- Assert calculated AQI within ±1 of expected (allows rounding tolerance)

**Import**: `from src.processing.spark.transformations.enrichment import calculate_aqi_pm25`

---

**Test Module**: `tests/unit/data_generation/test_temporal_patterns.py`

**Class**: `TestTemporalPatterns`

**Responsibility**: Verify temporal pattern multipliers for realistic data generation

**Test Cases Required**:
- `test_rush_hour_multiplier`: Hours 8 and 18 → multiplier = 1.4 (increased pollution)
- `test_night_multiplier`: Hours 2 and 23 → multiplier = 0.6 (reduced activity)
- `test_weekend_multiplier`: Days 5 and 6 (Sat/Sun) → multiplier = 0.8
- `test_weekday_multiplier`: Days 0-4 (Mon-Fri) → multiplier = 1.0
- `test_sensor_noise_positive`: Noise adds variability within ±30% range, value ≥ 0

**Import**: `from src.data_generation.generators.temporal_patterns import TemporalPatternGenerator`

---

**Test Module**: `tests/unit/common/test_config.py`

**Class**: `TestConfig`

**Responsibility**: Validate configuration loading and default values

**Test Cases Required**:
- `test_default_config`: environment = "dev", bronze_bucket = "dev-air-quality-bronze"
- `test_s3_config`: endpoint_url = "http://localhost:4566", region = "us-east-1"
- `test_kinesis_config`: stream_name = "air-quality-measurements"
- `test_database_config`: host = "localhost", port = 5432

**Import**: `from src.common.config import AppConfig`

---

### 8.2 Integration Tests

**Test Module**: `tests/integration/test_s3_operations.py`

**Class**: `TestS3Operations`

**Responsibility**: Test S3 upload/download operations with LocalStack

**Fixture**: `sample_dataframe` (pandas DataFrame with city_id, timestamp, pm25_value)

**Test Case**: `test_upload_and_verify`
- Upload DataFrame using `S3Uploader.upload_parquet_partitioned()`
- List objects in S3 bucket using `AWSClientFactory.create_s3_client()`
- Assert "Contents" key exists and contains uploaded files

**Dependencies**: LocalStack S3 service running

---

**Test Module**: `tests/integration/test_spark_job.py`

**Class**: `TestSparkTransformations`

**Responsibility**: Test Spark transformations with real SparkSession

**Fixture**: `spark` (module-scoped SparkSession, local[2] mode)

**Test Cases Required**:

1. `test_remove_nulls`:
   - Input: 3 rows, 2 with nulls in city_id or timestamp
   - Apply: `remove_nulls(df, ["city_id", "timestamp"])`
   - Assert: 1 row remains (NYC001 row)

2. `test_deduplicate`:
   - Input: 3 rows, 2 duplicates (same city_id + timestamp)
   - Apply: `deduplicate(df, ["city_id", "timestamp"])`
   - Assert: 2 unique rows remain

**Imports**: `from src.processing.spark.transformations.cleansing import remove_nulls, deduplicate`

---

### 8.3 End-to-End Tests

**Test Module**: `tests/e2e/test_batch_pipeline.py`

**Class**: `TestBatchPipeline`

**Responsibility**: Validate complete batch pipeline flow (generation → upload → S3)

**Test Case**: `test_full_pipeline_flow`
- Generate sample data: `BatchDataGenerator(mode="sample").generate()`
- Assert DataFrame has rows and required columns (city_id, pm25_value)
- Upload to S3: `S3Uploader().upload_parquet_partitioned()`
- Wait 5 seconds for async completion
- Optionally verify S3 object exists

**Dependencies**: LocalStack S3, data generation module

---

**Test Module**: `tests/e2e/test_streaming_pipeline.py`

**Class**: `TestStreamingPipeline`

**Responsibility**: Validate streaming pipeline (Kinesis → DynamoDB)

**Test Case**: `test_kinesis_to_dynamodb`
- Create test record (city_id="TEST001", pm25_value=25.5, etc.)
- Publish to Kinesis: `KinesisProducer().put_record()`
- Wait 5 seconds for consumer processing
- Query DynamoDB: `DynamoDBSpeedLayerWriter().get_latest_measurements()`
- Assert at least 1 result returned

**Dependencies**: LocalStack Kinesis, DynamoDB, streaming consumer running

---

### 8.4 Pre-commit Configuration

**File**: `.pre-commit-config.yaml`

**Responsibility**: Enforce code quality standards before commits

**Hooks Required**:

1. **Pre-commit built-in hooks** (v4.5.0):
   - `trailing-whitespace`: Remove trailing spaces
   - `end-of-file-fixer`: Ensure newline at EOF
   - `check-yaml`: Validate YAML syntax
   - `check-json`: Validate JSON syntax
   - `check-toml`: Validate TOML syntax
   - `check-added-large-files`: Reject files >10MB
   - `detect-private-key`: Prevent credential leaks

2. **Black** (23.11.0):
   - Language: Python 3.10
   - Args: `--line-length=100`

3. **isort** (5.12.0):
   - Profile: black (compatibility)
   - Args: `--line-length=100`

4. **Flake8** (6.1.0):
   - Args: `--max-line-length=100`, `--extend-ignore=E203,W503`

5. **mypy** (v1.7.0):
   - Dependencies: types-all
   - Args: `--ignore-missing-imports`, `--strict`

---

### 8.5 GitHub Actions CI/CD

**File**: `.github/workflows/ci.yml`

**Workflow Name**: CI Pipeline

**Triggers**:
- Push to: main, develop branches
- Pull requests to: main, develop

**Job 1: test** (ubuntu-latest)

**Services Required**:

1. **PostgreSQL**:
   - Image: postgres:15
   - Environment: POSTGRES_USER=airflow, POSTGRES_PASSWORD=airflow, POSTGRES_DB=air_quality_warehouse
   - Port: 5432
   - Health check: pg_isready every 10s

2. **LocalStack**:
   - Image: localstack/localstack:3.0
   - Services: s3, kinesis, dynamodb
   - Port: 4566

**Steps**:
1. Checkout code (actions/checkout@v3)
2. Setup Python 3.10 (actions/setup-python@v4)
3. Install Poetry (curl installer, add to PATH)
4. Install dependencies (`poetry install`)
5. Run linting (black --check, isort --check-only, flake8)
6. Run type checking (mypy src/)
7. Run unit tests (pytest tests/unit/ with coverage)
8. Run integration tests (pytest tests/integration/)
9. Upload coverage to Codecov (codecov/codecov-action@v3)

**Job 2: build** (needs: test, only on main branch)

**Steps**:
1. Checkout code
2. Build Docker images (Dockerfile with multi-stage builds)
3. Run security scan (Trivy on built image)

---

**File**: `.github/workflows/data-quality.yml`

**Workflow Name**: Data Quality Check

**Triggers**:
- Schedule: Daily at 6 AM UTC (`0 6 * * *`)
- Manual: workflow_dispatch

**Job: quality-check** (ubuntu-latest)

**Steps**:
1. Checkout code
2. Setup Python 3.10
3. Install Poetry + dependencies
4. Run Great Expectations (`python -m src.data_quality.quality_runner`)
5. Upload results artifact (uncommitted/ directory)

---

### 8.6 pytest Configuration

**File**: `pytest.ini`

**Configuration**:
- Test paths: `tests/`
- File pattern: `test_*.py`
- Class pattern: `Test*`
- Function pattern: `test_*`

**Options** (addopts):
- `-v`: Verbose output
- `--strict-markers`: Fail on undefined markers
- `--tb=short`: Short traceback format
- `--cov=src`: Coverage for src/ directory
- `--cov-report=term-missing`: Show missing lines
- `--cov-report=html`: Generate HTML coverage report
- `--cov-fail-under=80`: Fail if coverage <80%

**Custom Markers**:
- `unit`: Unit tests
- `integration`: Integration tests
- `e2e`: End-to-end tests
- `slow`: Slow running tests

---

**File**: `pyproject.toml`

**Development Dependencies to Add**:
- pytest: ^7.4.0
- pytest-cov: ^4.1.0 (coverage plugin)
- pytest-mock: ^3.12.0 (mocking support)
- pytest-asyncio: ^0.21.0 (async test support)
- black: ^23.11.0
- isort: ^5.12.0
- flake8: ^6.1.0
- mypy: ^1.7.0
- pre-commit: ^3.5.0

**Tool Configurations**:

- `[tool.black]`: line-length=100, target-version=['py310']
- `[tool.isort]`: profile="black", line_length=100
- `[tool.mypy]`: python_version="3.10", warn_return_any=true, disallow_untyped_defs=true

---

### 8.7 Makefile Automation

**File**: `Makefile`

**Targets to Add**:

- `test`: Run all tests
  - Command: `poetry run pytest tests/ -v`

- `test-unit`: Run unit tests only
  - Command: `poetry run pytest tests/unit/ -v -m unit`

- `test-integration`: Run integration tests only
  - Command: `poetry run pytest tests/integration/ -v -m integration`

- `test-e2e`: Run E2E tests only
  - Command: `poetry run pytest tests/e2e/ -v -m e2e`

- `coverage`: Generate coverage reports (HTML + terminal)
  - Command: `poetry run pytest tests/ --cov=src --cov-report=html --cov-report=term`

- `lint`: Check code quality (Black, isort, Flake8, mypy)
  - Commands: `black --check`, `isort --check-only`, `flake8`, `mypy src/`

- `format`: Auto-format code
  - Commands: `black src/ tests/`, `isort src/ tests/`

- `pre-commit-install`: Install pre-commit hooks
  - Command: `poetry run pre-commit install`

- `pre-commit-run`: Run pre-commit on all files
  - Command: `poetry run pre-commit run --all-files`

---

## Validation Steps

### 1. Install Pre-commit Hooks
```bash
make pre-commit-install
```

### 2. Run All Tests
```bash
make test
```

### 3. Check Coverage
```bash
make coverage
```

**Expected**: >80% coverage

### 4. Run Linting
```bash
make lint
```

### 5. Format Code
```bash
make format
```

### 6. Trigger CI Pipeline
Push to GitHub and verify Actions run successfully

---

## Deliverables Checklist

- [ ] Unit tests (>70% of total)
- [ ] Integration tests (>20% of total)
- [ ] End-to-end tests (>10% of total)
- [ ] Pre-commit hooks configured
- [ ] GitHub Actions CI/CD pipeline
- [ ] Test coverage >80%
- [ ] All quality gates passing
- [ ] Documentation updated

---

## Final Validation

### Complete System Test
```bash
make infra-up
make terraform-apply
make generate-data MODE=sample
make upload-data
make pipeline-run
make test
make coverage
```

**Expected Results**:
- All services running
- Data flowing through pipeline
- Tests passing with >80% coverage
- Quality score >95%
- No linting errors

---

## Project Completion

Congratulations! You have successfully implemented all 8 phases of the Global Air Quality Intelligence Platform.

**Final Deliverables**:
- Production-grade data pipeline with Lambda Architecture
- Batch processing (Airflow + Spark + dbt)
- Streaming processing (Kinesis + Flink)
- Data quality framework (Great Expectations + dbt tests)
- Monitoring & observability (Prometheus + Grafana)
- Comprehensive test suite (>80% coverage)
- CI/CD pipeline (GitHub Actions)
- Complete documentation

**Next Steps**:
- Add to portfolio/GitHub
- Create demo video
- Write blog post about implementation
- Prepare for technical interviews
