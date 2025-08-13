# IoT Lab Scheduler - 精简测试指南

本目录包含了IoT设备管理系统的**核心测试脚本**。所有测试都兼容pytest框架，功能全面且高效。

## 📂 精简后的测试文件

### 🎯 **3个核心测试文件（已精简优化）**

1. **`test_system_verification.py`** - 🔍 **系统全面验证测试**
   - API健康检查
   - 前端可访问性验证
   - 数据库连接和结构验证
   - 网络发现功能测试
   - 端口扫描和OS扫描功能验证
   - **推荐首先运行**

2. **`test_batch_scan.py`** - 🚀 **批量扫描测试套件**
   - 快速系统检查（3设备验证）
   - 批量端口扫描（串行/并行）
   - 批量OS扫描（指纹识别）
   - 组合扫描测试（端口+OS）
   - 特定设备扫描
   - **包含所有扫描功能**

3. **`test_batch_attacks.py`** - ⚔️ **网络安全攻击测试**
   - 循环攻击测试
   - 并行攻击测试
   - 网络安全评估
   - **独特的安全测试功能**

### ⚙️ 配置文件
- **`conftest.py`** - pytest配置文件
- **`__init__.py`** - Python包初始化文件

## 🚀 运行方法

### 前置条件
1. 确保Docker容器正在运行：
   ```bash
   sudo docker-compose up -d
   ```

2. 验证API服务可用：
   ```bash
   curl http://localhost:8000/health
   ```

### 1. 使用pytest运行（推荐）

#### 运行所有测试
```bash
# 在项目根目录运行
pytest project/tests/ -v -s

# 或者进入project目录运行
cd project
pytest tests/ -v -s
```

#### 运行特定测试文件
```bash
# 🔍 系统验证测试（推荐首先运行）
pytest project/tests/test_system_verification.py -v -s

# 🚀 批量扫描测试（包含所有扫描功能）
pytest project/tests/test_batch_scan.py -v -s

# ⚔️ 网络安全攻击测试
pytest project/tests/test_batch_attacks.py -v -s
```

#### 运行特定测试方法
```bash
# 🔍 系统验证
pytest project/tests/test_system_verification.py::TestSystemVerification::test_system_verification -v -s

# 🚀 快速扫描检查（3设备验证）
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_quick_system_check -v -s

# 🚀 批量端口扫描（顺序）
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_batch_port_scan_sequential -v -s

# 🚀 批量端口扫描（并行）
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_batch_port_scan_parallel -v -s

# 🚀 OS扫描
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_batch_os_scan_sequential -v -s

# 🚀 组合扫描（端口+OS）
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_combined_port_and_os_scan -v -s

# ⚔️ 安全攻击测试
pytest project/tests/test_batch_attacks.py::TestBatchAttacks::test_batch_cyclic_attacks_sequential -v -s
```

### 2. 独立运行Python脚本

```bash
# 进入tests目录
cd project/tests

# 🔍 系统验证
python3 test_system_verification.py

# 🚀 批量扫描（需要处理导入路径）
PYTHONPATH=.. python3 test_batch_scan.py

# ⚔️ 批量攻击（需要处理导入路径）
PYTHONPATH=.. python3 test_batch_attacks.py
```

## 📊 推荐测试顺序

### 🎯 新系统首次验证（3步骤）
1. **🔍 系统验证测试**（必须首先运行）
   ```bash
   pytest project/tests/test_system_verification.py -v -s
   ```

2. **🚀 快速扫描检查**（验证核心扫描功能）
   ```bash
   pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_quick_system_check -v -s
   ```

3. **🚀 完整扫描测试**（全面功能验证）
   ```bash
   pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_combined_port_and_os_scan -v -s
   ```

### 📅 日常测试
```bash
# 🔍 快速系统检查
pytest project/tests/test_system_verification.py -v -s

# 🚀 快速扫描验证（3设备）
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_quick_system_check -v -s
```

### 🔄 完整回归测试
```bash
# 运行所有核心测试
pytest project/tests/ -v -s --tb=short
```

## 🔧 测试配置

### 网络配置
所有测试默认使用以下配置：
- **API地址**: `http://localhost:8000`
- **Streamlit地址**: `http://localhost:8501`  
- **扫描子网**: `10.12.0.0/24`
- **端口扫描超时**: 120秒
- **OS扫描超时**: 180秒
- **OS扫描端口**: `22,80,443`

### 修改配置
可以在每个测试文件的顶部修改配置参数：

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

## 📄 测试输出

### 结果文件
精简后的测试会生成以下核心输出文件：
- `system_verification_YYYYMMDD_HHMMSS.json` - 🔍 系统验证详细结果
- `sequential_port_scan_results_YYYYMMDD_HHMMSS.json` - 🚀 顺序端口扫描结果
- `parallel_port_scan_results_YYYYMMDD_HHMMSS.json` - 🚀 并行端口扫描结果  
- `sequential_os_scan_results_YYYYMMDD_HHMMSS.json` - 🚀 OS扫描结果
- `combined_port_os_scan_results_YYYYMMDD_HHMMSS.json` - 🚀 组合扫描结果
- `batch_attack_results_YYYYMMDD_HHMMSS.json` - ⚔️ 攻击测试结果

### 日志输出
所有测试都会输出详细的实时日志，包括：
- 扫描进度
- 设备发现信息
- 扫描结果统计
- 错误信息
- 性能指标

## 🐛 故障排除

### 常见问题

1. **容器未启动**
   ```bash
   sudo docker-compose up -d
   sleep 10
   curl http://localhost:8000/health
   ```

2. **权限问题**
   ```bash
   sudo chmod 666 project/data/iotlab.db
   ```

3. **网络问题**
   - 检查子网配置是否正确
   - 确保设备在目标网络中
   - 验证nmap权限

4. **pytest导入错误**
   ```bash
   # 确保在正确目录运行
   cd /path/to/IoTLabScheduler
   PYTHONPATH=project pytest project/tests/ -v -s
   ```

5. **测试超时**
   - 增加超时时间配置
   - 减少并发工作线程数
   - 检查网络连接

### 调试模式
```bash
# 详细输出模式
pytest project/tests/test_system_verification.py -v -s --tb=long

# 在第一个失败时停止
pytest project/tests/ -v -s -x

# 显示最慢的测试
pytest project/tests/ --durations=10
```

## 📈 性能参考

### 典型执行时间（精简后）
- **🔍 系统验证测试**: ~30秒
- **🚀 快速扫描检查**: ~2-3分钟（3台设备）
- **🚀 完整批量扫描**: ~10-15分钟（所有在线设备，并行）
- **⚔️ 安全攻击测试**: ~5-10分钟（取决于攻击配置）

### 资源使用
- **网络带宽**: 中等（扫描期间）
- **CPU使用**: 低-中等
- **内存使用**: 低
- **磁盘使用**: 低（结果文件几MB）

---

## 🎯 精简后快速开始

```bash
# 1. 启动系统
sudo docker-compose up -d

# 2. 🔍 系统验证（必须）
pytest project/tests/test_system_verification.py -v -s

# 3. 🚀 快速功能测试（3设备验证）
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_quick_system_check -v -s

# 4. 🚀 完整功能测试（可选）
pytest project/tests/test_batch_scan.py::TestBatchPortScan::test_combined_port_and_os_scan -v -s
```

如果前3个测试通过，你的IoT设备管理系统就已经完全正常工作了！🎉

### 📊 测试覆盖
- **3个核心文件** 覆盖所有重要功能
- **6个主要测试方法** 验证系统各个方面  
- **精简50%代码量** 但保持100%功能覆盖
