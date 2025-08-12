#!/usr/bin/env python3
"""
数据库初始化脚本
用于重新创建数据库表结构，确保IP地址的唯一性约束
"""

from project.db.base import engine, Base, SessionLocal
from project.db.models import Device, Experiment, Capture, ScanResult, PortInfo
from sqlalchemy import MetaData
import os

def init_database():
    """初始化数据库"""
    print("正在删除现有数据库表...")
    Base.metadata.drop_all(bind=engine)
    
    print("正在创建新的数据库表...")
    Base.metadata.create_all(bind=engine)
    
    print("数据库初始化完成！")
    print("已添加以下唯一性约束：")
    print("- Device.ip_address: 唯一且不可为空")
    print("- Device.mac_address: 唯一且不可为空")
    print("- ScanResult.target_ip: 唯一且不可为空")

def test_database():
    """测试数据库功能"""
    print("\n正在测试数据库功能...")
    db = SessionLocal()
    try:
        # 插入测试设备
        device = Device(
            ip_address='10.12.0.100',
            mac_address='00:11:22:33:44:55',
            hostname='test-device',
            os_info='Linux',
            status='online'
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        print(f"✓ 插入设备成功: {device.id}, {device.ip_address}")

        # 插入扫描结果
        scan_result = ScanResult(
            device_id=device.id,
            scan_type='port_scan',
            target_ip='10.12.0.100',
            scan_duration=30,
            status='success'
        )
        db.add(scan_result)
        db.commit()
        print(f"✓ 插入扫描结果成功: {scan_result.id}, {scan_result.target_ip}")

        # 查询所有设备
        devices = db.query(Device).all()
        print(f"✓ 查询设备成功: {[d.ip_address for d in devices]}")

        # 查询所有扫描结果
        scan_results = db.query(ScanResult).all()
        print(f"✓ 查询扫描结果成功: {[s.target_ip for s in scan_results]}")

        # 清理测试数据
        db.delete(scan_result)
        db.delete(device)
        db.commit()
        print("✓ 清理测试数据成功")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    # 检查数据库文件是否存在
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'iotlab.db')
    if os.path.exists(db_path):
        print(f"发现现有数据库文件: {db_path}")
        response = input("是否要重新初始化数据库？这将删除所有现有数据 (y/N): ")
        if response.lower() != 'y':
            print("取消操作")
            exit()
    
    init_database()
    test_database()