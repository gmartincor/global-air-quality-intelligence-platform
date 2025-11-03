# Phase 5: Streaming Pipeline

**Duration**: 1.5 weeks  
**Prerequisites**: Phase 1-4 completed, Kinesis stream configured

---

## Objectives

- Implement Kinesis producer for real-time data ingestion
- Build Flink streaming job for windowed aggregations
- Store speed layer results in DynamoDB
- Implement dead letter queue for failed messages
- Achieve <60s end-to-end latency

---

## Tasks Breakdown

### 5.1 Kinesis Producer

**File**: `src/ingestion/streaming/kinesis_producer.py`

```python
import json
import time
from datetime import datetime
from typing import Dict
import hashlib

from src.common.config import config
from src.common.logger import setup_logger
from src.common.aws_client import AWSClientFactory

logger = setup_logger(__name__)


class KinesisProducer:
    
    def __init__(self):
        self.client = AWSClientFactory.create_kinesis_client()
        self.stream_name = config.kinesis.stream_name
        self.batch_size = 500
        self.batch = []
    
    def _generate_partition_key(self, record: Dict) -> str:
        return record.get("city_id", "default")
    
    def put_record(self, record: Dict):
        try:
            record_with_metadata = {
                **record,
                "ingestion_timestamp": datetime.utcnow().isoformat(),
                "message_id": self._generate_message_id(record)
            }
            
            response = self.client.put_record(
                StreamName=self.stream_name,
                Data=json.dumps(record_with_metadata),
                PartitionKey=self._generate_partition_key(record)
            )
            
            logger.debug(f"Record sent: {response['SequenceNumber']}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to send record: {e}")
            raise
    
    def put_records_batch(self, records: list[Dict]):
        if not records:
            return
        
        kinesis_records = [
            {
                "Data": json.dumps({
                    **record,
                    "ingestion_timestamp": datetime.utcnow().isoformat(),
                    "message_id": self._generate_message_id(record)
                }),
                "PartitionKey": self._generate_partition_key(record)
            }
            for record in records
        ]
        
        try:
            response = self.client.put_records(
                StreamName=self.stream_name,
                Records=kinesis_records
            )
            
            failed_count = response.get("FailedRecordCount", 0)
            if failed_count > 0:
                logger.warning(f"{failed_count} records failed to send")
            
            logger.info(f"Batch sent: {len(records) - failed_count}/{len(records)} successful")
            return response
            
        except Exception as e:
            logger.error(f"Failed to send batch: {e}")
            raise
    
    @staticmethod
    def _generate_message_id(record: Dict) -> str:
        content = f"{record.get('city_id')}_{record.get('timestamp')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
```

---

### 5.2 Kinesis Consumer

**File**: `src/ingestion/streaming/kinesis_consumer.py`

