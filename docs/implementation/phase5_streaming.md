# Phase 5: Streaming Pipeline

**Duration**: 1.5 weeks  
**Prerequisites**: Phase 1-4 completed, Kinesis stream configured

---

## Objectives

- Implement real-time data ingestion with Kinesis
- Build windowed stream aggregations with Flink
- Store speed layer results in DynamoDB
- Implement fault tolerance with dead letter queue
- Achieve <60s end-to-end latency

---

## Architecture Overview

```
IoT Sensors → Kinesis Producer → Kinesis Stream → Consumer → DynamoDB
                                      ↓
                                 Flink Job (5-min windows)
                                      ↓
                              DynamoDB Aggregations
                                      ↓
                                  DLQ (failures)
```

**Lambda Architecture Speed Layer**: Real-time processing path complementing batch layer (Phases 3-4)

---

## Module Structure

```
src/ingestion/streaming/
├── kinesis_producer.py      # Publishes messages to stream
└── kinesis_consumer.py      # Reads from stream with error handling

src/processing/streaming/
├── dynamodb_writer.py       # Speed layer persistence
└── stream_processor.py      # Orchestrates consumer → writer flow

src/processing/flink/
└── streaming_job.py         # Windowed aggregations
```

---

## 5.1 Kinesis Producer

**File**: `src/ingestion/streaming/kinesis_producer.py`

**Responsibility**: Publish air quality measurements to Kinesis stream with idempotency guarantees (SRP)

**Requirements**:
- Use AWSClientFactory for client creation (DIP)
- Partition by city_id for parallel processing
- Add metadata: ingestion_timestamp, message_id
- Support single and batch operations
- Generate deterministic message_id from (city_id + timestamp) hash

**Contract**:
```python
class KinesisProducer:
    def __init__(self):
        ...
    
    def put_record(self, record: Dict) -> Dict:
        ...
    
    def put_records_batch(self, records: List[Dict]) -> Dict:
        ...
    
    @staticmethod
    def _generate_partition_key(record: Dict) -> str:
        ...
    
    @staticmethod
    def _generate_message_id(record: Dict) -> str:
        ...
```

**Idempotency Pattern**: message_id enables duplicate detection downstream

---

## 5.2 Kinesis Consumer

**File**: `src/ingestion/streaming/kinesis_consumer.py`

**Responsibility**: Continuously poll Kinesis shards and delegate processing (SRP)

**Requirements**:
- Accept processor callback via constructor (Strategy Pattern, DIP)
- Manage shard iterators across all shards
- Handle deserialization errors gracefully
- Send failed records to DLQ
- Support graceful shutdown (KeyboardInterrupt)
- Poll limit: 100 records per shard per iteration

**Contract**:
```python
class KinesisConsumer:
    def __init__(self, processor: Callable[[Dict], None]):
        ...
    
    def consume(self, duration_seconds: Optional[int] = None) -> None:
        ...
    
    def _get_shard_iterator(self, shard_id: str) -> str:
        ...
    
    def _process_record(self, record: Dict) -> None:
        ...
    
    def _send_to_dlq(self, record: Dict, error: str) -> None:
        ...
```

**Error Handling**:
- Deserialization failures → DLQ
- Processing exceptions → DLQ
- Shard read errors → Logged, continue to next shard

**DLQ Schema** (DynamoDB):
- Partition key: error_id (message_id or generated)
- Attributes: error_timestamp, error_message, record_data (JSON)

---

## 5.3 DynamoDB Speed Layer Writer

**File**: `src/processing/streaming/dynamodb_writer.py`

**Responsibility**: Persist real-time measurements with automatic expiration (SRP)

**Requirements**:
- Write to realtime_table with TTL (24 hours)
- Store: city_id (PK), timestamp (SK), all measurement fields
- Use Decimal type for numeric precision
- Query latest N measurements by city

**Contract**:
```python
class DynamoDBSpeedLayerWriter:
    def __init__(self):
        ...
    
    def write_measurement(self, measurement: Dict) -> None:
        ...
    
    def get_latest_measurements(self, city_id: str, limit: int = 10) -> List[Dict]:
        ...
```

**Item Schema**:
```python
{
    "city_id": {"S": "NYC001"},
    "timestamp": {"N": "1699999999"},
    "pm25_value": {"N": "45.3"},
    "aqi_value": {"N": "125"},
    "ttl": {"N": "1700086399"}
}
```

---

## 5.4 Stream Processor (Orchestration)

**File**: `src/processing/streaming/stream_processor.py`

**Responsibility**: Wire consumer and writer together (Facade Pattern)

**Requirements**:
- Instantiate DynamoDBSpeedLayerWriter
- Pass processing callback to KinesisConsumer
- Filter duplicate messages (check is_duplicate flag)
- Main entry point for streaming execution

**Contract**:
```python
class StreamProcessor:
    def __init__(self):
        ...
    
    def process_message(self, message: Dict) -> None:
        ...
    
    def run(self) -> None:
        ...
```

