import re
import ast
import os
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

@dataclass
class ParsedParameter:
    """解析后的参数信息"""
    name: str
    type: str = "string"
    description: str = ""
    default: Optional[Any] = None
    required: bool = True
    options: Optional[List[str]] = None
    validation: Optional[Dict[str, Any]] = None

class ShellScriptParser:
    """解析shell脚本中的describe和参数信息"""
    
    def __init__(self):
        # 调整匹配顺序，让更具体的格式优先匹配
        self.param_patterns = [
            # 格式2: # param: name (type) - description (最具体，优先匹配)
            (r'#\s*param:\s*(\w+)\s*\(([^)]+)\)\s*-\s*(.+)', 'type_desc'),
            # 格式3: # param: name - description
            (r'#\s*param:\s*(\w+)\s*-\s*(.+)', 'desc_only'),
            # 格式1: # param: name=default_value
            (r'#\s*param:\s*(\w+)\s*=\s*(.+)', 'default_only'),
            # 格式4: # param: name
            (r'#\s*param:\s*(\w+)', 'name_only')
        ]
    
    def parse_script(self, script_content: Union[str, bytes]) -> Dict[str, Any]:
        """解析脚本内容，提取描述和参数信息"""
        # 如果是bytes，转换为字符串
        if isinstance(script_content, bytes):
            try:
                script_content = script_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    script_content = script_content.decode('latin-1')
                except UnicodeDecodeError:
                    script_content = script_content.decode('utf-8', errors='ignore')
        
        # 查找describe注释
        describe_match = re.search(r'#\s*describe:\s*(.+)', script_content, re.IGNORECASE)
        description = describe_match.group(1).strip() if describe_match else ""
        
        # 查找参数定义
        parameters = self._extract_parameters(script_content)
        
        return {
            "description": description,
            "parameters": parameters
        }
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """从文件路径解析shell脚本"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"脚本文件不存在: {file_path}")
        
        if not file_path.endswith('.sh'):
            raise ValueError(f"只支持.sh文件: {file_path}")
        
        try:
            with open(file_path, 'rb') as f:
                script_content = f.read()
            
            # 解析脚本内容
            result = self.parse_script(script_content)
            
            # 添加文件信息
            result.update({
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "file_size": len(script_content),
                "file_exists": True
            })
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"解析文件失败 {file_path}: {str(e)}")
    
    def parse_directory(self, directory_path: str, recursive: bool = False) -> List[Dict[str, Any]]:
        """解析目录中的所有.sh文件"""
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        if not os.path.isdir(directory_path):
            raise ValueError(f"不是目录: {directory_path}")
        
        results = []
        
        for root, dirs, files in os.walk(directory_path):
            # 过滤.sh文件
            sh_files = [f for f in files if f.endswith('.sh')]
            
            for sh_file in sh_files:
                file_path = os.path.join(root, sh_file)
                try:
                    result = self.parse_file(file_path)
                    results.append(result)
                except Exception as e:
                    print(f"警告: 解析文件失败 {file_path}: {str(e)}")
                    continue
            
            # 如果不递归，只处理根目录
            if not recursive:
                break
        
        return results
    
    def _extract_parameters(self, script_content: str) -> List[Dict[str, Any]]:
        """提取脚本中的参数定义"""
        parameters = []
        lines = script_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line.startswith('# param:'):
                continue
                
            # 尝试匹配各种参数格式
            for pattern, pattern_type in self.param_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    param = self._parse_parameter_line(match, pattern_type, line)
                    if param:
                        parameters.append(param)
                    break
        
        return [param.__dict__ for param in parameters]
    
    def _parse_parameter_line(self, match, pattern_type: str, line: str) -> Optional[ParsedParameter]:
        """解析单行参数定义"""
        groups = match.groups()
        
        if pattern_type == 'type_desc':
            # 格式2: name (type) - description
            name, param_type, description = groups
            return ParsedParameter(
                name=name.strip(),
                type=param_type.strip(),
                description=description.strip(),
                required=True
            )
        elif pattern_type == 'desc_only':
            # 格式3: name - description
            name, description = groups
            return ParsedParameter(
                name=name.strip(),
                description=description.strip(),
                required=True
            )
        elif pattern_type == 'default_only':
            # 格式1: name=default_value
            name, default_part = groups
            # 检查是否有描述部分
            if ' - ' in default_part:
                default, description = default_part.split(' - ', 1)
                return ParsedParameter(
                    name=name.strip(),
                    default=default.strip(),
                    description=description.strip(),
                    required=False
                )
            else:
                return ParsedParameter(
                    name=name.strip(),
                    default=default_part.strip(),
                    required=False
                )
        elif pattern_type == 'name_only':
            # 格式4: name
            name = groups[0]
            return ParsedParameter(
                name=name.strip(),
                required=True
            )
        
        return None
    
    def validate_parameters(self, script_content: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证参数值是否符合脚本要求"""
        # 这里可以添加更复杂的参数验证逻辑
        return parameters
    
    def get_script_summary(self, script_content: Union[str, bytes]) -> Dict[str, Any]:
        """获取脚本摘要信息"""
        parsed_info = self.parse_script(script_content)
        
        # 统计脚本基本信息
        if isinstance(script_content, str):
            lines = script_content.split('\n')
        else:
            lines = script_content.decode('utf-8', errors='ignore').split('\n')
            
        total_lines = len(lines)
        code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
        comment_lines = len([line for line in lines if line.strip().startswith('#')])
        
        return {
            "description": parsed_info["description"],
            "parameters": parsed_info["parameters"],
            "stats": {
                "total_lines": total_lines,
                "code_lines": code_lines,
                "comment_lines": comment_lines,
                "parameter_count": len(parsed_info["parameters"])
            }
        }
    
    def get_file_summary(self, file_path: str) -> Dict[str, Any]:
        """获取文件摘要信息"""
        result = self.parse_file(file_path)
        summary = self.get_script_summary(open(file_path, 'rb').read())
        
        result.update(summary)
        return result