```python
import json
import time
from typing import Callable, Dict
from botocore.exceptions import ClientError

from src.common.config import config
from src.common.logger import setup_logger
from src.common.aws_client import AWSClientFactory

logger = setup_logger(__name__)


class KinesisConsumer:
    
    def __init__(self, processor: Callable[[Dict], None]):
        self.client = AWSClientFactory.create_kinesis_client()
        self.stream_name = config.kinesis.stream_name
        self.processor = processor
        self.shard_iterators = {}
    
    def _get_shard_iterator(self, shard_id: str) -> str:
        if shard_id not in self.shard_iterators:
            response = self.client.get_shard_iterator(
                StreamName=self.stream_name,
                ShardId=shard_id,
                ShardIteratorType="LATEST"
            )
            self.shard_iterators[shard_id] = response["ShardIterator"]
        
        return self.shard_iterators[shard_id]
    
    def _process_record(self, record: Dict):
        try:
            data = json.loads(record["Data"])
            self.processor(data)
        except Exception as e:
            logger.error(f"Failed to process record: {e}")
            self._send_to_dlq(record, str(e))
    
    def _send_to_dlq(self, record: Dict, error: str):
        dynamodb = AWSClientFactory.create_dynamodb_client()
        
        try:
            dynamodb.put_item(
                TableName=config.dynamodb.dlq_table,
                Item={
                    "error_id": {"S": record.get("message_id", "unknown")},
                    "error_timestamp": {"S": str(int(time.time()))},
                    "error_message": {"S": error},
                    "record_data": {"S": json.dumps(record)}
                }
            )
            logger.info("Record sent to DLQ")
        except Exception as dlq_error:
            logger.error(f"Failed to send to DLQ: {dlq_error}")
    
    def consume(self, duration_seconds: int | None = None):
        logger.info("Starting Kinesis consumer")
        
        shards_response = self.client.list_shards(StreamName=self.stream_name)
        shards = shards_response["Shards"]
        
        logger.info(f"Found {len(shards)} shards")
        
        start_time = time.time()
        
        try:
            while True:
                for shard in shards:
                    shard_id = shard["ShardId"]
                    shard_iterator = self._get_shard_iterator(shard_id)
                    
                    try:
                        response = self.client.get_records(
                            ShardIterator=shard_iterator,
                            Limit=100
                        )
                        
                        records = response.get("Records", [])
                        
                        for record in records:
                            self._process_record(record)
                        
                        self.shard_iterators[shard_id] = response.get("NextShardIterator")
                        
                        if records:
                            logger.info(f"Processed {len(records)} records from {shard_id}")
                    
                    except ClientError as e:
                        logger.error(f"Error reading from shard {shard_id}: {e}")
                
                if duration_seconds and (time.time() - start_time) > duration_seconds:
                    break
                
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
```

---

### 5.3 Flink Streaming Job

**File**: `src/processing/flink/streaming_job.py`

```python
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kinesis import FlinkKinesisConsumer
from pyflink.datastream.window import TumblingProcessingTimeWindows
from pyflink.common.time import Time
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.typeinfo import Types
import json

from src.common.config import config
from src.common.logger import setup_logger

logger = setup_logger(__name__)


class FlinkStreamingJob:
    
    def __init__(self):
        self.env = StreamExecutionEnvironment.get_execution_environment()
        self.env.set_parallelism(2)
    
    def create_kinesis_source(self):
        consumer_config = {
            "aws.region": config.kinesis.region,
            "aws.endpoint": config.kinesis.endpoint_url,
            "aws.credentials.provider": "BASIC",
            "aws.credentials.provider.basic.accesskeyid": "test",
            "aws.credentials.provider.basic.secretkey": "test",
        }
        
        return FlinkKinesisConsumer(
            config.kinesis.stream_name,
            SimpleStringSchema(),
            consumer_config
        )
    
    def parse_json(self, value: str):
        try:
            return json.loads(value)
        except:
            return None
    
    def calculate_window_aggregates(self, records):
        city_id = records[0]["city_id"]
        
        pm25_values = [r["pm25_value"] for r in records]
        aqi_values = [r["aqi_value"] for r in records]
        
        return {
            "city_id": city_id,
            "window_start": records[0]["timestamp"],
            "window_end": records[-1]["timestamp"],
            "avg_pm25": sum(pm25_values) / len(pm25_values),
            "max_pm25": max(pm25_values),
            "avg_aqi": sum(aqi_values) / len(aqi_values),
            "max_aqi": max(aqi_values),
            "record_count": len(records)
        }
    
    def run(self):
        logger.info("Starting Flink streaming job")
        
        kinesis_source = self.create_kinesis_source()
        
        stream = self.env.add_source(kinesis_source)
        
        parsed_stream = stream.map(
            lambda x: self.parse_json(x),
            output_type=Types.PICKLED_BYTE_ARRAY()
        ).filter(lambda x: x is not None)
        
        windowed_stream = (
            parsed_stream
            .key_by(lambda x: x["city_id"])
            .window(TumblingProcessingTimeWindows.of(Time.minutes(5)))
            .reduce(
                lambda a, b: {
                    **a,
                    "pm25_value": (a["pm25_value"] + b["pm25_value"]) / 2,
                    "aqi_value": max(a["aqi_value"], b["aqi_value"])
                }
            )
        )
        
        windowed_stream.print()
        
        self.env.execute("Air Quality Streaming Job")


def main():
    job = FlinkStreamingJob()
    job.run()


if __name__ == "__main__":
    main()
```

