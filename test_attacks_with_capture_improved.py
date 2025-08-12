#!/usr/bin/env python3
"""
改进的攻击测试文件（带流量抓取）

本文件测试各种类型的攻击，同时记录流量数据。
解决了抓包时间短的问题。
"""

import asyncio
import sys
import os
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from project.core.attack_engine_v2 import (
    CyclicAttackEngine, 
    AttackConfig, 
    AttackType, 
    AttackMode
)
from project.core.traffic_capture import TcpdumpUtil

# 目标IP
TARGET_IP = '10.12.0.188'

# 创建数据目录
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# 统一的攻击参数
ATTACK_CYCLES = 3
ATTACK_DURATION = 10
ATTACK_SETTLE = 10

async def test_syn_flood_with_capture():
    """测试SYN Flood攻击（带流量抓取）"""
    print("="*50)
    print("测试SYN Flood攻击（带流量抓取）")
    print("="*50)
    
    engine = CyclicAttackEngine()
    
    # 创建攻击配置
    config = AttackConfig(
        attack_type=AttackType.SYN_FLOOD,
        target_ip=TARGET_IP,
        interface='wlan0',        # 使用wlan0接口
        port=80,                  # HTTP端口
        duration_sec=ATTACK_DURATION,      # 每轮攻击10秒
        settle_time_sec=ATTACK_SETTLE,     # 间隔10秒
        cycles=ATTACK_CYCLES,              # 循环3次
        mode=AttackMode.CYCLIC
    )
    
    # 创建流量捕获
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    capture_file = DATA_DIR / f"syn_flood_capture_{timestamp}.pcap"
    tcpdump = TcpdumpUtil(
        output_file=str(capture_file),
        interface='wlan0',        # 使用wlan0接口抓包
        target_ip=TARGET_IP
    )
    
    try:
        print(f"目标: {config.target_ip}:{config.port}")
        print(f"攻击接口: {config.interface}")
        print(f"抓包接口: wlan0")
        print(f"循环次数: {config.cycles}")
        print(f"每轮时长: {config.duration_sec}秒")
        print(f"间隔时间: {config.settle_time_sec}秒")
        print(f"流量捕获文件: {capture_file}")
        
        # 开始流量捕获
        print("开始流量捕获...")
        tcpdump.start()
        
        # 等待并检查tcpdump进程状态
        await asyncio.sleep(2)
        if tcpdump.process and tcpdump.process.poll() is not None:
            stderr_output = tcpdump.process.stderr.read().decode() if tcpdump.process.stderr else "无错误输出"
            raise RuntimeError(f"tcpdump进程异常退出: {stderr_output}")
        
        print(f"tcpdump进程正常运行 (PID: {tcpdump.process.pid})")
        
        # 开始循环攻击
        print("开始循环攻击...")
        success = await engine.start_cyclic_attack(config)
        
        if success:
            print("循环攻击完成!")
            
            # 显示结果
            results = engine.get_attack_results()
            print(f"\n攻击结果:")
            for result in results:
                status = "成功" if result.success else "失败"
                print(f"  第{result.cycle}轮: {status} (耗时: {result.duration_sec:.1f}秒)")
            
            # 显示统计信息
            status = engine.get_attack_status()
            print(f"\n统计信息:")
            print(f"  总轮数: {status['total_cycles']}")
            print(f"  成功轮数: {status['successful_cycles']}")
            print(f"  失败轮数: {status['failed_cycles']}")
        else:
            print("循环攻击失败!")
        
    except Exception as e:
        print(f"测试失败: {e}")
        if engine.is_attack_running():
            await engine.stop_attack()
    finally:
        # 等待一下确保所有流量都被捕获
        print("等待5秒确保所有流量都被捕获...")
        await asyncio.sleep(5)
        
        # 停止流量捕获
        print("停止流量捕获...")
        tcpdump.stop()
        
        # 检查捕获文件
        if capture_file.exists():
            file_size = capture_file.stat().st_size
            print(f"测试完成! 流量捕获文件: {capture_file} ({file_size} bytes)")
        else:
            print("警告: 流量捕获文件未创建")


