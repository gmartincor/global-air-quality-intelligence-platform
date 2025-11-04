# 🌍 Global Air Quality Intelligence Platform

Production-grade data engineering platform demonstrating Lambda Architecture with real-time and batch processing for air quality monitoring.


## 🎯 Project Overview

This platform showcases enterprise-level data engineering practices through:

- **Lambda Architecture** - Speed layer (Flink/Kinesis) + Batch layer (Spark/Airflow) + Serving layer
- **Medallion Architecture** - Bronze (raw) → Silver (cleaned) → Gold (business) data flow
- **Infrastructure as Code** - Terraform modules for reproducible infrastructure
- **LocalStack** - Zero-cost AWS simulation (S3, Kinesis, DynamoDB)
- **Docker-First Development** - Consistent environment across development and production
- **Clean Code** - SOLID, DRY, KISS, YAGNI principles applied throughout

## 🏗️ Architecture

```
Data Generation → Speed Layer (Kinesis/Flink) → DynamoDB (24h cache)
                ↓
                Batch Layer (Airflow/Spark) → Delta Lake → dbt → PostgreSQL
                ↓
                Serving Layer (Unified API + Dashboards)
```

## 🚀 Quick Start

### Prerequisites

- Docker Desktop 4.20+
- Make

### Installation

```bash
git clone <repo-url>
cd global-air-quality

make dev-build
make up
make terraform-init
make terraform-apply
```

For detailed setup instructions, see [GETTING_STARTED.md](GETTING_STARTED.md).

### Access UIs

- **Airflow**: http://localhost:8080 (admin/admin)
- **Spark**: http://localhost:8081
- **LocalStack**: http://localhost:4566

### Development Workflow

```bash
make dev-shell
make format
make lint
make test
```

## 📁 Project Structure

```
global-air-quality/
├── infrastructure/
│   ├── terraform/
│   │   └── modules/
│   └── docker/
│       ├── docker-compose.yml
│       └── Dockerfile
├── src/
│   └── common/               # Shared utilities (DRY principle)
│       ├── config.py         # Type-safe configuration with Pydantic
│       ├── logger.py         # Centralized logging
│       ├── exceptions.py     # Custom exception hierarchy
│       ├── aws/
│       │   └── client_factory.py  # AWS client factory with error handling
│       └── utils/
│           ├── validators.py # Input validation functions
│           └── retry.py      # Retry decorator with backoff
├── tests/
│   └── unit/                 # Unit tests with >90% coverage
├── config/
│   └── config.yaml          # Environment configuration
├── .pre-commit-config.yaml  # Code quality hooks
├── pyproject.toml           # Poetry dependencies
├── Makefile                 # Automation commands
└── README.md
```

## 🛠️ Technology Stack

**Infrastructure**: Terraform, LocalStack, Docker Compose  
**Processing**: Apache Spark, Apache Flink, dbt  
**Orchestration**: Apache Airflow  
**Storage**: S3 (LocalStack), Delta Lake, PostgreSQL, DynamoDB  
**Quality**: Great Expectations, pytest  
**Development**: Docker, Poetry, Make



## 🛠️ Development Commands

```bash
make dev-build        
make up               
make dev-shell        

make format           
make lint             
make type-check       
make test             
make test-cov         

make logs             
make ps               
make restart          

make terraform-init   
make terraform-plan   
make terraform-apply  
make terraform-destroy

make clean            
make clean-all        
```
