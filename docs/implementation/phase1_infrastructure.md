# Phase 1: Infrastructure & Environment Setup

**Duration**: 1 week  
**Prerequisites**: Docker Desktop, Terraform, Python 3.10+, Make

---

## Objectives

- Provision local AWS infrastructure via Terraform
- Configure Docker Compose for all services
- Establish LocalStack simulation
- Set up project structure and dependencies

---

## Tasks Breakdown

### 1.1 Project Initialization

**Directory Structure**:
```
global-air-quality/
├── infrastructure/
│   ├── terraform/
│   ├── docker/
│   └── localstack/
├── src/
│   └── common/
├── config/
├── tests/
├── docs/
├── Makefile
├── pyproject.toml
├── .gitignore
└── README.md
```

**Files to Create**:
- `pyproject.toml`: Python dependencies (Poetry)
- `.gitignore`: Exclude `__pycache__`, `.terraform/`, data files
- `Makefile`: Automation commands
- `README.md`: Setup instructions

**Dependencies** (pyproject.toml):
```toml
[tool.poetry]
name = "global-air-quality"
version = "0.1.0"
python = "^3.10"

[tool.poetry.dependencies]
pyspark = "^3.5.0"
delta-spark = "^3.0.0"
pandas = "^2.1.0"
numpy = "^1.26.0"
boto3 = "^1.34.0"
pydantic = "^2.5.0"
pyyaml = "^6.0.1"
apache-airflow = "^2.7.0"
great-expectations = "^0.18.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
black = "^23.11.0"
isort = "^5.12.0"
flake8 = "^6.1.0"
mypy = "^1.7.0"
pre-commit = "^3.5.0"
```

---

### 1.2 Docker Compose Configuration

**File**: `infrastructure/docker/docker-compose.yml`

**Services**:
1. **LocalStack** (AWS simulation)
2. **PostgreSQL** (Airflow metadata + Data warehouse)
3. **Redis** (Airflow Celery broker)
4. **Airflow Webserver**
5. **Airflow Scheduler**
6. **Airflow Worker**
7. **Spark Master**
8. **Spark Worker**
9. **Prometheus** (Metrics)
10. **Grafana** (Dashboards)

**Key Configuration**:
```yaml
version: '3.8'

services:
  localstack:
    image: localstack/localstack:3.0
    container_name: localstack
    ports:
      - "4566:4566"
    environment:
      - SERVICES=s3,kinesis,dynamodb
      - DEBUG=1
      - DATA_DIR=/tmp/localstack/data
      - PERSISTENCE=1
    volumes:
      - localstack-data:/tmp/localstack
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - air-quality-network

  postgres:
    image: postgres:15-alpine
    container_name: postgres
    environment:
      - POSTGRES_USER=airflow
      - POSTGRES_PASSWORD=airflow
      - POSTGRES_DB=airflow
      - POSTGRES_MULTIPLE_DATABASES=air_quality_warehouse
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    networks:
      - air-quality-network

  redis:
    image: redis:7-alpine
    container_name: redis
    ports:
      - "6379:6379"
    networks:
      - air-quality-network

  airflow-webserver:
    build:
      context: ../..
      dockerfile: infrastructure/docker/airflow.Dockerfile
    container_name: airflow-webserver
    depends_on:
      - postgres
      - redis
    environment:
      - AIRFLOW__CORE__EXECUTOR=CeleryExecutor
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow
      - AIRFLOW__CELERY__BROKER_URL=redis://:@redis:6379/0
      - AIRFLOW__CELERY__RESULT_BACKEND=db+postgresql://airflow:airflow@postgres/airflow
      - AIRFLOW__CORE__FERNET_KEY=<generate-via-python>
      - AIRFLOW__CORE__LOAD_EXAMPLES=False
      - AIRFLOW__WEBSERVER__EXPOSE_CONFIG=True
    volumes:
      - ../../src/orchestration/airflow/dags:/opt/airflow/dags
      - ../../src:/opt/airflow/src
      - airflow-logs:/opt/airflow/logs
    ports:
      - "8080:8080"
    command: webserver
    networks:
      - air-quality-network

  airflow-scheduler:
    build:
      context: ../..
      dockerfile: infrastructure/docker/airflow.Dockerfile
    container_name: airflow-scheduler
    depends_on:
      - postgres
      - redis
    environment:
      - AIRFLOW__CORE__EXECUTOR=CeleryExecutor
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow
      - AIRFLOW__CELERY__BROKER_URL=redis://:@redis:6379/0
      - AIRFLOW__CELERY__RESULT_BACKEND=db+postgresql://airflow:airflow@postgres/airflow
    volumes:
      - ../../src/orchestration/airflow/dags:/opt/airflow/dags
      - ../../src:/opt/airflow/src
      - airflow-logs:/opt/airflow/logs
    command: scheduler
    networks:
      - air-quality-network

  spark-master:
    image: bitnami/spark:3.5.0
    container_name: spark-master
    environment:
      - SPARK_MODE=master
      - SPARK_MASTER_HOST=spark-master
      - SPARK_RPC_AUTHENTICATION_ENABLED=no
      - SPARK_RPC_ENCRYPTION_ENABLED=no
    ports:
      - "8081:8080"
      - "7077:7077"
    volumes:
      - ../../src:/opt/spark/src
    networks:
      - air-quality-network

  spark-worker:
    image: bitnami/spark:3.5.0
    container_name: spark-worker
    depends_on:
      - spark-master
    environment:
      - SPARK_MODE=worker
      - SPARK_MASTER_URL=spark://spark-master:7077
      - SPARK_WORKER_MEMORY=4G
      - SPARK_WORKER_CORES=2
    volumes:
      - ../../src:/opt/spark/src
    networks:
      - air-quality-network

volumes:
  localstack-data:
  postgres-data:
  airflow-logs:

networks:
  air-quality-network:
    driver: bridge
```