async def test_udp_flood_with_capture():
    """测试UDP Flood攻击（带流量抓取）"""
    print("\n" + "="*50)
    print("测试UDP Flood攻击（带流量抓取）")
    print("="*50)
    
    engine = CyclicAttackEngine()
    
    # 创建攻击配置
    config = AttackConfig(
        attack_type=AttackType.UDP_FLOOD,
        target_ip=TARGET_IP,
        interface='wlan0',        # 使用wlan0接口
        port=53,                  # DNS端口
        duration_sec=ATTACK_DURATION,      # 每轮攻击10秒
        settle_time_sec=ATTACK_SETTLE,     # 间隔10秒
        cycles=ATTACK_CYCLES,              # 循环3次
        mode=AttackMode.CYCLIC
    )
    
    # 创建流量捕获
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    capture_file = DATA_DIR / f"udp_flood_capture_{timestamp}.pcap"
    tcpdump = TcpdumpUtil(
        output_file=str(capture_file),
        interface='wlan0',        # 使用wlan0接口抓包
        target_ip=TARGET_IP
    )
    
    try:
        print(f"目标: {config.target_ip}:{config.port} (DNS)")
        print(f"攻击接口: {config.interface}")
        print(f"抓包接口: wlan0")
        print(f"循环次数: {config.cycles}")
        print(f"每轮时长: {config.duration_sec}秒")
        print(f"间隔时间: {config.settle_time_sec}秒")
        print(f"流量捕获文件: {capture_file}")
        
        # 开始流量捕获
        print("开始流量捕获...")
        tcpdump.start()
        
        # 等待并检查tcpdump进程状态
        await asyncio.sleep(2)
        if tcpdump.process and tcpdump.process.poll() is not None:
            stderr_output = tcpdump.process.stderr.read().decode() if tcpdump.process.stderr else "无错误输出"
            raise RuntimeError(f"tcpdump进程异常退出: {stderr_output}")
        
        print(f"tcpdump进程正常运行 (PID: {tcpdump.process.pid})")
        
        # 开始循环攻击
        print("开始循环攻击...")
        success = await engine.start_cyclic_attack(config)
        
        if success:
            print("循环攻击完成!")
            
            # 显示结果
            results = engine.get_attack_results()
            print(f"\n攻击结果:")
            for result in results:
                status = "成功" if result.success else "失败"
                print(f"  第{result.cycle}轮: {status} (耗时: {result.duration_sec:.1f}秒)")
            
            # 显示统计信息
            status = engine.get_attack_status()
            print(f"\n统计信息:")
            print(f"  总轮数: {status['total_cycles']}")
            print(f"  成功轮数: {status['successful_cycles']}")
            print(f"  失败轮数: {status['failed_cycles']}")
        else:
            print("循环攻击失败!")
        
    except Exception as e:
        print(f"测试失败: {e}")
        if engine.is_attack_running():
            await engine.stop_attack()
    finally:
        # 等待一下确保所有流量都被捕获
        print("等待5秒确保所有流量都被捕获...")
        await asyncio.sleep(5)
        
        # 停止流量捕获
        print("停止流量捕获...")
        tcpdump.stop()
        
        # 检查捕获文件
        if capture_file.exists():
            file_size = capture_file.stat().st_size
            print(f"测试完成! 流量捕获文件: {capture_file} ({file_size} bytes)")
        else:
            print("警告: 流量捕获文件未创建")


