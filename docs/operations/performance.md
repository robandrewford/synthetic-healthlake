# Performance Benchmarking

This document provides performance benchmarks for the synthetic-healthlake data generation pipeline.

## Generation Performance

### Test Environment

- **Machine**: MacBook (Apple Silicon M-series)
- **Python**: 3.12+
- **Package Manager**: uv
- **Seed**: 42 (for reproducibility)

### Benchmark Results

| Dataset Size | Patients | Generation Time | Throughput |
|--------------|----------|-----------------|------------|
| Small | 100 | ~1.4s | ~71 patients/sec |
| Medium | 1,000 | ~1.1s | ~909 patients/sec |
| Large | 10,000 | ~3.5s | ~2,857 patients/sec |
| XLarge | 50,000 | ~15s | ~3,333 patients/sec |

- **Note**: Initial runs include Python/uv startup overhead (~1s)
- **Throughput increases** with dataset size due to amortized startup costs

### Output File Sizes

| Dataset | Patients | FHIR NDJSON | Person Parquet | Conditions Parquet | Measurements Parquet |
|---------|----------|-------------|----------------|-------------------|---------------------|
| Small | 100 | 59 KB | 11 KB | 9 KB | 14 KB |
| Medium | 1,000 | 590 KB | 29 KB | 40 KB | 72 KB |
| Large | 10,000 | 5.8 MB | 222 KB | 347 KB | 605 KB |
| XLarge | 50,000 | ~29 MB | ~1.1 MB | ~1.7 MB | ~3 MB |

### Storage Efficiency

| Format | Bytes per Patient | Compression Ratio |
|--------|-------------------|-------------------|
| FHIR NDJSON | ~590 bytes | 1x (baseline) |
| OMOP Parquet | ~22 bytes (person only) | 27x |
| OMOP Parquet (all tables) | ~117 bytes | 5x |

- **Parquet advantage**: Columnar compression significantly reduces storage
- **NDJSON advantage**: Human-readable, streaming-friendly

---

## Memory Usage

### Generation Process

| Dataset Size | Peak Memory (Approx) | Notes |
|--------------|---------------------|-------|
| 100 | ~100 MB | Includes Python runtime |
| 1,000 | ~120 MB | Linear scaling |
| 10,000 | ~200 MB | Pandas DataFrame overhead |
| 50,000 | ~500 MB | Consider streaming for larger |

### Memory Optimization

For datasets >50,000 patients:

1. **Batch generation**: Generate in chunks of 10k
2. **Streaming writes**: Write incrementally to avoid memory spikes
3. **Use PyArrow directly**: Skip Pandas for better memory efficiency

---

## Reproducibility

All datasets are **fully reproducible** using the `--seed` parameter:

```bash
# Generate identical datasets
./scripts/generate-sample-dataset.sh --size large --seed 42
./scripts/generate-sample-dataset.sh --size large --seed 42  # Same result
```

### Reproducibility Verification

```python
import hashlib
import pandas as pd

# Read generated data
df = pd.read_parquet("output/sample-10k/omop/person.parquet")

# Hash the data
data_hash = hashlib.md5(df.to_csv().encode()).hexdigest()
print(f"Data hash: {data_hash}")  # Should be consistent for seed=42
```

---

## Running Benchmarks

### Quick Benchmark Script

```bash
#!/bin/bash
# benchmark.sh - Run performance benchmarks

echo "=== Synthetic Data Generation Benchmarks ==="
echo ""

for size in small medium large; do
    echo "--- $size ---"
    time ./scripts/generate-sample-dataset.sh \
        --size $size \
        --output output/bench-$size \
        2>/dev/null
    echo ""
done

echo "=== File Sizes ==="
du -sh output/bench-*/
```

### Using Hyperfine for Accurate Benchmarks

```bash
# Install hyperfine (macOS)
brew install hyperfine

# Run accurate benchmark with warmup
hyperfine \
    --warmup 1 \
    --runs 3 \
    './scripts/generate-sample-dataset.sh --size medium --output output/bench-test' \
    --cleanup 'rm -rf output/bench-test'
```

---

## dbt Transformation Performance

### Estimated Performance (Based on Snowflake)

| Model | Records | Execution Time | Notes |
|-------|---------|----------------|-------|
| stg_person | 10,000 | ~2s | Source loading |
| stg_condition_occurrence | 15,000 | ~2s | Source loading |
| stg_measurement | 25,000 | ~3s | Source loading |
| dim_patient | 10,000 | ~5s | Join + transform |

- **Note**: Actual times depend on warehouse size and data volume

### dbt Run Timing

```bash
# Profile dbt run time
time dbt run --project-dir dbt/snowflake

# Run specific model with timing
dbt run --select dim_patient --timing
```

---

## Query Performance

### Sample Query Benchmarks (Estimated)

| Query Type | Records Scanned | Cold Time | Warm Time |
|------------|-----------------|-----------|-----------|
| Simple SELECT | 10,000 | ~1s | ~0.3s |
| Aggregation (COUNT/GROUP BY) | 10,000 | ~1.5s | ~0.5s |
| Join (2 tables) | 25,000 | ~2s | ~0.8s |
| Complex analytics | 50,000 | ~3s | ~1.5s |

### Optimization Tips

1. **Use Parquet format**: Columnar storage enables column pruning
2. **Partition by date**: Add `year_of_birth` partitioning for time-based queries
3. **Enable caching**: Snowflake/Athena cache query results automatically

---

## Scaling Considerations

### Dataset Size Limits

| Size | Patients | Recommended For |
|------|----------|-----------------|
| Small (100) | Quick tests | Unit tests, CI/CD |
| Medium (1k) | Integration tests | Development |
| Large (10k) | Realistic testing | Staging |
| XLarge (50k) | Performance testing | Load testing |
| 100k+ | Production-like | Capacity planning |

### Bottlenecks

1. **Generation**: CPU-bound (Faker library)
2. **I/O**: Parquet writes are fast (~100MB/s)
3. **Memory**: Pandas DataFrames for large datasets

### Recommendations by Use Case

| Use Case | Recommended Size | Generation Time | Storage |
|----------|------------------|-----------------|---------|
| CI/CD tests | 100 | ~1.5s | <1 MB |
| Local development | 1,000 | ~1.5s | ~1 MB |
| Integration testing | 10,000 | ~4s | ~7 MB |
| Performance testing | 50,000 | ~15s | ~35 MB |

---

## Related Documentation

- [Sample Dataset Documentation](../data/sample-dataset.md)
- [Cost Analysis](cost-analysis.md)
- [Data Quality Strategy](../data/data-quality-strategy.md)
