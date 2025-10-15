# Test Suite Documentation

This directory contains comprehensive automated tests for the multicam-infer project using pytest.

## 📁 Test Structure

```
tests/
├── __init__.py              # Package initialization
├── conftest.py              # Shared pytest fixtures and configuration
├── test_config.py           # Configuration and Pydantic model validation tests
├── test_roi.py              # ROI geometry operation tests
├── test_yolo_common.py      # YOLO detector tests with mocked models
└── test_publishers.py       # AWS publisher tests with boto3 mocking
```

## 🚀 Quick Start

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run Tests with Coverage

```bash
pytest --cov=src/kvs_infer --cov-report=html --cov-report=term-missing
```

View HTML coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 🎯 Test Categories

Tests are organized with pytest markers for selective execution:

### Unit Tests
Fast, isolated tests for individual functions/classes:
```bash
pytest -m unit
```

### Integration Tests
Tests that involve multiple components:
```bash
pytest -m integration
```

### AWS Tests
Tests that mock AWS services (Kinesis, S3, DynamoDB):
```bash
pytest -m aws
```

### Slow Tests
Tests that take longer to execute:
```bash
pytest -m "not slow"  # Skip slow tests
```

### GPU Tests
Tests that require GPU (currently mocked):
```bash
pytest -m gpu
```

## 📝 Test Modules

### test_config.py (489 lines)
Tests configuration loading and Pydantic model validation.

**Key Test Classes:**
- `TestYAMLLoading`: Validates YAML file loading and structure
- `TestROIConfig`: Tests ROI polygon/bbox validation, coordinate handling
- `TestYOLOConfig`: Tests YOLO configuration thresholds, class validation
- `TestCameraConfig`: Tests camera configuration with multiple ROIs
- `TestAppConfig`: Tests complete application configuration from cameras.example.yaml
- `TestConfigEdgeCases`: Tests negative coordinates, floating-point precision
- `TestConfigSerialization`: Tests dict/JSON serialization and round-trip

**Example:**
```bash
# Run only config tests
pytest tests/test_config.py -v

# Test YAML loading specifically
pytest tests/test_config.py::TestYAMLLoading -v
```

### test_roi.py (470 lines)
Tests ROI geometry operations including IoU calculations and point-in-polygon checks.

**Key Test Classes:**
- `TestIoUCalculation`: Tests Intersection over Union for bounding boxes
  - Identical boxes (IoU = 1.0)
  - No overlap (IoU = 0.0)
  - Partial overlap
  - One box inside another
  - Edge cases (touching, negative coords)
- `TestPointInPolygon`: Tests point-in-polygon algorithm
  - Simple shapes (triangle, rectangle)
  - Complex and concave polygons
  - Edge cases (on vertices, on edges)
- `TestBBoxIntersectsROI`: Tests bbox-ROI intersection logic
- `TestFilterDetectionsByROI`: Tests detection filtering by ROI
- `TestROIPerformance`: Performance tests with many vertices/detections

**Example:**
```bash
# Run ROI tests
pytest tests/test_roi.py -v

# Test IoU calculations only
pytest tests/test_roi.py::TestIoUCalculation -v
```

### test_yolo_common.py (458 lines)
Tests YOLO detector functionality with mocked models.

**Key Test Classes:**
- `TestFilterByClass`: Tests class filtering for detections
- `TestFilterByConfidence`: Tests confidence threshold filtering
- `TestApplyNMS`: Tests Non-Maximum Suppression
- `TestYOLODetector`: Tests YOLODetector initialization and prediction
- `TestTemporalConfirm`: Tests temporal confirmation across frames
  - Sliding window behavior
  - IoU-based object tracking
  - Minimum detection requirements
  - Multiple object tracking
- `TestYOLOEdgeCases`: Tests edge cases (empty frames, small detections)