async def test_icmp_flood_with_capture():
    """测试ICMP Flood攻击（带流量抓取）"""
    print("\n" + "="*50)
    print("测试ICMP Flood攻击（带流量抓取）")
    print("="*50)
    
    engine = CyclicAttackEngine()
    
    # 创建攻击配置
    config = AttackConfig(
        attack_type=AttackType.ICMP_FLOOD,
        target_ip=TARGET_IP,
        interface='wlan0',        # 使用wlan0接口
        port=0,                   # ICMP不需要端口
        duration_sec=ATTACK_DURATION,      # 每轮攻击10秒
        settle_time_sec=ATTACK_SETTLE,     # 间隔10秒
        cycles=ATTACK_CYCLES,              # 循环3次
        mode=AttackMode.CYCLIC
    )
    
    # 创建流量捕获
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    capture_file = DATA_DIR / f"icmp_flood_capture_{timestamp}.pcap"
    tcpdump = TcpdumpUtil(
        output_file=str(capture_file),
        interface='wlan0',        # 使用wlan0接口抓包
        target_ip=TARGET_IP
    )
    
    try:
        print(f"目标: {config.target_ip} (ICMP Echo)")
        print(f"攻击接口: {config.interface}")
        print(f"抓包接口: wlan0")
        print(f"循环次数: {config.cycles}")
        print(f"每轮时长: {config.duration_sec}秒")
        print(f"间隔时间: {config.settle_time_sec}秒")
        print(f"流量捕获文件: {capture_file}")
        
        # 开始流量捕获
        print("开始流量捕获...")
        tcpdump.start()
        
        # 等待并检查tcpdump进程状态
        await asyncio.sleep(2)
        if tcpdump.process and tcpdump.process.poll() is not None:
            stderr_output = tcpdump.process.stderr.read().decode() if tcpdump.process.stderr else "无错误输出"
            raise RuntimeError(f"tcpdump进程异常退出: {stderr_output}")
        
        print(f"tcpdump进程正常运行 (PID: {tcpdump.process.pid})")
        
        # 开始循环攻击
        print("开始循环攻击...")
        success = await engine.start_cyclic_attack(config)
        
        if success:
            print("循环攻击完成!")
            
            # 显示结果
            results = engine.get_attack_results()
            print(f"\n攻击结果:")
            for result in results:
                status = "成功" if result.success else "失败"
                print(f"  第{result.cycle}轮: {status} (耗时: {result.duration_sec:.1f}秒)")
            
            # 显示统计信息
            status = engine.get_attack_status()
            print(f"\n统计信息:")
            print(f"  总轮数: {status['total_cycles']}")
            print(f"  成功轮数: {status['successful_cycles']}")
            print(f"  失败轮数: {status['failed_cycles']}")
        else:
            print("循环攻击失败!")
        
    except Exception as e:
        print(f"测试失败: {e}")
        if engine.is_attack_running():
            await engine.stop_attack()
    finally:
        # 等待一下确保所有流量都被捕获
        print("等待5秒确保所有流量都被捕获...")
        await asyncio.sleep(5)
        
        # 停止流量捕获
        print("停止流量捕获...")
        tcpdump.stop()
        
        # 检查捕获文件
        if capture_file.exists():
            file_size = capture_file.stat().st_size
            print(f"测试完成! 流量捕获文件: {capture_file} ({file_size} bytes)")
        else:
            print("警告: 流量捕获文件未创建")