**Flow**: Consumer polls → process_message → Writer persists

---

## 5.5 Flink Streaming Job

**File**: `src/processing/flink/streaming_job.py`

**Responsibility**: Windowed aggregations over streaming data

**Requirements**:
- Read from Kinesis using FlinkKinesisConsumer
- Parse JSON messages, filter invalid
- Key by city_id for stateful processing
- Tumbling windows: 5 minutes
- Aggregations per window: avg_pm25, max_pm25, avg_aqi, max_aqi, record_count
- Output to stdout (extensible to DynamoDB sink)
- Parallelism: 2

**Contract**:
```python
class FlinkStreamingJob:
    def __init__(self):
        ...
    
    def create_kinesis_source(self) -> FlinkKinesisConsumer:
        ...
    
    def run(self) -> None:
        ...
```

**Window Output Schema**:
```python
{
    "city_id": "NYC001",
    "window_start": "2024-11-03T10:00:00Z",
    "window_end": "2024-11-03T10:05:00Z",
    "avg_pm25": 42.5,
    "max_pm25": 58.3,
    "record_count": 300
}
```

---

## Design Patterns Applied

### Strategy Pattern (Behavioral)
**Location**: KinesisConsumer constructor

**Implementation**: Consumer accepts processor callback via dependency injection
```python
KinesisConsumer(processor: Callable[[Dict], None])
```

**Benefit**: 
- Decouple message consumption from processing logic (OCP)
- Easy to swap processing strategies without modifying consumer
- Testable in isolation with mock processors

### Facade Pattern (Structural)
**Location**: StreamProcessor class

**Implementation**: Simplified interface for complex streaming subsystem
```python
processor = StreamProcessor()
processor.run()
```

**Benefit**:
- Hide complexity of consumer-writer coordination
- Single entry point for streaming pipeline
- Easier to understand and use

### Template Method Pattern (Behavioral)
**Location**: FlinkStreamingJob

**Implementation**: Define algorithm skeleton (setup → source → transform → sink → execute)

**Benefit**:
- Reusable streaming job structure
- Consistent execution flow across different jobs
- Override specific steps without changing overall algorithm

---

## SOLID Principles Applied

### Single Responsibility Principle (SRP)
- **KinesisProducer**: Only publishes to stream
- **KinesisConsumer**: Only reads from stream and delegates processing
- **DynamoDBSpeedLayerWriter**: Only persists to DynamoDB
- **StreamProcessor**: Only coordinates consumer and writer
- **FlinkStreamingJob**: Only windowed aggregations

Each class has one reason to change (one axis of responsibility)

### Open/Closed Principle (OCP)
- Add new processors without modifying KinesisConsumer (pass different callback)
- Extend FlinkStreamingJob with new aggregation logic without changing base structure
- Add new sinks by creating new writer classes

### Liskov Substitution Principle (LSP)
- Any Callable[[Dict], None] can be used as processor in KinesisConsumer
- Writers can be swapped (DynamoDB, S3, Redis) if they implement same interface

### Interface Segregation Principle (ISP)
- KinesisConsumer only requires processor interface: single method callback
- DynamoDBSpeedLayerWriter exposes minimal interface: write and query
- No forced implementation of unused methods

### Dependency Inversion Principle (DIP)
- All classes depend on abstractions (AWSClientFactory, config)
- StreamProcessor depends on processor abstraction, not concrete implementation
- High-level modules (StreamProcessor) don't depend on low-level details (DynamoDB client)

---

## Data Engineering Patterns Applied

### Idempotency
- **message_id**: Deterministic hash from (city_id + timestamp) enables duplicate detection
- **DynamoDB writes**: Same message_id overwrites, not duplicates
- **Replayability**: Consumer can reprocess same data safely

### Dead Letter Queue (DLQ)
- **Purpose**: Capture failed messages for later analysis/replay
- **Implementation**: DynamoDB table with error context
- **Benefit**: No data loss, debugging visibility

### Watermarking
- **ingestion_timestamp**: Track when data entered system
- **Latency calculation**: Compare ingestion_timestamp to processing time
- **SLA monitoring**: Detect processing delays

### Partitioning
- **city_id as partition key**: Parallel processing across cities
- **Benefit**: Horizontal scalability, no cross-partition transactions

### Windowing
- **Tumbling windows (5 minutes)**: Non-overlapping time buckets
- **Aggregation**: Summarize high-frequency data to reduce downstream load
- **Benefit**: Real-time insights with bounded memory

---

## Configuration Management

**File**: `config/config.yaml`

Add streaming-specific configuration:
```yaml
kinesis:
  endpoint_url: http://localhost:4566
  stream_name: air-quality-measurements
  region: us-east-1
  
dynamodb:
  endpoint_url: http://localhost:4566
  realtime_table: air-quality-realtime
  dlq_table: air-quality-dlq
  region: us-east-1
  ttl_hours: 24

flink:
  parallelism: 2
  window_minutes: 5
```

---

## Automation Commands

**File**: `Makefile`

