# Phase 2: Data Generation

**Duration**: 1 week  
**Prerequisites**: Phase 1 completed, infrastructure running

---

## Objectives

- Generate synthetic batch data (sample: 440K records, full: 13M records)
- Build realistic IoT stream simulator
- Implement data quality patterns from inception
- Create configurable generators with realistic patterns

---

## Tasks Breakdown

### 2.1 Batch Data Generator

**File Structure**:
```
src/data_generation/
├── __init__.py
├── batch_generator.py
├── stream_simulator.py
├── generators/
│   ├── __init__.py
│   ├── sensor_data.py
│   ├── weather_patterns.py
│   ├── geographic_patterns.py
│   └── temporal_patterns.py
└── models/
    ├── __init__.py
    └── measurement.py
```

**Data Model** (`src/data_generation/models/measurement.py`):
```python
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class AirQualityMeasurement(BaseModel):
    city_id: str
    city_name: str
    country_name: str
    country_code: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timestamp: datetime
    pm25_value: float = Field(ge=0, le=500)
    pm10_value: float = Field(ge=0, le=600)
    no2_value: float = Field(ge=0, le=400)
    so2_value: float = Field(ge=0, le=300)
    co_value: float = Field(ge=0, le=50)
    o3_value: float = Field(ge=0, le=300)
    temperature_c: float = Field(ge=-50, le=60)
    humidity_pct: int = Field(ge=0, le=100)
    wind_speed_kmh: float = Field(ge=0, le=200)
    
    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        if len(v) != 2 or not v.isupper():
            raise ValueError("Country code must be 2 uppercase letters")
        return v
```

**Geographic Patterns** (`src/data_generation/generators/geographic_patterns.py`):
```python
from dataclasses import dataclass
import numpy as np


@dataclass
class CityProfile:
    city_id: str
    city_name: str
    country_name: str
    country_code: str
    latitude: float
    longitude: float
    population: int
    is_coastal: bool
    is_industrial: bool
    base_pollution_level: float


class GeographicPatternGenerator:
    CITIES = [
        CityProfile("NYC001", "New York", "United States", "US", 40.7128, -74.0060, 8_336_000, True, False, 35.0),
        CityProfile("LON001", "London", "United Kingdom", "GB", 51.5074, -0.1278, 8_982_000, False, False, 42.0),
        CityProfile("TOK001", "Tokyo", "Japan", "JP", 35.6762, 139.6503, 13_960_000, True, True, 38.0),
        CityProfile("DEL001", "Delhi", "India", "IN", 28.7041, 77.1025, 30_291_000, False, True, 125.0),
        CityProfile("SHA001", "Shanghai", "China", "CN", 31.2304, 121.4737, 27_059_000, True, True, 78.0),
        CityProfile("BEI001", "Beijing", "China", "CN", 39.9042, 116.4074, 21_540_000, False, True, 95.0),
        CityProfile("MEX001", "Mexico City", "Mexico", "MX", 19.4326, -99.1332, 21_782_000, False, False, 65.0),
        CityProfile("SAO001", "São Paulo", "Brazil", "BR", -23.5505, -46.6333, 12_325_000, False, True, 48.0),
        CityProfile("MUM001", "Mumbai", "India", "IN", 19.0760, 72.8777, 20_411_000, True, True, 87.0),
        CityProfile("CAI001", "Cairo", "Egypt", "EG", 30.0444, 31.2357, 20_902_000, False, False, 92.0),
    ]
    
    @classmethod
    def get_city_profiles(cls, mode: str = "sample") -> list[CityProfile]:
        if mode == "sample":
            return cls.CITIES[:10]
        return cls.CITIES
    
    @staticmethod
    def apply_coastal_effect(base_pollution: float, is_coastal: bool) -> float:
        return base_pollution * 0.75 if is_coastal else base_pollution
    
    @staticmethod
    def apply_industrial_effect(base_pollution: float, is_industrial: bool) -> float:
        return base_pollution * 1.35 if is_industrial else base_pollution
```

