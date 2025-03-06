# -*- coding: utf-8 -*-
'''
配置解析器
'''

import os
import re
import logging
from yacs.config import CfgNode as CN
from typing import Dict, Any

# 配置日志
logger = logging.getLogger(__name__)

class ConfigParser:
    """
    配置解析器，用于加载和解析配置文件
    """
    @staticmethod
    def load_yaml(yaml_file: str) -> CN:
        """
        加载YAML配置文件
        
        参数:
            yaml_file: YAML配置文件路径
            
        返回:
            CN: 配置节点
        """
        if not os.path.exists(yaml_file):
            logger.error(f"配置文件不存在: {yaml_file}")
            raise FileNotFoundError(f"配置文件不存在: {yaml_file}")
            
        config = CN()
        config.defrost()
        config.merge_from_file(yaml_file)
        
        # 处理环境变量
        ConfigParser._process_env_vars(config)
        
        config.freeze()
        return config
    
    @staticmethod
    def _process_env_vars(config: CN) -> None:
        """
        处理配置中的环境变量引用
        
        参数:
            config: 配置节点
        """
        for k, v in config.items():
            if isinstance(v, CN):
                ConfigParser._process_env_vars(v)
            elif isinstance(v, str) and "${" in v and "}" in v:
                # 替换环境变量
                env_vars = re.findall(r'\${([^}]+)}', v)
                for env_var in env_vars:
                    env_value = os.environ.get(env_var, "")
                    if not env_value:
                        logger.warning(f"环境变量未设置: {env_var}")
                    config[k] = v.replace(f"${{{env_var}}}", env_value)
                    
    @staticmethod
    def dict_to_cn(d: Dict[str, Any]) -> CN:
        """
        将字典转换为配置节点
        
        参数:
            d: 字典
            
        返回:
            CN: 配置节点
        """
        config = CN()
        config.defrost()
        
        for k, v in d.items():
            if isinstance(v, dict):
                config[k] = ConfigParser.dict_to_cn(v)
            else:
                config[k] = v
                
        config.freeze()
        return config

# 全局配置实例
config = ConfigParser()