**Mocking Strategy:**
```python
# YOLO model is mocked to return predefined detections
with patch('ultralytics.YOLO') as mock_yolo_class:
    mock_model = MagicMock()
    mock_model.return_value = [mock_results]
    mock_yolo_class.return_value = mock_model
```

**Example:**
```bash
# Run YOLO tests
pytest tests/test_yolo_common.py -v

# Test temporal confirmation only
pytest tests/test_yolo_common.py::TestTemporalConfirm -v
```

### test_publishers.py (552 lines)
Tests AWS publisher integrations with boto3 mocking using moto.

**Key Test Classes:**
- `TestBatchRecords`: Tests record batching logic
- `TestKinesisPublisher`: Tests Kinesis Data Streams publishing
  - Single and batch publishing
  - Partition key generation
  - Large batch splitting (500 records max)
  - Retry logic and error handling
- `TestS3Publisher`: Tests S3 object storage
  - Key format with camera_id and timestamp
  - JSON body encoding
  - Metadata and server-side encryption
  - Error handling
- `TestDynamoDBPublisher`: Tests DynamoDB table writes
  - Item structure with partition/sort keys
  - Batch write operations
  - Conditional check failures
  - TTL attributes
- `TestPublisherIntegration`: Tests multiple publishers together
- `TestPublisherPerformance`: Tests batch efficiency

**Mocking Strategy:**
```python
# Uses moto for AWS service mocking
@mock_kinesis
def test_kinesis_publish():
    # Kinesis operations are mocked in-memory
    client = boto3.client('kinesis', region_name='us-east-1')
    # ... test code
```

**Example:**
```bash
# Run publisher tests
pytest tests/test_publishers.py -v

# Test Kinesis only
pytest tests/test_publishers.py::TestKinesisPublisher -v

# Test with AWS marker
pytest -m aws -v
```

## 🔧 Configuration

### pytest.ini
Main pytest configuration file with:
- Test discovery patterns
- Coverage settings (80% minimum)
- Test markers
- Output formatting

### conftest.py
Shared pytest fixtures:
- `project_root`: Project root directory path
- `test_data_dir`: Test data directory path
- `mock_frame`: Mock video frame (numpy array)
- `sample_camera_config`: Sample camera configuration
- `sample_yolo_config`: Sample YOLO configuration
- `reset_mocks`: Automatic mock cleanup between tests

## 📊 Coverage Requirements

Minimum coverage threshold: **80%**

Coverage reports are generated in multiple formats:
- **Terminal**: `--cov-report=term-missing` shows uncovered lines
- **HTML**: `--cov-report=html` creates htmlcov/index.html
- **XML**: `--cov-report=xml` for CI/CD integration

### Check Coverage
```bash
# Generate all coverage reports
pytest --cov=src/kvs_infer --cov-report=html --cov-report=term-missing --cov-report=xml

# Fail if coverage is below 80%
pytest --cov=src/kvs_infer --cov-fail-under=80
```

## 🔍 Running Specific Tests

### By Test File
```bash
pytest tests/test_config.py
```

### By Test Class
```bash
pytest tests/test_roi.py::TestIoUCalculation
```

### By Test Function
```bash
pytest tests/test_roi.py::TestIoUCalculation::test_identical_boxes
```

### By Keyword
```bash
pytest -k "iou"  # Run tests matching "iou"
pytest -k "not slow"  # Skip slow tests
```

### By Marker
```bash
pytest -m unit  # Run unit tests
pytest -m "integration and not slow"  # Run fast integration tests
```

## 🚨 Debugging Tests

### Verbose Output
```bash
pytest -v  # Verbose test names
pytest -vv  # More verbose with full diffs
```

### Show Print Statements
```bash
pytest -s  # Show print() output
```

### Stop on First Failure
```bash
pytest -x  # Stop after first failure
pytest --maxfail=3  # Stop after 3 failures
```

### Run Last Failed Tests
```bash
pytest --lf  # Run only last failed tests
pytest --ff  # Run failed first, then others
```