**Temporal Patterns** (`src/data_generation/generators/temporal_patterns.py`):
```python
from datetime import datetime, time
import numpy as np


class TemporalPatternGenerator:
    
    @staticmethod
    def get_hour_of_day_multiplier(hour: int) -> float:
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            return 1.4
        elif 22 <= hour or hour <= 5:
            return 0.6
        return 1.0
    
    @staticmethod
    def get_day_of_week_multiplier(weekday: int) -> float:
        if weekday >= 5:
            return 0.8
        return 1.0
    
    @staticmethod
    def get_seasonal_multiplier(month: int, is_northern_hemisphere: bool) -> float:
        winter_months = [12, 1, 2] if is_northern_hemisphere else [6, 7, 8]
        if month in winter_months:
            return 1.25
        return 1.0
    
    @staticmethod
    def add_sensor_noise(value: float, noise_pct: float = 0.05) -> float:
        noise = np.random.normal(0, value * noise_pct)
        return max(0, value + noise)
```

**Weather Patterns** (`src/data_generation/generators/weather_patterns.py`):
```python
import numpy as np


class WeatherPatternGenerator:
    
    @staticmethod
    def generate_temperature(latitude: float, month: int) -> float:
        base_temp = 15.0
        latitude_effect = -0.3 * abs(latitude)
        seasonal_effect = 10 * np.cos((month - 1) * np.pi / 6)
        
        if latitude < 0:
            seasonal_effect *= -1
        
        temp = base_temp + latitude_effect + seasonal_effect
        return round(temp + np.random.normal(0, 3), 1)
    
    @staticmethod
    def generate_humidity(temperature: float) -> int:
        base_humidity = 60
        temp_effect = -0.5 * (temperature - 20)
        humidity = base_humidity + temp_effect + np.random.normal(0, 10)
        return int(np.clip(humidity, 0, 100))
    
    @staticmethod
    def generate_wind_speed() -> float:
        return round(np.random.gamma(3, 2), 1)
    
    @staticmethod
    def apply_wind_effect(pollution: float, wind_speed: float) -> float:
        reduction = min(0.3, wind_speed / 100)
        return pollution * (1 - reduction)
    
    @staticmethod
    def apply_rain_effect(pollution: float, is_raining: bool) -> float:
        return pollution * 0.6 if is_raining else pollution
    
    @staticmethod
    def is_raining(humidity: int) -> bool:
        rain_probability = max(0, (humidity - 70) / 30)
        return np.random.random() < rain_probability
```

**Sensor Data Generator** (`src/data_generation/generators/sensor_data.py`):
```python
from datetime import datetime
import numpy as np
from src.data_generation.generators.geographic_patterns import CityProfile
from src.data_generation.generators.temporal_patterns import TemporalPatternGenerator
from src.data_generation.generators.weather_patterns import WeatherPatternGenerator
from src.data_generation.models.measurement import AirQualityMeasurement


class SensorDataGenerator:
    
    def __init__(self):
        self.temporal_gen = TemporalPatternGenerator()
        self.weather_gen = WeatherPatternGenerator()
    
    def generate_measurement(
        self,
        city: CityProfile,
        timestamp: datetime
    ) -> AirQualityMeasurement:
        
        temperature = self.weather_gen.generate_temperature(city.latitude, timestamp.month)
        humidity = self.weather_gen.generate_humidity(temperature)
        wind_speed = self.weather_gen.generate_wind_speed()
        is_raining = self.weather_gen.is_raining(humidity)
        
        is_northern = city.latitude > 0
        base_pollution = city.base_pollution_level
        
        base_pollution *= self.temporal_gen.get_hour_of_day_multiplier(timestamp.hour)
        base_pollution *= self.temporal_gen.get_day_of_week_multiplier(timestamp.weekday())
        base_pollution *= self.temporal_gen.get_seasonal_multiplier(timestamp.month, is_northern)
        
        base_pollution = self.weather_gen.apply_wind_effect(base_pollution, wind_speed)
        base_pollution = self.weather_gen.apply_rain_effect(base_pollution, is_raining)
        
        pm25 = self.temporal_gen.add_sensor_noise(base_pollution)
        pm10 = self.temporal_gen.add_sensor_noise(pm25 * 1.5)
        no2 = self.temporal_gen.add_sensor_noise(base_pollution * 0.4)
        so2 = self.temporal_gen.add_sensor_noise(base_pollution * 0.3)
        co = self.temporal_gen.add_sensor_noise(base_pollution * 0.08)
        o3 = self.temporal_gen.add_sensor_noise(base_pollution * 0.5)
        
        return AirQualityMeasurement(
            city_id=city.city_id,
            city_name=city.city_name,
            country_name=city.country_name,
            country_code=city.country_code,
            latitude=city.latitude,
            longitude=city.longitude,
            timestamp=timestamp,
            pm25_value=round(pm25, 2),
            pm10_value=round(pm10, 2),
            no2_value=round(no2, 2),
            so2_value=round(so2, 2),
            co_value=round(co, 2),
            o3_value=round(o3, 2),
            temperature_c=temperature,
            humidity_pct=humidity,
            wind_speed_kmh=wind_speed
        )
```

