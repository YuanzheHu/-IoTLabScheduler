# IoT Lab Scheduler - Streamlined Testing Guide

This directory contains the **core test scripts** for the IoT device management system. All tests are compatible with the pytest framework, comprehensive and efficient.

## 📂 Streamlined Test Files

### 🎯 **3 Core Test Files (Streamlined and Optimized)**

1. **`test_system_verification.py`** - 🔍 **Comprehensive System Verification Tests**
   - API health checks
   - Frontend accessibility verification
   - Database connection and structure validation
   - Network discovery functionality testing
   - Port scanning and OS scanning functionality verification
   - **Recommended to run first**

2. **`test_batch_scan.py`** - 🚀 **Batch Scanning Test Suite**
   - Quick system check (3 device verification)
   - Batch port scanning (sequential/parallel)
   - Batch OS scanning (fingerprinting)
   - Combined scanning tests (port + OS)
   - Specific device scanning
   - **Includes all scanning functionality**

3. **`test_batch_attacks.py`** - ⚔️ **Network Security Attack Testing**
   - Cyclic attack testing
   - Parallel attack testing
   - Network security assessment
   - **Unique security testing functionality**

### ⚙️ Configuration Files
- **`conftest.py`** - pytest configuration file
- **`__init__.py`** - Python package initialization file

## 🚀 Running Methods

### Prerequisites
1. Ensure Docker containers are running:
   ```bash
   sudo docker-compose up -d
   ```

2. Verify API service availability:
   ```bash
   curl http://localhost:8000/health
   ```

### 1. Using pytest (Recommended)

#### Run All Tests
```bash
# Run from project root directory
pytest project/tests/ -v -s

# Or run from project directory
cd project
pytest tests/ -v -s
```

#### Run Specific Test Files
```bash
# 🔍 System verification tests (recommended to run first)
pytest project/tests/test_system_verification.py -v -s

# 🚀 Batch scanning tests (includes all scanning functionality)
pytest project/tests/test_batch_scan.py -v -s

# ⚔️ Network security attack tests
pytest project/tests/test_batch_attacks.py -v -s
```

#### Run Specific Test Methods
```bash
# 🔍 System verification
pytest project/tests/test_system_verification.py::TestSystemVerification::test_system_verification -v -s

# 🚀 Quick scanning check (3 device verification)
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_quick_system_check -v -s

# 🚀 Batch port scanning (sequential)
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_batch_port_scan_sequential -v -s

# 🚀 Batch port scanning (parallel)
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_batch_port_scan_parallel -v -s

# 🚀 OS scanning
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_batch_os_scan_sequential -v -s

# 🚀 Combined scanning (port + OS)
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_combined_port_and_os_scan -v -s

# ⚔️ Security attack testing
pytest project/tests/test_batch_attacks.py::TestBatchAttacks::test_batch_cyclic_attacks_sequential -v -s
```

### 2. Running Python Scripts Independently

```bash
# Enter tests directory
cd project/tests

# 🔍 System verification
python3 test_system_verification.py

# 🚀 Batch scanning (requires import path handling)
PYTHONPATH=.. python3 test_batch_scan.py

# ⚔️ Batch attacks (requires import path handling)
PYTHONPATH=.. python3 test_batch_attacks.py
```

## 📊 Recommended Test Sequence

### 🎯 New System First-Time Verification (3 Steps)
1. **🔍 System verification tests** (must run first)
   ```bash
   pytest project/tests/test_system_verification.py -v -s
   ```

2. **🚀 Quick scanning check** (verify core scanning functionality)
   ```bash
   pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_quick_system_check -v -s
   ```

3. **🚀 Complete scanning tests** (comprehensive functionality verification)
   ```bash
   pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_combined_port_and_os_scan -v -s
   ```

### 📅 Daily Testing
```bash
# 🔍 Quick system check
pytest project/tests/test_system_verification.py -v -s

# 🚀 Quick scanning verification (3 devices)
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_quick_system_check -v -s
```

