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
├── batch_generator.py
├── stream_simulator.py
├── generators/
│   ├── sensor_data.py
│   ├── weather_patterns.py
│   ├── geographic_patterns.py
│   └── temporal_patterns.py
└── models/
    └── measurement.py
```

**Implementation Requirements**:

**Data Model** (`models/measurement.py`):
- Pydantic BaseModel for AirQualityMeasurement with validation
- Fields: city_id, city_name, country_name, country_code, lat/lon, timestamp
- Pollutant values: pm25, pm10, no2, so2, co, o3 (with range constraints)
- Weather: temperature_c (-50 to 60), humidity_pct (0-100), wind_speed_kmh (0-200)
- Validators: country_code must be 2 uppercase letters

**Geographic Patterns** (`generators/geographic_patterns.py`):
- CityProfile dataclass: id, name, country, coordinates, population, coastal/industrial flags, base_pollution_level
- Initial city list: NYC, London, Tokyo, Delhi, Shanghai, Beijing, Mexico City, São Paulo, Mumbai, Cairo (expandable to 300)
- Methods: `get_city_profiles(mode)`, `apply_coastal_effect()` (0.75x), `apply_industrial_effect()` (1.35x)

**Temporal Patterns** (`generators/temporal_patterns.py`):
- Hour multipliers: rush hours (7-9, 17-19) → 1.4x, night (22-5) → 0.6x
- Day of week: weekends → 0.8x, weekdays → 1.0x
- Seasonal: winter months → 1.25x (hemisphere-aware)
- Sensor noise: ±5% random normal distribution

**Weather Patterns** (`generators/weather_patterns.py`):
- Temperature generation: latitude-based + seasonal cosine wave
- Humidity calculation: inverse correlation with temperature
- Wind speed: gamma distribution (shape=3, scale=2)
- Effects: wind reduces pollution (up to 30%), rain reduces 40%

**Sensor Data Generator** (`generators/sensor_data.py`):
- Orchestrates all pattern generators
- Applies sequential effects: temporal → weather → noise
- Pollutant calculations: PM10 = 1.5×PM2.5, NO2 = 0.4×base, SO2 = 0.3×base, CO = 0.08×base, O3 = 0.5×base
- Returns validated AirQualityMeasurement instance

**Batch Generator** (`batch_generator.py`):
- Modes: "sample" (2024, 10 cities, 440K records) / "full" (2020-2024, 300 cities, 13M records)
- Triple loop: days → hours → cities
- Progress tracking with tqdm
- Output: Parquet with Snappy compression
- Logging: dataset info, record count, file size

---

### 2.2 Stream Data Simulator

**Implementation** (`stream_simulator.py`):

**Configuration**:
- Development mode: 10 sensors, 1 msg/sec
- Production mode: 1000 sensors, 33 msg/sec
- Random city sampling from full list

**Features**:
- Infinite generator with random city selection
- Real-time timestamps (UTC)
- Simulated failures: 0.1% sensor drops, 0.5% duplicates
- Kinesis integration: partition by city_id
- Message metadata: message_id, is_duplicate flag

**Kinesis Integration**:
- Uses AWSClientFactory for client creation
- JSON serialization with ISO timestamp format
- Error handling with logging
- Graceful shutdown on KeyboardInterrupt

---

### 2.3 Configuration Updates

**File**: `config/config.yaml`

Add Kinesis and DynamoDB configurations:
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
```

---

### 2.4 Makefile Updates

Add data generation commands:
```makefile
generate-data:
	poetry run python -m src.data_generation.batch_generator --mode=$(MODE)

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
Use pandas to validate: record count, unique cities, date range, null values

### 3. Test Stream Simulator
```bash
make stream-simulator MODE=development
```
**Expected**: Messages sent to Kinesis at 1 msg/sec

---

## Deliverables Checklist

- [ ] Data models with Pydantic validation
- [ ] Geographic, temporal, and weather pattern generators
- [ ] Sensor data orchestrator
- [ ] Batch data generator (sample/full modes)
- [ ] Stream simulator (development/production modes)
- [ ] Configuration file updated
- [ ] Data generated and validated

---

## Design Principles Applied

**DRY**: Pattern generators are reusable across batch and streaming
**SRP**: Each generator handles one pattern type
**OCP**: New patterns can be added without modifying existing code
**KISS**: Simple composition pattern, no complex hierarchies
**YAGNI**: Only implement sample/full modes, avoid speculative features

---

## Next Phase

[Phase 3: Batch Pipeline](./phase3_batch_pipeline.md)