**Batch Generator Main** (`src/data_generation/batch_generator.py`):
```python
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from tqdm import tqdm

from src.common.config import config
from src.common.logger import setup_logger
from src.data_generation.generators.geographic_patterns import GeographicPatternGenerator
from src.data_generation.generators.sensor_data import SensorDataGenerator

logger = setup_logger(__name__)


class BatchDataGenerator:
    
    def __init__(self, mode: str = "sample"):
        self.mode = mode
        self.sensor_gen = SensorDataGenerator()
        self.cities = GeographicPatternGenerator.get_city_profiles(mode)
        
        if mode == "sample":
            self.start_date = datetime(2024, 1, 1)
            self.end_date = datetime(2024, 12, 31)
        else:
            self.start_date = datetime(2020, 1, 1)
            self.end_date = datetime(2024, 12, 31)
    
    def generate(self) -> pd.DataFrame:
        logger.info(f"Generating {self.mode} dataset")
        logger.info(f"Cities: {len(self.cities)}")
        logger.info(f"Date range: {self.start_date} to {self.end_date}")
        
        measurements = []
        current_date = self.start_date
        
        total_days = (self.end_date - self.start_date).days + 1
        
        with tqdm(total=total_days * len(self.cities) * 24) as pbar:
            while current_date <= self.end_date:
                for hour in range(24):
                    timestamp = current_date.replace(hour=hour)
                    
                    for city in self.cities:
                        measurement = self.sensor_gen.generate_measurement(city, timestamp)
                        measurements.append(measurement.model_dump())
                        pbar.update(1)
                
                current_date += timedelta(days=1)
        
        df = pd.DataFrame(measurements)
        logger.info(f"Generated {len(df):,} records")
        return df
    
    def save_to_parquet(self, df: pd.DataFrame, output_path: Path | None = None):
        if output_path is None:
            output_path = config.project_root / "data" / "generated" / f"batch_{self.mode}.parquet"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, compression="snappy", index=False)
        
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Saved to {output_path} ({file_size_mb:.2f} MB)")


def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["sample", "full"], default="sample")
    args = parser.parse_args()
    
    generator = BatchDataGenerator(mode=args.mode)
    df = generator.generate()
    generator.save_to_parquet(df)


if __name__ == "__main__":
    main()
```

---

### 2.2 Stream Data Simulator

**File**: `src/data_generation/stream_simulator.py`

