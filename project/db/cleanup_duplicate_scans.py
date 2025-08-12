#!/usr/bin/env python3
"""
清理重复扫描结果脚本
确保每个设备每种扫描类型只有一个最新的扫描结果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.base import engine, SessionLocal
from db.models import ScanResult, Device
from sqlalchemy import text
import datetime

def cleanup_duplicate_scan_results():
    """清理重复的扫描结果"""
    db = SessionLocal()
    try:
        print("🔍 开始清理重复的扫描结果...")
        
        # 1. 统计清理前的数据
        total_before = db.query(ScanResult).count()
        print(f"   清理前总扫描结果数: {total_before}")
        
        # 2. 查找重复记录
        duplicates_query = text("""
            WITH ranked_results AS (
                SELECT 
                    id,
                    device_id,
                    scan_type,
                    target_ip,
                    scan_time,
                    ROW_NUMBER() OVER (
                        PARTITION BY device_id, scan_type 
                        ORDER BY scan_time DESC
                    ) as rn
                FROM scan_results
            )
            SELECT 
                device_id,
                scan_type,
                COUNT(*) as total_count,
                COUNT(CASE WHEN rn > 1 THEN 1 END) as duplicate_count
            FROM ranked_results 
            GROUP BY device_id, scan_type
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC
        """)
        
        duplicates = db.execute(duplicates_query).fetchall()
        
        if not duplicates:
            print("✅ 没有发现重复的扫描结果")
            return
        
        print(f"   发现 {len(duplicates)} 个设备有重复扫描结果:")
        for dup in duplicates:
            device_id, scan_type, total, duplicate = dup
            print(f"      - 设备ID {device_id}, {scan_type}: 总计 {total}, 重复 {duplicate}")
        
        # 3. 删除重复记录
        delete_query = text("""
            DELETE FROM scan_results 
            WHERE id IN (
                SELECT id FROM (
                    SELECT 
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY device_id, scan_type 
                            ORDER BY scan_time DESC
                        ) as rn
                    FROM scan_results
                ) ranked
                WHERE rn > 1
            )
        """)
        
        result = db.execute(delete_query)
        db.commit()
        
        # 4. 统计清理后的数据
        total_after = db.query(ScanResult).count()
        deleted_count = total_before - total_after
        
        print(f"\n✅ 清理完成!")
        print(f"   删除重复记录数: {deleted_count}")
        print(f"   清理后总扫描结果数: {total_after}")
        print(f"   节省存储空间: 约 {deleted_count} 条记录")
        
        # 5. 验证清理结果
        remaining_duplicates = db.execute(text("""
            SELECT 
                device_id,
                scan_type,
                COUNT(*) as count
            FROM scan_results 
            GROUP BY device_id, scan_type
            HAVING COUNT(*) > 1
        """)).fetchall()
        
        if not remaining_duplicates:
            print("✅ 验证通过: 没有重复记录")
        else:
            print("⚠️  警告: 仍有重复记录:")
            for dup in remaining_duplicates:
                print(f"      - 设备ID {dup[0]}, {dup[1]}: {dup[2]} 条")
        
        # 6. 显示清理后的统计
        print(f"\n📊 清理后的统计信息:")
        type_stats = db.execute(text("""
            SELECT 
                scan_type,
                COUNT(*) as count,
                COUNT(DISTINCT device_id) as unique_devices
            FROM scan_results 
            GROUP BY scan_type
        """)).fetchall()
        
        for stat in type_stats:
            scan_type, count, unique_devices = stat
            print(f"   {scan_type}: {count} 条结果, {unique_devices} 个唯一设备")
        
        device_stats = db.execute(text("""
            SELECT 
                device_id,
                COUNT(*) as scan_count
            FROM scan_results 
            GROUP BY device_id
            ORDER BY scan_count DESC
            LIMIT 10
        """)).fetchall()
        
        print(f"\n   扫描结果最多的前10个设备:")
        for stat in device_stats:
            device_id, scan_count = stat
            print(f"      - 设备ID {device_id}: {scan_count} 条扫描结果")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 清理过程中出错: {e}")
        raise
    finally:
        db.close()

def verify_one_result_per_device():
    """验证每个设备每种扫描类型只有一个结果"""
    db = SessionLocal()
    try:
        print("\n🔍 验证清理结果...")
        
        # 检查是否还有重复
        duplicates = db.execute(text("""
            SELECT 
                device_id,
                scan_type,
                COUNT(*) as count
            FROM scan_results 
            GROUP BY device_id, scan_type
            HAVING COUNT(*) > 1
        """)).fetchall()
        
        if not duplicates:
            print("✅ 验证通过: 每个设备每种扫描类型只有一个结果")
            
            # 显示设备统计
            device_count = db.query(Device).count()
            scan_result_count = db.query(ScanResult).count()
            
            print(f"   设备总数: {device_count}")
            print(f"   扫描结果总数: {scan_result_count}")
            print(f"   平均每个设备: {scan_result_count/device_count:.2f} 条扫描结果")
            
            return True
        else:
            print("❌ 验证失败: 仍有重复记录:")
            for dup in duplicates:
                print(f"   - 设备ID {dup[0]}, {dup[1]}: {dup[2]} 条")
            return False
            
    except Exception as e:
        print(f"❌ 验证过程中出错: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🧹 扫描结果重复数据清理工具")
    print("=" * 50)
    
    try:
        # 执行清理
        cleanup_duplicate_scan_results()
        
        # 验证结果
        verify_one_result_per_device()
        
        print("\n🎉 清理和验证完成!")
        
    except Exception as e:
        print(f"\n❌ 脚本执行失败: {e}")
        sys.exit(1)

清理重复扫描结果脚本
确保每个设备每种扫描类型只有一个最新的扫描结果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.base import engine, SessionLocal
from db.models import ScanResult, Device
from sqlalchemy import text
import datetime

def cleanup_duplicate_scan_results():
    """清理重复的扫描结果"""
    db = SessionLocal()
    try:
        print("🔍 开始清理重复的扫描结果...")
        
        # 1. 统计清理前的数据
        total_before = db.query(ScanResult).count()
        print(f"   清理前总扫描结果数: {total_before}")
        
        # 2. 查找重复记录
        duplicates_query = text("""
            WITH ranked_results AS (
                SELECT 
                    id,
                    device_id,
                    scan_type,
                    target_ip,
                    scan_time,
                    ROW_NUMBER() OVER (
                        PARTITION BY device_id, scan_type 
                        ORDER BY scan_time DESC
                    ) as rn
                FROM scan_results
            )
            SELECT 
                device_id,
                scan_type,
                COUNT(*) as total_count,
                COUNT(CASE WHEN rn > 1 THEN 1 END) as duplicate_count
            FROM ranked_results 
            GROUP BY device_id, scan_type
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC
        """)
        
        duplicates = db.execute(duplicates_query).fetchall()
        
        if not duplicates:
            print("✅ 没有发现重复的扫描结果")
            return
        
        print(f"   发现 {len(duplicates)} 个设备有重复扫描结果:")
        for dup in duplicates:
            device_id, scan_type, total, duplicate = dup
            print(f"      - 设备ID {device_id}, {scan_type}: 总计 {total}, 重复 {duplicate}")
        
        # 3. 删除重复记录
        delete_query = text("""
            DELETE FROM scan_results 
            WHERE id IN (
                SELECT id FROM (
                    SELECT 
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY device_id, scan_type 
                            ORDER BY scan_time DESC
                        ) as rn
                    FROM scan_results
                ) ranked
                WHERE rn > 1
            )
        """)
        
        result = db.execute(delete_query)
        db.commit()
        
        # 4. 统计清理后的数据
        total_after = db.query(ScanResult).count()
        deleted_count = total_before - total_after
        
        print(f"\n✅ 清理完成!")
        print(f"   删除重复记录数: {deleted_count}")
        print(f"   清理后总扫描结果数: {total_after}")
        print(f"   节省存储空间: 约 {deleted_count} 条记录")
        
        # 5. 验证清理结果
        remaining_duplicates = db.execute(text("""
            SELECT 
                device_id,
                scan_type,
                COUNT(*) as count
            FROM scan_results 
            GROUP BY device_id, scan_type
            HAVING COUNT(*) > 1
        """)).fetchall()
        
        if not remaining_duplicates:
            print("✅ 验证通过: 没有重复记录")
        else:
            print("⚠️  警告: 仍有重复记录:")
            for dup in remaining_duplicates:
                print(f"      - 设备ID {dup[0]}, {dup[1]}: {dup[2]} 条")
        
        # 6. 显示清理后的统计
        print(f"\n📊 清理后的统计信息:")
        type_stats = db.execute(text("""
            SELECT 
                scan_type,
                COUNT(*) as count,
                COUNT(DISTINCT device_id) as unique_devices
            FROM scan_results 
            GROUP BY scan_type
        """)).fetchall()
        
        for stat in type_stats:
            scan_type, count, unique_devices = stat
            print(f"   {scan_type}: {count} 条结果, {unique_devices} 个唯一设备")
        
        device_stats = db.execute(text("""
            SELECT 
                device_id,
                COUNT(*) as scan_count
            FROM scan_results 
            GROUP BY device_id
            ORDER BY scan_count DESC
            LIMIT 10
        """)).fetchall()
        
        print(f"\n   扫描结果最多的前10个设备:")
        for stat in device_stats:
            device_id, scan_count = stat
            print(f"      - 设备ID {device_id}: {scan_count} 条扫描结果")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 清理过程中出错: {e}")
        raise
    finally:
        db.close()

def verify_one_result_per_device():
    """验证每个设备每种扫描类型只有一个结果"""
    db = SessionLocal()
    try:
        print("\n🔍 验证清理结果...")
        
        # 检查是否还有重复
        duplicates = db.execute(text("""
            SELECT 
                device_id,
                scan_type,
                COUNT(*) as count
            FROM scan_results 
            GROUP BY device_id, scan_type
            HAVING COUNT(*) > 1
        """)).fetchall()
        
        if not duplicates:
            print("✅ 验证通过: 每个设备每种扫描类型只有一个结果")
            
            # 显示设备统计
            device_count = db.query(Device).count()
            scan_result_count = db.query(ScanResult).count()
            
            print(f"   设备总数: {device_count}")
            print(f"   扫描结果总数: {scan_result_count}")
            print(f"   平均每个设备: {scan_result_count/device_count:.2f} 条扫描结果")
            
            return True
        else:
            print("❌ 验证失败: 仍有重复记录:")
            for dup in duplicates:
                print(f"   - 设备ID {dup[0]}, {dup[1]}: {dup[2]} 条")
            return False
            
    except Exception as e:
        print(f"❌ 验证过程中出错: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🧹 扫描结果重复数据清理工具")
    print("=" * 50)
    
    try:
        # 执行清理
        cleanup_duplicate_scan_results()
        
        # 验证结果
        verify_one_result_per_device()
        
        print("\n🎉 清理和验证完成!")
        
    except Exception as e:
        print(f"\n❌ 脚本执行失败: {e}")
        sys.exit(1)