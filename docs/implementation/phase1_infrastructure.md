# Phase 1: Infrastructure & Environment Setup

**Duration**: 1 week  
**Prerequisites**: Docker Desktop, Terraform, Python 3.10+, Make

## Objectives

- Provision AWS infrastructure using Terraform modules
- Configure containerized environment via Docker Compose
- Establish development workflow automation
- Implement infrastructure as code best practices

---

## 1.1 Project Structure

**Responsibility**: Establish base directory hierarchy following separation of concerns

**Structure**:
```
global-air-quality/
├── infrastructure/
│   ├── terraform/modules/     # Reusable Terraform components
│   ├── terraform/environments/ # Environment-specific configs
│   └── docker/                # Container definitions
├── src/
│   └── common/                # Shared utilities (DRY)
│       ├── aws/               # AWS client factory
│       └── utils/             # Helper functions
├── config/                    # Configuration files
├── tests/                     # Test suites
├── Makefile                   # Automation commands
└── pyproject.toml             # Dependencies
```

**Principles Applied**: SRP (separation by layer), DRY (shared utilities)

---

## 1.2 Dependency Management

**File**: `pyproject.toml`

**Responsibility**: Define all Python dependencies with version constraints

**Required Dependencies**:
- Runtime: `pyspark ^3.5.0`, `delta-spark ^3.0.0`, `boto3 ^1.34.0`, `pydantic ^2.5.0`, `pyyaml ^6.0.1`
- Development: `pytest ^7.4.0`, `black ^23.11.0`, `mypy ^1.7.0`

**Constraints**: Python 3.10+, use Poetry for management

---

## 1.3 Configuration Management

**Module**: `src/common/config.py`

**Responsibility**: Centralized configuration with validation (DIP - depend on abstraction)

**Requirements**:
- Use Pydantic models for validation
- Support environment-based configs (dev, prod)
- Singleton pattern for global config access
- YAML-based configuration in `config/config.yaml`

**Contract**:
```python
class AppConfig:
    def from_yaml(path: Path) -> AppConfig
    
class AWSConfig:
    endpoint_url: str
    region: str
    
class S3Config:
    bronze_bucket: str
    silver_bucket: str
    gold_bucket: str
```

**Validation**: Config must be loaded before any service initialization

---

## 1.4 AWS Client Factory

**Module**: `src/common/aws/client_factory.py`

**Responsibility**: Create AWS service clients with consistent configuration (DRY, DIP)

**Requirements**:
- Single source for client creation
- Support LocalStack and AWS seamlessly
- LRU cache for session config
- Type-hinted return values

**Contract**:
```python
class AWSClientFactory:
    @classmethod
    def create_client(service_name: str) -> BaseClient
```

**Services Required**: S3, Kinesis, DynamoDB

---

## 1.5 Docker Infrastructure

**File**: `infrastructure/docker/docker-compose.yml`

**Responsibility**: Define all containerized services for local development

**Services**:

| Service | Port | Purpose |
|---------|------|---------|
| LocalStack | 4566 | AWS simulation |
| PostgreSQL | 5432 | Data warehouse |
| Redis | 6379 | Airflow backend |
| Airflow Webserver | 8080 | Orchestration UI |
| Airflow Scheduler | - | DAG execution |
| Spark Master | 8081, 7077 | Processing |
| Spark Worker | - | Worker nodes |

**Requirements**:
- Use anchor pattern for Airflow config reuse (DRY)
- Network: `air-quality-network` for inter-service communication
- Volumes: Persist LocalStack data, PostgreSQL data, Airflow logs
- Airflow executor: CeleryExecutor

**Unified Dockerfile** (`infrastructure/docker/Dockerfile`):
- Multi-stage build with `dev` and `airflow` targets
- Configurable base image via build args
- Supports Java 11 (Airflow) and Java 17 (dev)
- Install project dependencies via Poetry
- Optimized layer caching

---

## 1.6 Terraform Infrastructure as Code