async def test_tcp_flood_with_capture():
    """测试TCP Flood攻击（带流量抓取）"""
    print("\n" + "="*50)
    print("测试TCP Flood攻击（带流量抓取）")
    print("="*50)
    
    engine = CyclicAttackEngine()
    
    # 创建攻击配置
    config = AttackConfig(
        attack_type=AttackType.TCP_FLOOD,
        target_ip=TARGET_IP,
        interface='wlan0',        # 使用wlan0接口
        port=22,                  # SSH端口
        duration_sec=ATTACK_DURATION,      # 每轮攻击10秒
        settle_time_sec=ATTACK_SETTLE,     # 间隔10秒
        cycles=ATTACK_CYCLES,              # 循环3次
        mode=AttackMode.CYCLIC
    )
    
    # 创建流量捕获
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    capture_file = DATA_DIR / f"tcp_flood_capture_{timestamp}.pcap"
    tcpdump = TcpdumpUtil(
        output_file=str(capture_file),
        interface='wlan0',        # 使用wlan0接口抓包
        target_ip=TARGET_IP
    )
    
    try:
        print(f"目标: {config.target_ip}:{config.port} (SSH)")
        print(f"攻击接口: {config.interface}")
        print(f"抓包接口: wlan0")
        print(f"循环次数: {config.cycles}")
        print(f"每轮时长: {config.duration_sec}秒")
        print(f"间隔时间: {config.settle_time_sec}秒")
        print(f"流量捕获文件: {capture_file}")
        
        # 开始流量捕获
        print("开始流量捕获...")
        tcpdump.start()
        
        # 等待并检查tcpdump进程状态
        await asyncio.sleep(2)
        if tcpdump.process and tcpdump.process.poll() is not None:
            stderr_output = tcpdump.process.stderr.read().decode() if tcpdump.process.stderr else "无错误输出"
            raise RuntimeError(f"tcpdump进程异常退出: {stderr_output}")
        
        print(f"tcpdump进程正常运行 (PID: {tcpdump.process.pid})")
        
        # 开始循环攻击
        print("开始循环攻击...")
        success = await engine.start_cyclic_attack(config)
        
        if success:
            print("循环攻击完成!")
            
            # 显示结果
            results = engine.get_attack_results()
            print(f"\n攻击结果:")
            for result in results:
                status = "成功" if result.success else "失败"
                print(f"  第{result.cycle}轮: {status} (耗时: {result.duration_sec:.1f}秒)")
            
            # 显示统计信息
            status = engine.get_attack_status()
            print(f"\n统计信息:")
            print(f"  总轮数: {status['total_cycles']}")
            print(f"  成功轮数: {status['successful_cycles']}")
            print(f"  失败轮数: {status['failed_cycles']}")
        else:
            print("循环攻击失败!")
        
    except Exception as e:
        print(f"测试失败: {e}")
        if engine.is_attack_running():
            await engine.stop_attack()
    finally:
        # 等待一下确保所有流量都被捕获
        print("等待5秒确保所有流量都被捕获...")
        await asyncio.sleep(5)
        
        # 停止流量捕获
        print("停止流量捕获...")
        tcpdump.stop()
        
        # 检查捕获文件
        if capture_file.exists():
            file_size = capture_file.stat().st_size
            print(f"测试完成! 流量捕获文件: {capture_file} ({file_size} bytes)")
        else:
            print("警告: 流量捕获文件未创建")


async def test_ip_frag_flood_with_capture():
    """测试IP Fragment Flood攻击（带流量抓取）"""
    print("\n" + "="*50)
    print("测试IP Fragment Flood攻击（带流量抓取）")
    print("="*50)
    
    engine = CyclicAttackEngine()
    
    # 创建攻击配置
    config = AttackConfig(
        attack_type=AttackType.IP_FRAG_FLOOD,
        target_ip=TARGET_IP,
        interface='wlan0',        # 使用wlan0接口
        port=80,                  # HTTP端口
        duration_sec=ATTACK_DURATION,      # 每轮攻击10秒
        settle_time_sec=ATTACK_SETTLE,     # 间隔10秒
        cycles=ATTACK_CYCLES,              # 循环3次
        mode=AttackMode.CYCLIC
    )
    
    # 创建流量捕获
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    capture_file = DATA_DIR / f"ip_frag_flood_capture_{timestamp}.pcap"
    tcpdump = TcpdumpUtil(
        output_file=str(capture_file),
        interface='wlan0',        # 使用wlan0接口抓包
        target_ip=TARGET_IP
    )
    
    try:
        print(f"目标: {config.target_ip}:{config.port} (HTTP)")
        print(f"攻击接口: {config.interface}")
        print(f"抓包接口: wlan0")
        print(f"循环次数: {config.cycles}")
        print(f"每轮时长: {config.duration_sec}秒")
        print(f"间隔时间: {config.settle_time_sec}秒")
        print(f"流量捕获文件: {capture_file}")
        
        # 开始流量捕获
        print("开始流量捕获...")
        tcpdump.start()
        
        # 等待并检查tcpdump进程状态
        await asyncio.sleep(2)
        if tcpdump.process and tcpdump.process.poll() is not None:
            stderr_output = tcpdump.process.stderr.read().decode() if tcpdump.process.stderr else "无错误输出"
            raise RuntimeError(f"tcpdump进程异常退出: {stderr_output}")
        
        print(f"tcpdump进程正常运行 (PID: {tcpdump.process.pid})")
        
        # 开始循环攻击
        print("开始循环攻击...")
        success = await engine.start_cyclic_attack(config)
        
        if success:
            print("循环攻击完成!")
            
            # 显示结果
            results = engine.get_attack_results()
            print(f"\n攻击结果:")
            for result in results:
                status = "成功" if result.success else "失败"
                print(f"  第{result.cycle}轮: {status} (耗时: {result.duration_sec:.1f}秒)")
            
            # 显示统计信息
            status = engine.get_attack_status()
            print(f"\n统计信息:")
            print(f"  总轮数: {status['total_cycles']}")
            print(f"  成功轮数: {status['successful_cycles']}")
            print(f"  失败轮数: {status['failed_cycles']}")
        else:
            print("循环攻击失败!")
        
    except Exception as e:
        print(f"测试失败: {e}")
        if engine.is_attack_running():
            await engine.stop_attack()
    finally:
        # 等待一下确保所有流量都被捕获
        print("等待5秒确保所有流量都被捕获...")
        await asyncio.sleep(5)
        
        # 停止流量捕获
        print("停止流量捕获...")
        tcpdump.stop()
        
        # 检查捕获文件
        if capture_file.exists():
            file_size = capture_file.stat().st_size
            print(f"测试完成! 流量捕获文件: {capture_file} ({file_size} bytes)")
        else:
            print("警告: 流量捕获文件未创建")