Add streaming targets:
```makefile
.PHONY: stream-producer stream-consumer flink-job

stream-producer:
	poetry run python -m src.data_generation.stream_simulator --mode=$(MODE)

stream-consumer:
	poetry run python -m src.processing.streaming.stream_processor

flink-job:
	poetry run python -m src.processing.flink.streaming_job
```

**Usage**:
```bash
make stream-producer MODE=development
make stream-consumer
make flink-job
```

**Usage**:
```bash
make stream-producer MODE=development
make stream-consumer
make flink-job
```

---

## Validation Criteria

### 1. End-to-End Latency Test

**Objective**: Verify <60s from sensor to DynamoDB

**Steps**:
1. Start consumer: `make stream-consumer`
2. Start producer: `make stream-producer MODE=development`
3. Monitor logs for ingestion_timestamp and processing_at
4. Calculate difference: processing_at - ingestion_timestamp

**Success**: 95th percentile <60s

### 2. Message Throughput Test

**Objective**: Handle 33 msgs/sec (production mode)

**Steps**:
1. Start producer in production: `make stream-producer MODE=production`
2. Monitor Kinesis metrics: IncomingRecords, IncomingBytes
3. Verify consumer keeps up (no shard iterator lag)

**Success**: Consumer processes all records within 5 minutes of ingestion

### 3. DLQ Functionality Test

**Objective**: Failed records captured in DLQ

**Steps**:
1. Inject malformed JSON into stream
2. Verify consumer logs error
3. Query DLQ table:
```bash
aws --endpoint-url=http://localhost:4566 dynamodb scan \
    --table-name air-quality-dlq \
    --max-items 10
```

**Success**: Error record present with error_message and record_data

### 4. Flink Window Aggregation Test

**Objective**: 5-minute windows produce correct aggregates

**Steps**:
1. Start Flink job: `make flink-job`
2. Wait for 2 complete windows (10 minutes)
3. Verify stdout output contains window_start, window_end, aggregations
4. Validate: avg_pm25 < max_pm25, record_count > 0

**Success**: Valid aggregations printed every 5 minutes

### 5. DynamoDB Query Test

**Objective**: Retrieve latest measurements by city

**Steps**:
1. Insert 20 measurements for NYC001
2. Query using DynamoDBSpeedLayerWriter.get_latest_measurements("NYC001", 5)
3. Verify returns 5 most recent records, sorted by timestamp descending

**Success**: Correct count and ordering

### 6. Idempotency Test

**Objective**: Duplicate messages don't create duplicate records

**Steps**:
1. Send same measurement twice (same city_id + timestamp)
2. Query DynamoDB for city_id + timestamp combination
3. Verify only 1 record exists

**Success**: Deduplication works via message_id

---

## Monitoring Metrics

Track these metrics for SLA compliance:

| Metric | Target | Measurement |
|--------|--------|-------------|
| End-to-end latency | <60s | ingestion_timestamp → DynamoDB write |
| Throughput | 33 msgs/sec | Kinesis IncomingRecords/sec |
| Error rate | <0.5% | DLQ writes / total messages |
| Consumer lag | <30s | Shard iterator age |
| DynamoDB write latency | <100ms | PutItem duration |

---

## Deliverables Checklist

- [ ] KinesisProducer with batching support
- [ ] KinesisConsumer with DLQ error handling
- [ ] DynamoDBSpeedLayerWriter with TTL
- [ ] StreamProcessor orchestration
- [ ] FlinkStreamingJob with 5-min windows
- [ ] Configuration updated (kinesis, dynamodb, flink)
- [ ] Makefile automation commands
- [ ] End-to-end latency <60s validated
- [ ] DLQ capturing failures
- [ ] Throughput test passing (33 msgs/sec)

---

## Technical Debt & Future Improvements

**Current Limitations**:
- Flink job outputs to stdout (not DynamoDB)
- No checkpointing for consumer state recovery
- Single consumer instance (no horizontal scaling)
- No backpressure handling

**Future Enhancements** (YAGNI - implement only when needed):
- DynamoDB sink for Flink aggregations
- Consumer checkpointing with DynamoDB state table
- Auto-scaling consumer fleet with ECS/Fargate
- Rate limiting and backpressure

---

## Integration with Batch Layer

**Lambda Architecture**: Speed layer complements batch layer

| Layer | Latency | Scope | Technology |
|-------|---------|-------|------------|
| **Batch** | Hours | Complete historical data | Spark + Delta Lake |
| **Speed** | Seconds | Last 24 hours | Kinesis + Flink + DynamoDB |
| **Serving** | Merge both | Query interface | PostgreSQL + DynamoDB |

**Query Pattern**:
```python
recent = dynamodb.query(city_id, last_24h)
historical = postgresql.query(city_id, older_than_24h)
combined = recent + historical
```

---

## Next Phase

[Phase 6: Data Quality Framework](./phase6_data_quality.md)

**Prerequisites from this phase**: Streaming pipeline operational, DynamoDB populated