**Responsibility**: Provision AWS resources declaratively

### Main Configuration (`infrastructure/terraform/main.tf`)

**Requirements**:
- Configure AWS provider for LocalStack
- Define common tags (Environment, Project, ManagedBy)
- Use modular approach (storage, streaming, database)

**Variables** (`variables.tf`):
- `aws_region`: "us-east-1"
- `environment`: "dev"
- `project_name`: "air-quality"
- `localstack_endpoint`: "http://localhost:4566"

### Module: Storage (`modules/storage/`)

**Responsibility**: Create S3 buckets for medallion architecture

**Resources**:
- Buckets: bronze, silver, gold
- Naming: `${environment}-${project}-${layer}`
- Silver bucket: Enable versioning
- Tags: Include layer identifier

**Outputs**: Map of bucket names by layer

### Module: Streaming (`modules/streaming/`)

**Responsibility**: Provision Kinesis stream

**Resources**:
- Stream name: `${project}-measurements`
- Retention: 24 hours
- Shard count: Configurable (default 1)
- Metrics: IncomingBytes, IncomingRecords

**Outputs**: Stream name

### Module: Database (`modules/database/`)

**Responsibility**: Create DynamoDB tables

**Resources**:
- Speed layer table: `${project}-realtime`
  - Hash key: city_id (S)
  - Range key: timestamp (N)
  - TTL: Enabled
- DLQ table: `${project}-dlq`
  - Hash key: error_id (S)
  
**Billing**: PAY_PER_REQUEST

---

## 1.7 Automation Workflow

**File**: `Makefile`

**Responsibility**: Provide simple commands for common operations (KISS)

**Required Targets**:

| Command | Purpose |
|---------|---------|
| `make help` | Display available commands |
| `make install` | Install dependencies |
| `make infra-up` | Start Docker services |
| `make infra-down` | Stop Docker services |
| `make terraform-init` | Initialize Terraform |
| `make terraform-apply` | Provision infrastructure |
| `make clean` | Remove generated files |

**Requirements**:
- Idempotent operations
- Clear output messages
- Wait for services to be ready (sleep after startup)

---

## 1.8 Configuration File

**File**: `config/config.yaml`

**Responsibility**: Environment-specific settings

**Required Sections**:
```yaml
environment: dev

aws:
  endpoint_url: http://localhost:4566
  region: us-east-1

s3:
  bronze_bucket: dev-air-quality-bronze
  silver_bucket: dev-air-quality-silver
  gold_bucket: dev-air-quality-gold
```

---

## Validation Criteria

### Success Criteria:

1. **Services Running**:
   ```bash
   make infra-up
   docker ps
   ```
   Expected: 7 containers running

2. **Infrastructure Provisioned**:
   ```bash
   make terraform-apply
   aws --endpoint-url=http://localhost:4566 s3 ls
   ```
   Expected: 3 S3 buckets visible

3. **UIs Accessible**:
   - Airflow: http://localhost:8080
   - Spark: http://localhost:8081

4. **Configuration Loaded**:
   ```python
   from src.common.config import config
   assert config.environment == "dev"
   ```

### Acceptance Tests:

- [ ] All Docker containers healthy
- [ ] Terraform state shows 3 S3 buckets, 1 Kinesis stream, 2 DynamoDB tables
- [ ] Config module loads without errors
- [ ] AWS client factory creates S3 client successfully
- [ ] Airflow UI accessible
- [ ] No hardcoded credentials in code

---

## Design Principles Applied

**SOLID**:
- **SRP**: Each module has single responsibility
- **DIP**: Depend on config abstraction, not hardcoded values

**DRY**:
- Shared utilities in `common/`
- Terraform modules reusable
- Docker Compose anchors for Airflow config

**KISS**:
- Simple Makefile commands
- Straightforward directory structure
- Minimal abstraction layers

**YAGNI**:
- Only essential services included
- No speculative infrastructure

---

## Next Phase

[Phase 2: Data Generation](./phase2_data_generation.md)