def list_capture_files():
    """列出所有流量捕获文件"""
    if DATA_DIR.exists():
        files = list(DATA_DIR.glob("*.pcap"))
        if files:
            print(f"\n流量捕获文件列表 ({len(files)} 个文件):")
            for file in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
                size = file.stat().st_size
                mtime = datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                print(f"  {file.name} ({size} bytes, {mtime})")
        else:
            print("\n暂无流量捕获文件")
    else:
        print("\n数据目录不存在")


async def main():
    """主函数"""
    print("改进的攻击测试（带流量抓取）")
    print("="*60)
    print(f"本程序测试5种不同类型的攻击，每种均为循环{ATTACK_CYCLES}次")
    print(f"每轮攻击{ATTACK_DURATION}秒，间隔{ATTACK_SETTLE}秒")
    print("每种攻击都会记录流量数据到 data/ 目录")
    print("解决了抓包时间短的问题")
    print("="*60)
    
    # 测试列表
    tests = [
        (test_syn_flood_with_capture, "SYN Flood攻击"),
        (test_udp_flood_with_capture, "UDP Flood攻击"),
        (test_icmp_flood_with_capture, "ICMP Flood攻击"),
        (test_tcp_flood_with_capture, "TCP Flood攻击"),
        (test_ip_frag_flood_with_capture, "IP Fragment Flood攻击")
    ]
    
    print("\n可用的测试类型:")
    for i, (_, name) in enumerate(tests, 1):
        print(f"  {i}. {name}")
    
    # 让用户选择要运行的测试
    print("\n请选择要运行的测试 (输入数字，或输入 'all' 运行所有测试，或输入 'list' 查看流量文件):")
    choice = input("选择: ").strip()
    
    if choice.lower() == 'list':
        list_capture_files()
    elif choice.lower() == 'all':
        # 运行所有测试
        for test_func, test_name in tests:
            print(f"\n开始运行: {test_name}")
            await test_func()
            await asyncio.sleep(2)  # 测试之间稍作休息
        # 显示所有捕获文件
        list_capture_files()
    else:
        try:
            index = int(choice) - 1
            if 0 <= index < len(tests):
                test_func, test_name = tests[index]
                await test_func()
                # 显示捕获文件
                list_capture_files()
            else:
                print("无效的选择")
        except ValueError:
            print("请输入有效的数字、'all' 或 'list'")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n程序执行错误: {e}") 