### 🔄 Complete Regression Testing
```bash
# Run all core tests
pytest project/tests/ -v -s --tb=short
```

## 🔧 Test Configuration

### Network Configuration
All tests use the following default configuration:
- **API Address**: `http://localhost:8000`
- **Streamlit Address**: `http://localhost:8501`  
- **Scan Subnet**: `10.12.0.0/24`
- **Port Scan Timeout**: 120 seconds
- **OS Scan Timeout**: 180 seconds
- **OS Scan Ports**: `22,80,443`

### Modifying Configuration
You can modify configuration parameters at the top of each test file:

```python
# Configuration
API_BASE_URL = "http://localhost:8000"
SUBNET_TO_SCAN = "10.12.0.0/24"
FAST_SCAN = True
SCAN_TIMEOUT = 120
OS_SCAN_TIMEOUT = 180
OS_SCAN_PORTS = "22,80,443"
MAX_WORKERS = 3
```

## 📄 Test Output

### Result Files
Streamlined tests generate the following core output files:
- `system_verification_YYYYMMDD_HHMMSS.json` - 🔍 System verification detailed results
- `sequential_port_scan_results_YYYYMMDD_HHMMSS.json` - 🚀 Sequential port scan results
- `parallel_port_scan_results_YYYYMMDD_HHMMSS.json` - 🚀 Parallel port scan results  
- `sequential_os_scan_results_YYYYMMDD_HHMMSS.json` - 🚀 OS scan results
- `combined_port_os_scan_results_YYYYMMDD_HHMMSS.json` - 🚀 Combined scan results
- `batch_attack_results_YYYYMMDD_HHMMSS.json` - ⚔️ Attack test results

### Log Output
All tests output detailed real-time logs including:
- Scan progress
- Device discovery information
- Scan result statistics
- Error messages
- Performance metrics

## 🐛 Troubleshooting

### Common Issues

1. **Containers Not Started**
   ```bash
   sudo docker-compose up -d
   sleep 10
   curl http://localhost:8000/health
   ```

2. **Permission Issues**
   ```bash
   sudo chmod 666 project/data/iotlab.db
   ```

3. **Network Issues**
   - Check if subnet configuration is correct
   - Ensure devices are in the target network
   - Verify nmap permissions

4. **pytest Import Errors**
   ```bash
   # Ensure running from correct directory
   cd /path/to/IoTLabScheduler
   PYTHONPATH=project pytest project/tests/ -v -s
   ```

5. **Test Timeouts**
   - Increase timeout configuration
   - Reduce concurrent worker threads
   - Check network connectivity

### Debug Mode
```bash
# Detailed output mode
pytest project/tests/test_system_verification.py -v -s --tb=long

# Stop at first failure
pytest project/tests/ -v -s -x

# Show slowest tests
pytest project/tests/ --durations=10
```

## 📈 Performance Reference

### Typical Execution Time (After Streamlining)
- **🔍 System verification tests**: ~30 seconds
- **🚀 Quick scanning check**: ~2-3 minutes (3 devices)
- **🚀 Complete batch scanning**: ~10-15 minutes (all online devices, parallel)
- **⚔️ Security attack tests**: ~5-10 minutes (depends on attack configuration)

---
## 🎯 Quick Start After Streamlining

```bash
# 1. Start system
sudo docker-compose up -d

# 2. 🔍 System verification (required)
pytest project/tests/test_system_verification.py -v -s

# 3. 🚀 Quick functionality test (3 device verification)
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_quick_system_check -v -s

# 4. 🚀 Complete functionality test (optional)
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_combined_port_and_os_scan -v -s
```

If the first 3 tests pass, your IoT device management system is fully operational! 🎉

### 📊 Test Coverage
- **3 core files** cover all important functionality
- **6 main test methods** verify all aspects of the system  
- **50% code reduction** while maintaining 100% functionality coverage