---

### 5.4 DynamoDB Speed Layer Writer

**File**: `src/processing/streaming/dynamodb_writer.py`

```python
import time
from typing import Dict
from decimal import Decimal

from src.common.config import config
from src.common.logger import setup_logger
from src.common.aws_client import AWSClientFactory

logger = setup_logger(__name__)


class DynamoDBSpeedLayerWriter:
    
    def __init__(self):
        self.client = AWSClientFactory.create_dynamodb_client()
        self.table_name = config.dynamodb.realtime_table
        self.ttl_hours = 24
    
    def write_measurement(self, measurement: Dict):
        ttl = int(time.time()) + (self.ttl_hours * 3600)
        
        item = {
            "city_id": {"S": measurement["city_id"]},
            "timestamp": {"N": str(int(time.time()))},
            "city_name": {"S": measurement["city_name"]},
            "pm25_value": {"N": str(Decimal(str(measurement["pm25_value"])))},
            "pm10_value": {"N": str(Decimal(str(measurement["pm10_value"])))},
            "aqi_value": {"N": str(measurement["aqi_value"])},
            "aqi_category": {"S": measurement["aqi_category"]},
            "temperature_c": {"N": str(Decimal(str(measurement["temperature_c"])))},
            "ttl": {"N": str(ttl)}
        }
        
        try:
            self.client.put_item(
                TableName=self.table_name,
                Item=item
            )
            logger.debug(f"Wrote measurement for {measurement['city_id']}")
        except Exception as e:
            logger.error(f"Failed to write to DynamoDB: {e}")
            raise
    
    def get_latest_measurements(self, city_id: str, limit: int = 10):
        try:
            response = self.client.query(
                TableName=self.table_name,
                KeyConditionExpression="city_id = :city_id",
                ExpressionAttributeValues={
                    ":city_id": {"S": city_id}
                },
                ScanIndexForward=False,
                Limit=limit
            )
            
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Failed to query DynamoDB: {e}")
            raise
```

---

### 5.5 Integration Script

**File**: `src/processing/streaming/stream_processor.py`

```python
from src.ingestion.streaming.kinesis_consumer import KinesisConsumer
from src.processing.streaming.dynamodb_writer import DynamoDBSpeedLayerWriter
from src.common.logger import setup_logger

logger = setup_logger(__name__)


class StreamProcessor:
    
    def __init__(self):
        self.dynamodb_writer = DynamoDBSpeedLayerWriter()
    
    def process_message(self, message: dict):
        logger.debug(f"Processing message for {message.get('city_id')}")
        
        if message.get("is_duplicate"):
            logger.warning("Duplicate message detected, skipping")
            return
        
        self.dynamodb_writer.write_measurement(message)
    
    def run(self):
        consumer = KinesisConsumer(processor=self.process_message)
        consumer.consume()


def main():
    processor = StreamProcessor()
    processor.run()


if __name__ == "__main__":
    main()
```

---

### 5.6 Makefile Updates

```makefile
.PHONY: stream-producer stream-consumer

stream-producer:
	poetry run python -m src.data_generation.stream_simulator --mode=$(MODE)

stream-consumer:
	poetry run python -m src.processing.streaming.stream_processor
```

---

## Validation Steps

### 1. Start Stream Producer
```bash
make stream-producer MODE=development
```

### 2. Start Stream Consumer
```bash
make stream-consumer
```

### 3. Verify DynamoDB Writes
```bash
aws --endpoint-url=http://localhost:4566 dynamodb scan \
    --table-name air-quality-realtime \
    --limit 10
```

### 4. Check Latency
Monitor time between producer timestamp and DynamoDB write (target: <60s)

---

## Deliverables Checklist

- [ ] Kinesis producer implemented
- [ ] Kinesis consumer with DLQ support
- [ ] Flink streaming job (5-min windows)
- [ ] DynamoDB speed layer writer
- [ ] Stream processor integration
- [ ] End-to-end streaming working
- [ ] Latency <60 seconds
- [ ] DLQ capturing failed messages

---

## Next Phase

Proceed to [Phase 6: Data Quality Framework](./phase6_data_quality.md)