```python
import time
import json
from datetime import datetime
from typing import Generator
import random

from src.common.config import config
from src.common.logger import setup_logger
from src.common.aws_client import AWSClientFactory
from src.data_generation.generators.geographic_patterns import GeographicPatternGenerator
from src.data_generation.generators.sensor_data import SensorDataGenerator

logger = setup_logger(__name__)


class StreamSimulator:
    
    def __init__(self, mode: str = "development"):
        self.mode = mode
        self.sensor_gen = SensorDataGenerator()
        self.kinesis_client = AWSClientFactory.create_kinesis_client()
        
        if mode == "development":
            self.num_sensors = 10
            self.messages_per_second = 1
        else:
            self.num_sensors = 1000
            self.messages_per_second = 33
        
        all_cities = GeographicPatternGenerator.get_city_profiles("full")
        self.cities = random.sample(all_cities, min(self.num_sensors, len(all_cities)))
        
        logger.info(f"Stream simulator initialized: {mode} mode")
        logger.info(f"Sensors: {self.num_sensors}, Rate: {self.messages_per_second} msgs/sec")
    
    def generate_messages(self) -> Generator[dict, None, None]:
        while True:
            city = random.choice(self.cities)
            timestamp = datetime.utcnow()
            
            measurement = self.sensor_gen.generate_measurement(city, timestamp)
            
            if random.random() < 0.001:
                logger.warning(f"Simulating sensor failure for {city.city_id}")
                continue
            
            message = {
                **measurement.model_dump(),
                "timestamp": measurement.timestamp.isoformat(),
                "message_id": f"{city.city_id}_{int(timestamp.timestamp())}",
                "is_duplicate": random.random() < 0.005
            }
            
            yield message
    
    def send_to_kinesis(self, message: dict):
        try:
            self.kinesis_client.put_record(
                StreamName=config.kinesis.stream_name,
                Data=json.dumps(message),
                PartitionKey=message["city_id"]
            )
        except Exception as e:
            logger.error(f"Failed to send message to Kinesis: {e}")
    
    def run(self):
        logger.info("Starting stream simulator")
        message_generator = self.generate_messages()
        
        interval = 1.0 / self.messages_per_second
        
        try:
            while True:
                message = next(message_generator)
                self.send_to_kinesis(message)
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Stream simulator stopped")


def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["development", "production"], default="development")
    args = parser.parse_args()
    
    simulator = StreamSimulator(mode=args.mode)
    simulator.run()


if __name__ == "__main__":
    main()
```

---

### 2.3 Configuration File

**File**: `config/config.yaml`

```yaml
environment: dev

s3:
  endpoint_url: http://localhost:4566
  bronze_bucket: dev-air-quality-bronze
  silver_bucket: dev-air-quality-silver
  gold_bucket: dev-air-quality-gold
  region: us-east-1

kinesis:
  endpoint_url: http://localhost:4566
  stream_name: air-quality-measurements
  region: us-east-1

dynamodb:
  endpoint_url: http://localhost:4566
  realtime_table: air-quality-realtime
  dlq_table: air-quality-dlq
  region: us-east-1

database:
  host: localhost
  port: 5432
  database: air_quality_warehouse
  user: airflow
  password: airflow
```

---

### 2.4 Makefile Updates

Add to existing `Makefile`:

```makefile
.PHONY: generate-data upload-data stream-simulator

generate-data:
	poetry run python -m src.data_generation.batch_generator --mode=$(MODE)

upload-data:
	poetry run python -m src.ingestion.batch.s3_uploader

stream-simulator:
	poetry run python -m src.data_generation.stream_simulator --mode=$(MODE)
```

---

## Validation Steps

### 1. Generate Sample Data
```bash
make generate-data MODE=sample
```

**Expected**: `data/generated/batch_sample.parquet` (~50 MB, ~440K records)

### 2. Verify Data Quality
```python
import pandas as pd

df = pd.read_parquet("data/generated/batch_sample.parquet")
print(f"Records: {len(df):,}")
print(f"Cities: {df['city_id'].nunique()}")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Null values:\n{df.isnull().sum()}")
```

### 3. Test Stream Simulator
```bash
make stream-simulator MODE=development
```

**Expected**: Messages sent to Kinesis at 1 msg/sec

---

## Deliverables Checklist

- [ ] Data models with Pydantic validation
- [ ] Geographic pattern generator
- [ ] Temporal pattern generator
- [ ] Weather pattern generator
- [ ] Sensor data generator
- [ ] Batch data generator (sample/full modes)
- [ ] Stream simulator (development/production modes)
- [ ] Configuration file
- [ ] Data generated and validated
- [ ] Stream simulator tested

---

## Next Phase

Proceed to [Phase 3: Batch Pipeline](./phase3_batch_pipeline.md)