**Dockerfile for Airflow** (`infrastructure/docker/airflow.Dockerfile`):
```dockerfile
FROM apache/airflow:2.7.0-python3.10

USER root
RUN apt-get update && apt-get install -y \
    openjdk-11-jdk \
    && apt-get clean

USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

---

### 1.3 Terraform Configuration

**File Structure**:
```
infrastructure/terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── backend.tf
├── modules/
│   ├── s3/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── kinesis/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── dynamodb/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── environments/
    ├── dev.tfvars
    └── prod.tfvars
```

**Root Module** (`main.tf`):
```hcl
terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = var.aws_region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3       = "http://localhost:4566"
    kinesis  = "http://localhost:4566"
    dynamodb = "http://localhost:4566"
  }
}

module "s3" {
  source      = "./modules/s3"
  environment = var.environment
  project     = var.project_name
}

module "kinesis" {
  source      = "./modules/kinesis"
  environment = var.environment
  stream_name = "${var.project_name}-measurements"
  shard_count = var.kinesis_shard_count
}

module "dynamodb" {
  source      = "./modules/dynamodb"
  environment = var.environment
  project     = var.project_name
}
```

**S3 Module** (`modules/s3/main.tf`):
```hcl
resource "aws_s3_bucket" "bronze" {
  bucket = "${var.environment}-${var.project}-bronze"
  
  tags = {
    Environment = var.environment
    Layer       = "bronze"
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket" "silver" {
  bucket = "${var.environment}-${var.project}-silver"
  
  tags = {
    Environment = var.environment
    Layer       = "silver"
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket" "gold" {
  bucket = "${var.environment}-${var.project}-gold"
  
  tags = {
    Environment = var.environment
    Layer       = "gold"
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_versioning" "silver_versioning" {
  bucket = aws_s3_bucket.silver.id
  
  versioning_configuration {
    status = "Enabled"
  }
}
```

**Kinesis Module** (`modules/kinesis/main.tf`):
```hcl
resource "aws_kinesis_stream" "measurements" {
  name             = var.stream_name
  shard_count      = var.shard_count
  retention_period = 24

  shard_level_metrics = [
    "IncomingBytes",
    "IncomingRecords",
    "OutgoingBytes",
    "OutgoingRecords",
  ]

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
```

**DynamoDB Module** (`modules/dynamodb/main.tf`):
```hcl
resource "aws_dynamodb_table" "speed_layer" {
  name           = "${var.project}-realtime"
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

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_dynamodb_table" "dead_letter_queue" {
  name           = "${var.project}-dlq"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "error_id"

  attribute {
    name = "error_id"
    type = "S"
  }

  tags = {
    Environment = var.environment
    Purpose     = "dead-letter-queue"
    ManagedBy   = "terraform"
  }
}
```

---

### 1.4 Common Utilities

**File**: `src/common/config.py`

```python
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
import yaml


class S3Config(BaseModel):
    endpoint_url: str = "http://localhost:4566"
    bronze_bucket: str = "dev-air-quality-bronze"
    silver_bucket: str = "dev-air-quality-silver"
    gold_bucket: str = "dev-air-quality-gold"
    region: str = "us-east-1"


class KinesisConfig(BaseModel):
    endpoint_url: str = "http://localhost:4566"
    stream_name: str = "air-quality-measurements"
    region: str = "us-east-1"


class DynamoDBConfig(BaseModel):
    endpoint_url: str = "http://localhost:4566"
    realtime_table: str = "air-quality-realtime"
    dlq_table: str = "air-quality-dlq"
    region: str = "us-east-1"


class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    database: str = "air_quality_warehouse"
    user: str = "airflow"
    password: str = "airflow"


class AppConfig(BaseModel):
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    environment: str = "dev"
    s3: S3Config = Field(default_factory=S3Config)
    kinesis: KinesisConfig = Field(default_factory=KinesisConfig)
    dynamodb: DynamoDBConfig = Field(default_factory=DynamoDBConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)

    @classmethod
    def from_yaml(cls, config_path: Optional[Path] = None) -> "AppConfig":
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        
        if not config_path.exists():
            return cls()
        
        with open(config_path) as f:
            data = yaml.safe_load(f)
        
        return cls(**data)


config = AppConfig.from_yaml()
```

**File**: `src/common/logger.py`

```python
import logging
import sys
from pathlib import Path


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Path | None = None
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
```

**File**: `src/common/aws_client.py`

```python
import boto3
from botocore.client import BaseClient
from src.common.config import config


class AWSClientFactory:
    @staticmethod
    def create_s3_client() -> BaseClient:
        return boto3.client(
            "s3",
            endpoint_url=config.s3.endpoint_url,
            region_name=config.s3.region,
            aws_access_key_id="test",
            aws_secret_access_key="test"
        )
    
    @staticmethod
    def create_kinesis_client() -> BaseClient:
        return boto3.client(
            "kinesis",
            endpoint_url=config.kinesis.endpoint_url,
            region_name=config.kinesis.region,
            aws_access_key_id="test",
            aws_secret_access_key="test"
        )
    
    @staticmethod
    def create_dynamodb_client() -> BaseClient:
        return boto3.client(
            "dynamodb",
            endpoint_url=config.dynamodb.endpoint_url,
            region_name=config.dynamodb.region,
            aws_access_key_id="test",
            aws_secret_access_key="test"
        )
```

---

### 1.5 Makefile Automation

**File**: `Makefile`

```makefile
.PHONY: help install infra-up infra-down terraform-init terraform-apply terraform-destroy clean

help:
	@echo "Available commands:"
	@echo "  make install           - Install Python dependencies"
	@echo "  make infra-up          - Start all Docker services"
	@echo "  make infra-down        - Stop all Docker services"
	@echo "  make terraform-init    - Initialize Terraform"
	@echo "  make terraform-apply   - Apply Terraform configuration"
	@echo "  make terraform-destroy - Destroy Terraform resources"
	@echo "  make clean             - Clean all generated files"

install:
	poetry install
	poetry run pre-commit install

infra-up:
	docker-compose -f infrastructure/docker/docker-compose.yml up -d
	@echo "Waiting for services to be ready..."
	sleep 10
	docker-compose -f infrastructure/docker/docker-compose.yml ps

infra-down:
	docker-compose -f infrastructure/docker/docker-compose.yml down

terraform-init:
	cd infrastructure/terraform && terraform init

terraform-apply:
	cd infrastructure/terraform && terraform apply -var-file=environments/dev.tfvars -auto-approve

terraform-destroy:
	cd infrastructure/terraform && terraform destroy -var-file=environments/dev.tfvars -auto-approve

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
```

---

## Validation Steps

### 1. Verify Docker Services
```bash
make infra-up
docker ps
```

**Expected Output**: All containers running (localstack, postgres, redis, airflow, spark)

### 2. Test LocalStack
```bash
aws --endpoint-url=http://localhost:4566 s3 ls
```

### 3. Verify Terraform
```bash
make terraform-init
make terraform-apply
aws --endpoint-url=http://localhost:4566 s3 ls
```

**Expected**: See bronze, silver, gold buckets

### 4. Access UIs
- Airflow: http://localhost:8080 (airflow/airflow)
- Spark: http://localhost:8081
- Grafana: http://localhost:3000 (admin/admin)

---

## Deliverables Checklist

- [ ] Project structure created
- [ ] `pyproject.toml` with dependencies
- [ ] Docker Compose with all services
- [ ] Terraform modules (S3, Kinesis, DynamoDB)
- [ ] Common utilities (config, logger, AWS clients)
- [ ] Makefile automation
- [ ] All services running
- [ ] Infrastructure provisioned
- [ ] UIs accessible

---

## Next Phase

Proceed to [Phase 2: Data Generation](./phase2_data_generation.md)