### Debug with PDB
```bash
pytest --pdb  # Drop into debugger on failure
```

### Show Local Variables on Failure
```bash
pytest -l  # Show local variables in tracebacks
```

## ⚡ Performance Optimization

### Parallel Execution
```bash
# Run tests in parallel using pytest-xdist
pytest -n auto  # Use all available CPU cores
pytest -n 4  # Use 4 parallel workers
```

### Only Collect Tests
```bash
pytest --collect-only  # List all tests without running
```

### Profile Test Duration
```bash
pytest --durations=10  # Show 10 slowest tests
pytest --durations=0  # Show all test durations
```

## 🔐 Mocking Strategy

### unittest.mock for Python Objects
Used for mocking YOLO models, functions, and classes:
```python
from unittest.mock import patch, MagicMock

with patch('ultralytics.YOLO') as mock_yolo:
    mock_yolo.return_value = mock_model
    # ... test code
```

### moto for AWS Services
Used for mocking boto3 clients:
```python
from moto import mock_kinesis, mock_s3, mock_dynamodb

@mock_kinesis
def test_kinesis():
    client = boto3.client('kinesis', region_name='us-east-1')
    # Kinesis operations are mocked
```

### freezegun for Time Mocking
Used for time-dependent tests:
```python
from freezegun import freeze_time

@freeze_time("2024-01-01 12:00:00")
def test_timestamps():
    # Time is frozen at 2024-01-01 12:00:00
```

## 🎓 Best Practices

### 1. Test Organization
- One test file per module
- Group related tests in classes
- Use descriptive test names: `test_<what>_<condition>_<expected>`

### 2. Fixtures
- Use fixtures for common setup
- Keep fixtures small and focused
- Use appropriate fixture scopes (function, class, module, session)

### 3. Mocking
- Mock external dependencies (AWS, YOLO models)
- Don't mock the code under test
- Verify mock calls with `assert_called_with()`

### 4. Assertions
- Use pytest assertions, not unittest assertions
- One logical assertion per test (when possible)
- Use `pytest.approx()` for floating-point comparisons

### 5. Coverage
- Aim for high coverage, but don't sacrifice quality
- Test edge cases and error conditions
- Don't test external libraries

## 🐛 Common Issues

### Import Errors
If you get import errors, ensure `src/` is in the Python path:
```python
# conftest.py already handles this
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

### AWS Credentials
Tests use moto for mocking, so no real AWS credentials are needed. If you see credential errors:
```bash
# Set dummy credentials for tests
export AWS_ACCESS_KEY_ID=testing
export AWS_SECRET_ACCESS_KEY=testing
export AWS_DEFAULT_REGION=us-east-1
```

### YOLO Model Files
Tests mock YOLO models, so no real model files (.pt) are needed.

## 📈 Test Statistics

- **Total Test Files**: 4
- **Total Test Classes**: ~30
- **Total Test Functions**: ~100+
- **Total Lines of Test Code**: ~2,000
- **Coverage Target**: 80%+

## 🔄 CI/CD Integration

Tests run automatically on:
- Pull requests to `main` or `develop`
- Pushes to `main` or `develop`

See `.github/workflows/test.yml` for the CI configuration.

### GitHub Actions Jobs
1. **test**: Main test job with coverage reporting
2. **test-matrix**: Test across Python 3.10, 3.11, 3.12
3. **lint**: Code quality checks (black, flake8, isort, mypy, pylint)
4. **security**: Security scanning (safety, bandit)

## 📚 Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [moto documentation](http://docs.getmoto.org/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)

## 🤝 Contributing

When adding new tests:
1. Follow existing patterns and conventions
2. Add appropriate markers (`@pytest.mark.unit`, etc.)
3. Use descriptive test names
4. Add docstrings to complex tests
5. Ensure tests are isolated and deterministic
6. Run the full test suite before committing
7. Maintain or improve code coverage

---

**Questions or issues?** Check the project README or open an issue on GitHub.
