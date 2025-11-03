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

## Tasks Breakdown

### 8.1 Unit Tests

**File**: `tests/unit/processing/test_aqi_calculator.py`

```python
import pytest
from src.processing.spark.transformations.enrichment import calculate_aqi_pm25


class TestAQICalculator:
    
    def test_good_range(self):
        assert calculate_aqi_pm25(10.5) == 44
    
    def test_moderate_range(self):
        assert calculate_aqi_pm25(25.0) == 79
    
    def test_unhealthy_range(self):
        assert calculate_aqi_pm25(45.0) == 112
    
    def test_very_unhealthy_range(self):
        assert calculate_aqi_pm25(200.0) == 250
    
    def test_hazardous_range(self):
        assert calculate_aqi_pm25(350.5) == 458
    
    def test_boundary_low(self):
        assert calculate_aqi_pm25(0.0) == 0
    
    def test_boundary_high(self):
        assert calculate_aqi_pm25(500.0) == 500
    
    @pytest.mark.parametrize("pm25,expected", [
        (12.0, 50),
        (35.4, 100),
        (55.4, 150),
        (150.4, 200),
        (250.4, 300),
    ])
    def test_boundary_values(self, pm25, expected):
        result = calculate_aqi_pm25(pm25)
        assert abs(result - expected) <= 1
```

**File**: `tests/unit/data_generation/test_temporal_patterns.py`

```python
import pytest
from src.data_generation.generators.temporal_patterns import TemporalPatternGenerator


class TestTemporalPatterns:
    
    def test_rush_hour_multiplier(self):
        gen = TemporalPatternGenerator()
        assert gen.get_hour_of_day_multiplier(8) == 1.4
        assert gen.get_hour_of_day_multiplier(18) == 1.4
    
    def test_night_multiplier(self):
        gen = TemporalPatternGenerator()
        assert gen.get_hour_of_day_multiplier(2) == 0.6
        assert gen.get_hour_of_day_multiplier(23) == 0.6
    
    def test_weekend_multiplier(self):
        gen = TemporalPatternGenerator()
        assert gen.get_day_of_week_multiplier(5) == 0.8
        assert gen.get_day_of_week_multiplier(6) == 0.8
    
    def test_weekday_multiplier(self):
        gen = TemporalPatternGenerator()
        assert gen.get_day_of_week_multiplier(0) == 1.0
        assert gen.get_day_of_week_multiplier(4) == 1.0
    
    def test_sensor_noise_positive(self):
        gen = TemporalPatternGenerator()
        value = 100.0
        noisy = gen.add_sensor_noise(value)
        assert noisy >= 0
        assert 70 <= noisy <= 130
```

**File**: `tests/unit/common/test_config.py`

```python
import pytest
from pathlib import Path
from src.common.config import AppConfig


class TestConfig:
    
    def test_default_config(self):
        config = AppConfig()
        assert config.environment == "dev"
        assert config.s3.bronze_bucket == "dev-air-quality-bronze"
    
    def test_s3_config(self):
        config = AppConfig()
        assert config.s3.endpoint_url == "http://localhost:4566"
        assert config.s3.region == "us-east-1"
    
    def test_kinesis_config(self):
        config = AppConfig()
        assert config.kinesis.stream_name == "air-quality-measurements"
    
    def test_database_config(self):
        config = AppConfig()
        assert config.database.host == "localhost"
        assert config.database.port == 5432
```

---

### 8.2 Integration Tests

**File**: `tests/integration/test_s3_operations.py`

```python
import pytest
import pandas as pd
from src.ingestion.batch.s3_uploader import S3Uploader
from src.common.aws_client import AWSClientFactory


@pytest.fixture
def sample_dataframe():
    return pd.DataFrame({
        "city_id": ["NYC001", "LON001"],
        "timestamp": ["2024-01-01 12:00:00", "2024-01-01 12:00:00"],
        "pm25_value": [25.5, 30.2]
    })


class TestS3Operations:
    
    def test_upload_and_verify(self, sample_dataframe):
        uploader = S3Uploader()
        uploader.upload_parquet_partitioned(sample_dataframe, "test-data")
        
        s3_client = AWSClientFactory.create_s3_client()
        response = s3_client.list_objects_v2(
            Bucket="dev-air-quality-bronze",
            Prefix="test-data/"
        )
        
        assert "Contents" in response
        assert len(response["Contents"]) > 0
```

**File**: `tests/integration/test_spark_job.py`

```python
import pytest
from pyspark.sql import SparkSession
from src.processing.spark.transformations.cleansing import remove_nulls, deduplicate


@pytest.fixture(scope="module")
def spark():
    spark = SparkSession.builder \
        .appName("test") \
        .master("local[2]") \
        .getOrCreate()
    yield spark
    spark.stop()


class TestSparkTransformations:
    
    def test_remove_nulls(self, spark):
        data = [
            ("NYC001", "2024-01-01", 25.5),
            ("LON001", None, 30.2),
            (None, "2024-01-01", 35.1)
        ]
        df = spark.createDataFrame(data, ["city_id", "timestamp", "pm25_value"])
        
        result = remove_nulls(df, ["city_id", "timestamp"])
        
        assert result.count() == 1
        assert result.first()["city_id"] == "NYC001"
    
    def test_deduplicate(self, spark):
        data = [
            ("NYC001", "2024-01-01 12:00:00", 25.5),
            ("NYC001", "2024-01-01 12:00:00", 26.0),
            ("LON001", "2024-01-01 12:00:00", 30.2)
        ]
        df = spark.createDataFrame(data, ["city_id", "timestamp", "pm25_value"])
        
        result = deduplicate(df, ["city_id", "timestamp"])
        
        assert result.count() == 2
```

