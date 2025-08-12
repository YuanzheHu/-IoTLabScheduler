"""
tcpdump_util.py

Utility for managing tcpdump processes for packet capture.

This module provides the TcpdumpUtil class, which allows starting and stopping
a tcpdump process to capture network packets to a file. It is useful for
automating packet capture in scripts or tests.

Example usage:
    tcpdump = TcpdumpUtil(output_file='capture.pcap', interface='eth0')
    tcpdump.start()
    # ... generate or observe network traffic ...
    tcpdump.stop()
"""

import subprocess
import os
import signal
import time


class TcpdumpUtil:
    """Utility class to manage tcpdump process for packet capture."""

    def __init__(self, output_file='capture.pcap', interface='any', extra_args=None, target_ip=None):
        """Initialize TcpdumpUtil.
        
        Args:
            output_file (str): Output file for captured packets
            interface (str): Network interface to capture on ('any' for all interfaces)
            extra_args (list): Additional tcpdump arguments
            target_ip (str): Target IP address to filter for (optional)
        """
        self.output_file = output_file
        self.interface = interface
        self.extra_args = extra_args or []
        self.target_ip = target_ip
        self.process = None

    def start(self):
        """Start the tcpdump process with bidirectional capture."""
        if self.process is not None:
            raise RuntimeError('tcpdump is already running')
        
        # Build command with options for bidirectional capture
        cmd = [
            'tcpdump',  # In Docker we don't need sudo
            '-i', self.interface,
            '-w', self.output_file,
            '-s', '0',  # Capture full packet size
            '-n',  # Don't resolve hostnames
            '-v',  # Verbose output
            '-e',  # Print link-level header
            '-tttt'  # Print human readable timestamps
        ]
        
        # Add target IP filter if specified
        if self.target_ip:
            # Capture both directions: packets to/from the target IP
            cmd.extend(['host', self.target_ip])
        else:
            # If no target IP, capture all traffic on the interface
            cmd.extend(['-v'])  # Verbose output
        
        # Add extra arguments
        cmd.extend(self.extra_args)
        
        # 添加详细的错误处理和日志
        print(f"启动tcpdump命令: {' '.join(cmd)}")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        
        # 检查tcpdump命令是否可用
        try:
            result = subprocess.run(['which', 'tcpdump'], check=True, capture_output=True, text=True)
            print(f"tcpdump路径: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            raise RuntimeError("tcpdump命令不可用")
        
        # 检查网络接口
        try:
            # 列出所有网络接口
            result = subprocess.run(['ip', 'link', 'show'], check=True, capture_output=True, text=True)
            print(f"可用网络接口:\n{result.stdout}")
            
            # 获取指定接口的IP地址
            result = subprocess.run(['ip', 'addr', 'show', self.interface], check=True, capture_output=True, text=True)
            print(f"{self.interface}接口信息:\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"网络接口检查失败: {e}")
        
        # 测试tcpdump是否可以在指定接口上工作
        try:
            test_cmd = ['tcpdump', '-i', self.interface, '-c', '1', '-n']
            print(f"测试tcpdump命令: {' '.join(test_cmd)}")
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=3)
            print(f"tcpdump测试结果:\n{result.stdout}\n{result.stderr}")
        except subprocess.TimeoutExpired:
            print("tcpdump测试超时，但这是正常的")
        except Exception as e:
            raise RuntimeError(f"tcpdump测试失败: {e}")
        
        # 启动tcpdump进程
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,
                text=True  # 使用文本模式
            )
            print(f"tcpdump进程已启动 (PID: {self.process.pid})")
        except Exception as e:
            raise RuntimeError(f"启动tcpdump进程失败: {e}")
        
        # 等待一下确保进程启动
        time.sleep(1)
        
        # 检查进程是否正常启动
        if self.process.poll() is not None:
            stderr_output = self.process.stderr.read() if self.process.stderr else "无错误输出"
            raise RuntimeError(f"tcpdump进程启动失败: {stderr_output}")
        
        # 检查输出文件是否创建
        if not os.path.exists(self.output_file):
            raise RuntimeError(f"tcpdump输出文件未创建: {self.output_file}")
        
        print(f"tcpdump已成功启动，输出文件: {self.output_file}")

    def stop(self):
        """Stop the tcpdump process."""
        if self.process is None:
            raise RuntimeError('tcpdump is not running')
        
        print(f"停止tcpdump进程 (PID: {self.process.pid})")
        
        try:
            # 检查进程是否还在运行
            if self.process.poll() is not None:
                print(f"tcpdump进程已经停止，返回码: {self.process.returncode}")
                stdout = self.process.stdout.read() if self.process.stdout else ""
                stderr = self.process.stderr.read() if self.process.stderr else ""
                if stdout:
                    print(f"进程输出:\n{stdout}")
                if stderr:
                    print(f"进程错误:\n{stderr}")
                return
            
            # 先尝试优雅停止
            print("发送SIGTERM信号")
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            
            # 等待最多5秒
            for i in range(10):
                if self.process.poll() is not None:
                    print(f"进程已停止，返回码: {self.process.returncode}")
                    break
                print(f"等待进程停止... ({i+1}/10)")
                time.sleep(0.5)
            
            # 如果还没停止，强制终止
            if self.process.poll() is None:
                print("发送SIGKILL信号")
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                self.process.wait()
                print(f"进程已被强制终止，返回码: {self.process.returncode}")
            
            # 读取进程输出
            stdout = self.process.stdout.read() if self.process.stdout else ""
            stderr = self.process.stderr.read() if self.process.stderr else ""
            if stdout:
                print(f"进程输出:\n{stdout}")
            if stderr:
                print(f"进程错误:\n{stderr}")
            
            # 检查输出文件
            if os.path.exists(self.output_file):
                file_size = os.path.getsize(self.output_file)
                print(f"PCAP文件大小: {file_size} bytes")
                if file_size == 0:
                    print("警告: PCAP文件为空")
            else:
                print(f"警告: PCAP文件不存在: {self.output_file}")
            
            print("tcpdump进程已停止")
        except Exception as e:
            print(f"停止tcpdump进程时出错: {e}")
        finally:
            self.process = None


if __name__ == '__main__':
    # Test the TcpdumpUtil module
    print("Testing TcpdumpUtil module...")
    
    # Create test capture file
    test_file = 'test_capture.pcap'
    interface = 'lo'  # Use loopback for safe testing
    
    tcpdump = TcpdumpUtil(output_file=test_file, interface=interface)
    
    try:
        print(f"Starting tcpdump capture on {interface}...")
        tcpdump.start()
        
        # Generate some test traffic
        print("Generating test traffic...")
        for i in range(3):
            subprocess.run(['ping', '-c', '1', '127.0.0.1'], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
        
        print("Stopping tcpdump...")
        tcpdump.stop()
        
        # Check if file was created
        if os.path.exists(test_file):
            file_size = os.path.getsize(test_file)
            print(f"Test successful! Capture file created: {test_file} ({file_size} bytes)")
        else:
            print("Test failed: Capture file not created")
            
    except Exception as e:
        print(f"Test failed with error: {e}")