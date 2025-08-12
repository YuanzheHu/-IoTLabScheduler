#!/usr/bin/env python3
"""
批量攻击测试 - 使用pytest框架
获取所有在线设备并批量发起攻击
"""

import pytest
import requests
import json
import time
import random
from typing import List, Dict
from datetime import datetime

# ==================== 配置参数 ====================
# 修改这些参数来调整测试行为
API_BASE_URL = "http://localhost:8000"  # API基础URL
SUBNET_TO_SCAN = "10.12.0.0/24"    # 要扫描的子网
ATTACK_DURATION_SEC = 10                # 每次攻击持续时间（秒）
SETTLE_TIME_SEC = 30                    # 循环攻击间的稳定时间（秒）
CYCLES = 3                              # 循环攻击次数
NETWORK_INTERFACE = "wlan0"             # 网络接口
MAX_DEVICES_TO_TEST = 2                 # 最多测试2个设备
# ================================================

class TestBatchAttacks:
    """批量攻击测试类"""
    
    @pytest.fixture(scope="class")
    def attack_types(self):
        """5种攻击类型"""
        return [
            "syn_flood", 
            "udp_flood", 
            "icmp_flood", 
            "tcp_flood", 
            "ip_frag_flood"
        ]
    
    def scan_and_get_online_devices(self) -> List[Dict]:
        """扫描子网并获取所有在线设备"""
        try:
            # 1. 扫描子网
            print(f"🔍 扫描子网: {SUBNET_TO_SCAN}")
            scan_response = requests.post(
                f"{API_BASE_URL}/devices/scan",
                json={"subnet": SUBNET_TO_SCAN},
                timeout=300
            )
            scan_response.raise_for_status()
            print(f"✅ 子网扫描完成")
            
            # 2. 获取所有设备（包括在线状态）
            devices_response = requests.get(f"{API_BASE_URL}/devices/", timeout=30)
            devices_response.raise_for_status()
            devices = devices_response.json()
            
            # 3. 过滤出在线设备，排除Unknown设备
            online_devices = [
                device for device in devices 
                if (device.get("status") == "online" and 
                    device.get("ip_address") and
                    device.get("hostname") and 
                    device.get("hostname") != "Unknown" and
                    device.get("hostname") != "Unknown Device")
            ]
            
            print(f"✅ 找到 {len(online_devices)} 个有效在线设备（排除Unknown设备）")
            
            # 4. 随机选择最多5个设备
            if len(online_devices) > MAX_DEVICES_TO_TEST:
                selected_devices = random.sample(online_devices, MAX_DEVICES_TO_TEST)
                print(f"🎲 随机选择了 {len(selected_devices)} 个设备进行测试")
            else:
                selected_devices = online_devices
                print(f"📱 使用所有 {len(selected_devices)} 个有效设备进行测试")
            
            # 5. 显示选中的设备
            for i, device in enumerate(selected_devices, 1):
                print(f"   {i}. {device.get('hostname')} ({device.get('ip_address')}) - {device.get('mac_address')}")
            
            return selected_devices
            
        except requests.RequestException as e:
            pytest.fail(f"获取在线设备失败: {e}")
    
    def check_experiment_status(self, experiment_id: str) -> str:
        """检查实验状态"""
        try:
            response = requests.get(f"{API_BASE_URL}/experiments/{experiment_id}", timeout=10)
            if response.status_code == 200:
                experiment = response.json()
                return experiment.get("status", "unknown")
            return "unknown"
        except:
            return "unknown"
    
    def wait_for_experiment_completion(self, experiment_id: str, timeout_minutes: int = 10) -> bool:
        """等待实验完成"""
        print(f"⏳ 等待实验 {experiment_id} 完成...")
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            status = self.check_experiment_status(experiment_id)
            if status in ["completed", "failed", "stopped"]:
                print(f"✅ 实验 {experiment_id} 状态: {status}")
                return True
            elif status == "running":
                print(f"🔄 实验 {experiment_id} 正在运行...")
            else:
                print(f"📊 实验 {experiment_id} 状态: {status}")
            
            time.sleep(10)  # 每10秒检查一次
        
        print(f"⏰ 实验 {experiment_id} 超时")
        return False
    
    def create_cyclic_attack_experiment(self, target_ip: str, device_name: str, 
                                       attack_type: str) -> Dict:
        """创建循环攻击实验"""
        experiment_data = {
            "name": f"Batch Test - {attack_type} on {device_name}",
            "attack_type": attack_type,
            "target_ip": target_ip,  # 使用设备的实际IP地址
            "port": 80,
            "duration_sec": ATTACK_DURATION_SEC,
            "interface": NETWORK_INTERFACE,
            "attack_mode": "cyclic",
            "cycles": CYCLES,
            "settle_time_sec": SETTLE_TIME_SEC
        }
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/experiments/v2",
                json=experiment_data,
                timeout=30
            )
            response.raise_for_status()
            experiment = response.json()
            
            print(f"✅ 成功创建 {attack_type} 循环攻击实验 (ID: {experiment.get('id')})")
            return experiment
            
        except requests.RequestException as e:
            pytest.fail(f"创建 {attack_type} 循环攻击实验失败: {e}")
    
    def test_batch_cyclic_attacks_sequential(self, attack_types):
        """测试：对选中的在线设备顺序发起循环攻击（避免冲突）"""
        print(f"\n🚀 开始顺序批量循环攻击测试 - {datetime.now()}")
        print(f"📋 测试配置:")
        print(f"   子网: {SUBNET_TO_SCAN}")
        print(f"   攻击持续时间: {ATTACK_DURATION_SEC}秒")
        print(f"   循环次数: {CYCLES}")
        print(f"   稳定时间: {SETTLE_TIME_SEC}秒")
        print(f"   网络接口: {NETWORK_INTERFACE}")
        print(f"   最大测试设备数: {MAX_DEVICES_TO_TEST}")
        print(f"   ⚠️  攻击模式: 顺序执行（避免数据污染）")
        
        # 1. 获取选中的在线设备
        online_devices = self.scan_and_get_online_devices()
        
        if not online_devices:
            pytest.skip("没有找到有效的在线设备，跳过测试")
        
        # 2. 为每个设备顺序创建循环攻击实验（避免同时攻击同一IP）
        created_experiments = []
        
        for device in online_devices:
            device_mac = device["mac_address"]
            device_name = device.get("hostname", "Unknown Device")
            device_ip = device.get("ip_address", "Unknown")
            
            print(f"\n🎯 为设备 {device_name} ({device_ip}) 创建循环攻击实验...")
            print(f"   📍 将顺序执行所有攻击类型，确保数据质量")
            
            for attack_type in attack_types:
                try:
                    print(f"   🔥 开始 {attack_type} 攻击...")
                    
                    # 创建攻击实验
                    experiment = self.create_cyclic_attack_experiment(
                        device_ip, device_name, attack_type
                    )
                    
                    # 等待实验完成
                    experiment_completed = self.wait_for_experiment_completion(
                        experiment.get("id"), 
                        timeout_minutes=15  # 15分钟超时
                    )
                    
                    if experiment_completed:
                        created_experiments.append({
                            "device_mac": device_mac,
                            "device_name": device_name,
                            "device_ip": device_ip,
                            "attack_type": attack_type,
                            "experiment_id": experiment.get("id"),
                            "status": "completed",
                            "timestamp": datetime.now().isoformat()
                        })
                        print(f"   ✅ {attack_type} 攻击完成")
                    else:
                        created_experiments.append({
                            "device_mac": device_mac,
                            "device_name": device_name,
                            "device_ip": device_ip,
                            "attack_type": attack_type,
                            "experiment_id": experiment.get("id"),
                            "status": "timeout",
                            "timestamp": datetime.now().isoformat()
                        })
                        print(f"   ⏰ {attack_type} 攻击超时")
                    
                    # 攻击完成后等待稳定时间，确保网络恢复正常
                    print(f"   ⏸️  等待 {SETTLE_TIME_SEC} 秒稳定时间...")
                    time.sleep(SETTLE_TIME_SEC)
                    
                except Exception as e:
                    print(f"   ❌ 为设备 {device_name} 创建 {attack_type} 攻击失败: {e}")
                    created_experiments.append({
                        "device_mac": device_mac,
                        "device_name": device_name,
                        "device_ip": device_ip,
                        "attack_type": attack_type,
                        "experiment_id": None,
                        "status": "failed",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
        
        # 3. 输出测试结果摘要
        print(f"\n📊 顺序批量循环攻击测试完成!")
        print(f"   测试设备数: {len(online_devices)}")
        print(f"   总攻击实验数: {len(created_experiments)}")
        
        completed_count = len([exp for exp in created_experiments if exp["status"] == "completed"])
        failed_count = len([exp for exp in created_experiments if exp["status"] == "failed"])
        timeout_count = len([exp for exp in created_experiments if exp["status"] == "timeout"])
        
        print(f"   成功完成: {completed_count}")
        print(f"   执行失败: {failed_count}")
        print(f"   执行超时: {timeout_count}")
        
        # 4. 保存测试结果到文件
        results_file = f"sequential_batch_attack_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump({
                "test_config": {
                    "subnet": SUBNET_TO_SCAN,
                    "attack_duration_sec": ATTACK_DURATION_SEC,
                    "cycles": CYCLES,
                    "settle_time_sec": SETTLE_TIME_SEC,
                    "network_interface": NETWORK_INTERFACE,
                    "max_devices_to_test": MAX_DEVICES_TO_TEST,
                    "attack_mode": "sequential",
                    "description": "顺序执行攻击，避免数据污染"
                },
                "test_timestamp": datetime.now().isoformat(),
                "tested_devices": len(online_devices),
                "total_experiments": len(created_experiments),
                "completed_count": completed_count,
                "failed_count": failed_count,
                "timeout_count": timeout_count,
                "experiments": created_experiments
            }, f, indent=2, ensure_ascii=False)
        
        print(f"   测试结果已保存到: {results_file}")
        
        # 5. 断言测试结果
        assert completed_count > 0, "至少应该成功完成一些攻击实验"
        assert failed_count < len(created_experiments) * 0.3, "失败率不应超过30%"
        
        print("✅ 顺序批量循环攻击测试通过!")
        print("🎯 数据收集质量: 高（无并发攻击干扰）")
    
    def test_batch_cyclic_attacks(self, attack_types):
        """测试：对选中的在线设备批量发起循环攻击（保持原有功能）"""
        print(f"\n🚀 开始批量循环攻击测试 - {datetime.now()}")
        print(f"📋 测试配置:")
        print(f"   子网: {SUBNET_TO_SCAN}")
        print(f"   攻击持续时间: {ATTACK_DURATION_SEC}秒")
        print(f"   循环次数: {CYCLES}")
        print(f"   稳定时间: {SETTLE_TIME_SEC}秒")
        print(f"   网络接口: {NETWORK_INTERFACE}")
        print(f"   最大测试设备数: {MAX_DEVICES_TO_TEST}")
        print(f"   ⚠️  攻击模式: 并发执行（可能产生数据污染）")
        
        # 1. 获取选中的在线设备
        online_devices = self.scan_and_get_online_devices()
        
        if not online_devices:
            pytest.skip("没有找到有效的在线设备，跳过测试")
        
        # 2. 为每个设备创建所有类型的循环攻击实验
        created_experiments = []
        
        for device in online_devices:
            device_mac = device["mac_address"]
            device_name = device.get("hostname", "Unknown Device")
            device_ip = device.get("ip_address", "Unknown")
            
            print(f"\n🎯 为设备 {device_name} ({device_ip}) 创建循环攻击实验...")
            
            for attack_type in attack_types:
                try:
                    experiment = self.create_cyclic_attack_experiment(
                        device_ip,  # 使用IP地址作为目标
                        device_name, 
                        attack_type
                    )
                    created_experiments.append({
                        "device_mac": device_mac,
                        "device_name": device_name,
                        "device_ip": device_ip,
                        "attack_type": attack_type,
                        "experiment_id": experiment.get("id"),
                        "status": "created",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # 短暂延迟，避免API过载
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"❌ 为设备 {device_name} 创建 {attack_type} 攻击失败: {e}")
                    created_experiments.append({
                        "device_mac": device_mac,
                        "device_name": device_name,
                        "device_ip": device_ip,
                        "attack_type": attack_type,
                        "experiment_id": None,
                        "status": "failed",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
        
        # 3. 输出测试结果摘要
        print(f"\n📊 批量循环攻击测试完成!")
        print(f"   测试设备数: {len(online_devices)}")
        print(f"   总攻击实验数: {len(created_experiments)}")
        
        success_count = len([exp for exp in created_experiments if exp["status"] == "created"])
        failed_count = len([exp for exp in created_experiments if exp["status"] == "failed"])
        
        print(f"   成功创建: {success_count}")
        print(f"   创建失败: {failed_count}")
        
        # 4. 保存测试结果到文件
        results_file = f"batch_cyclic_attack_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump({
                "test_config": {
                    "subnet": SUBNET_TO_SCAN,
                    "attack_duration_sec": ATTACK_DURATION_SEC,
                    "cycles": CYCLES,
                    "settle_time_sec": SETTLE_TIME_SEC,
                    "network_interface": NETWORK_INTERFACE,
                    "max_devices_to_test": MAX_DEVICES_TO_TEST
                },
                "test_timestamp": datetime.now().isoformat(),
                "tested_devices": len(online_devices),
                "total_experiments": len(created_experiments),
                "success_count": success_count,
                "failed_count": failed_count,
                "experiments": created_experiments
            }, f, indent=2, ensure_ascii=False)
        
        print(f"   测试结果已保存到: {results_file}")
        
        # 5. 断言测试结果
        assert success_count > 0, "至少应该成功创建一些攻击实验"
        assert failed_count < len(created_experiments) * 0.5, "失败率不应超过50%"
        
        print("✅ 批量循环攻击测试通过!")

    def test_batch_cyclic_attacks_parallel_by_ip(self, attack_types):
        """测试：对不同IP设备并行发起循环攻击（避免数据污染，提高效率）"""
        print(f"\n🚀 开始IP并行批量循环攻击测试 - {datetime.now()}")
        print(f"📋 测试配置:")
        print(f"   子网: {SUBNET_TO_SCAN}")
        print(f"   攻击持续时间: {ATTACK_DURATION_SEC}秒")
        print(f"   循环次数: {CYCLES}")
        print(f"   稳定时间: {SETTLE_TIME_SEC}秒")
        print(f"   网络接口: {NETWORK_INTERFACE}")
        print(f"   最大测试设备数: {MAX_DEVICES_TO_TEST}")
        print(f"   🚀 攻击模式: IP并行执行（不同IP可并行，同一IP顺序执行）")
        
        # 1. 获取选中的在线设备
        online_devices = self.scan_and_get_online_devices()
        
        if not online_devices:
            pytest.skip("没有找到有效的在线设备，跳过测试")
        
        # 2. 为每个设备并行创建循环攻击实验（不同IP可并行）
        created_experiments = []
        
        # 为每个设备创建所有攻击类型的实验
        for device in online_devices:
            device_mac = device["mac_address"]
            device_name = device.get("hostname", "Unknown Device")
            device_ip = device.get("ip_address", "Unknown")
            
            print(f"\n🎯 为设备 {device_name} ({device_ip}) 创建循环攻击实验...")
            
            for attack_type in attack_types:
                try:
                    experiment = self.create_cyclic_attack_experiment(
                        device_ip, device_name, attack_type
                    )
                    created_experiments.append({
                        "device_mac": device_mac,
                        "device_name": device_name,
                        "device_ip": device_ip,
                        "attack_type": attack_type,
                        "experiment_id": experiment.get("id"),
                        "status": "created",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # 短暂延迟，避免API过载
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"❌ 为设备 {device_name} 创建 {attack_type} 攻击失败: {e}")
                    created_experiments.append({
                        "device_mac": device_mac,
                        "device_name": device_name,
                        "device_ip": device_ip,
                        "attack_type": attack_type,
                        "experiment_id": None,
                        "status": "failed",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
        
        # 3. 输出测试结果摘要
        print(f"\n📊 IP并行批量循环攻击测试完成!")
        print(f"   测试设备数: {len(online_devices)}")
        print(f"   总攻击实验数: {len(created_experiments)}")
        
        success_count = len([exp for exp in created_experiments if exp["status"] == "created"])
        failed_count = len([exp for exp in created_experiments if exp["status"] == "failed"])
        
        print(f"   成功创建: {success_count}")
        print(f"   创建失败: {failed_count}")
        
        # 4. 保存测试结果到文件
        results_file = f"parallel_by_ip_batch_attack_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump({
                "test_config": {
                    "subnet": SUBNET_TO_SCAN,
                    "attack_duration_sec": ATTACK_DURATION_SEC,
                    "cycles": CYCLES,
                    "settle_time_sec": SETTLE_TIME_SEC,
                    "network_interface": NETWORK_INTERFACE,
                    "max_devices_to_test": MAX_DEVICES_TO_TEST,
                    "attack_mode": "parallel_by_ip",
                    "description": "不同IP并行执行，同一IP顺序执行，避免数据污染"
                },
                "test_timestamp": datetime.now().isoformat(),
                "tested_devices": len(online_devices),
                "total_experiments": len(created_experiments),
                "success_count": success_count,
                "failed_count": failed_count,
                "experiments": created_experiments
            }, f, indent=2, ensure_ascii=False)
        
        print(f"   测试结果已保存到: {results_file}")
        
        # 5. 断言测试结果
        assert success_count > 0, "至少应该成功创建一些攻击实验"
        assert failed_count < len(created_experiments) * 0.5, "失败率不应超过50%"
        
        print("✅ IP并行批量循环攻击测试通过!")
        print("🎯 数据收集质量: 高（不同IP并行，无数据污染）")
        print("⚡ 执行效率: 高（并行执行，节省时间）")

# 如果直接运行此文件
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