---

### 8.3 End-to-End Tests

**File**: `tests/e2e/test_batch_pipeline.py`

```python
import pytest
import time
from pathlib import Path
import pandas as pd
from src.data_generation.batch_generator import BatchDataGenerator
from src.ingestion.batch.s3_uploader import S3Uploader


class TestBatchPipeline:
    
    def test_full_pipeline_flow(self):
        generator = BatchDataGenerator(mode="sample")
        df = generator.generate()
        
        assert len(df) > 0
        assert "city_id" in df.columns
        assert "pm25_value" in df.columns
        
        uploader = S3Uploader()
        uploader.upload_parquet_partitioned(df, "e2e-test")
        
        time.sleep(5)
```

**File**: `tests/e2e/test_streaming_pipeline.py`

```python
import pytest
import time
from src.ingestion.streaming.kinesis_producer import KinesisProducer
from src.processing.streaming.dynamodb_writer import DynamoDBSpeedLayerWriter


class TestStreamingPipeline:
    
    def test_kinesis_to_dynamodb(self):
        producer = KinesisProducer()
        
        test_record = {
            "city_id": "TEST001",
            "city_name": "Test City",
            "timestamp": "2024-01-01T12:00:00",
            "pm25_value": 25.5,
            "pm10_value": 35.0,
            "aqi_value": 80,
            "aqi_category": "Moderate",
            "temperature_c": 20.0
        }
        
        producer.put_record(test_record)
        
        time.sleep(5)
        
        writer = DynamoDBSpeedLayerWriter()
        results = writer.get_latest_measurements("TEST001", limit=1)
        
        assert len(results) > 0
```

---

### 8.4 Pre-commit Configuration

**File**: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=10000']
      - id: check-json
      - id: check-toml
      - id: detect-private-key

  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.10
        args: ['--line-length=100']

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ['--profile', 'black', '--line-length=100']

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100', '--extend-ignore=E203,W503']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: ['--ignore-missing-imports', '--strict']
```

---

### 8.5 GitHub Actions CI/CD

**File**: `.github/workflows/ci.yml`

```yaml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: airflow
          POSTGRES_PASSWORD: airflow
          POSTGRES_DB: air_quality_warehouse
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      localstack:
        image: localstack/localstack:3.0
        env:
          SERVICES: s3,kinesis,dynamodb
        ports:
          - 4566:4566

    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH
      
      - name: Install dependencies
        run: |
          poetry install
      
      - name: Run linting
        run: |
          poetry run black --check src/ tests/
          poetry run isort --check-only src/ tests/
          poetry run flake8 src/ tests/
      
      - name: Run type checking
        run: |
          poetry run mypy src/
      
      - name: Run unit tests
        run: |
          poetry run pytest tests/unit/ -v --cov=src --cov-report=xml
      
      - name: Run integration tests
        run: |
          poetry run pytest tests/integration/ -v
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker images
        run: |
          docker build -f infrastructure/docker/airflow.Dockerfile -t air-quality-airflow:latest .
      
      - name: Run security scan
        run: |
          docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image air-quality-airflow:latest
```

**File**: `.github/workflows/data-quality.yml`

```yaml
name: Data Quality Check

on:
  schedule:
    - cron: '0 6 * * *'
  workflow_dispatch:

jobs:
  quality-check:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      
      - name: Run Great Expectations
        run: |
          poetry run python -m src.data_quality.quality_runner
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: quality-results
          path: src/data_quality/great_expectations/uncommitted/
```

---

### 8.6 pytest Configuration

**File**: `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=80

markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
```

**File**: `pyproject.toml` (add testing dependencies)

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-cov = "^4.1.0"
pytest-mock = "^3.12.0"
pytest-asyncio = "^0.21.0"
black = "^23.11.0"
isort = "^5.12.0"
flake8 = "^6.1.0"
mypy = "^1.7.0"
pre-commit = "^3.5.0"

[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

---

### 8.7 Makefile Updates

```makefile
.PHONY: test test-unit test-integration test-e2e coverage lint format

test:
	poetry run pytest tests/ -v

test-unit:
	poetry run pytest tests/unit/ -v -m unit

test-integration:
	poetry run pytest tests/integration/ -v -m integration

test-e2e:
	poetry run pytest tests/e2e/ -v -m e2e

coverage:
	poetry run pytest tests/ --cov=src --cov-report=html --cov-report=term

lint:
	poetry run black --check src/ tests/
	poetry run isort --check-only src/ tests/
	poetry run flake8 src/ tests/
	poetry run mypy src/

format:
	poetry run black src/ tests/
	poetry run isort src/ tests/

pre-commit-install:
	poetry run pre-commit install

pre-commit-run:
	poetry run pre-commit run --all-files
```

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
