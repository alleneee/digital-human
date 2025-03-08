# -*- coding: utf-8 -*-
'''
配置管理工具
'''

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from yacs.config import CfgNode as CN

# 配置日志
logger = logging.getLogger(__name__)

def load_config(config_file: str) -> CN:
    """
    加载配置文件
    
    参数:
        config_file: 配置文件路径
        
    返回:
        配置对象
    """
    try:
        logger.info(f"加载配置文件: {config_file}")
        
        # 创建默认配置
        cfg = CN()
        
        # 设置基础默认值
        cfg.NAME = "DigitalHuman"
        
        # ASR 相关配置
        cfg.ASR = CN()
        cfg.ASR.ENABLED = True
        cfg.ASR.NAME = "funasrLocal"
        
        # LLM 相关配置
        cfg.LLM = CN()
        cfg.LLM.ENABLED = True
        cfg.LLM.NAME = "openai"
        
        # TTS 相关配置
        cfg.TTS = CN()
        cfg.TTS.ENABLED = True
        cfg.TTS.NAME = "edge"
        
        # API 相关配置
        cfg.API = CN()
        cfg.API.HOST = "127.0.0.1"
        cfg.API.PORT = 8000
        
        # 检查配置文件是否存在
        if not os.path.exists(config_file):
            logger.warning(f"配置文件不存在: {config_file}，使用默认配置")
            return cfg
        
        # 从文件加载配置
        cfg.merge_from_file(config_file)
        
        # 完成配置后冻结，防止修改
        cfg.freeze()
        
        return cfg
        
    except Exception as e:
        logger.error(f"加载配置文件出错: {str(e)}")
        raise

def merge_configs(base_config: CN, override_config: CN) -> CN:
    """
    合并配置
    
    参数:
        base_config: 基础配置
        override_config: 覆盖配置
        
    返回:
        合并后的配置
    """
    try:
        # 解冻配置以便修改
        if base_config.is_frozen():
            base_config = base_config.clone()
            base_config.defrost()
            
        # 合并覆盖配置
        base_config.merge_from_other_cfg(override_config)
        
        # 完成配置后冻结，防止修改
        base_config.freeze()
        
        return base_config
        
    except Exception as e:
        logger.error(f"合并配置出错: {str(e)}")
        raise

def create_engine_config(config: CN, engine_type: str, engine_name: str) -> CN:
    """
    创建引擎配置
    
    参数:
        config: 主配置
        engine_type: 引擎类型，例如 'ASR', 'LLM', 'TTS'
        engine_name: 引擎名称
        
    返回:
        引擎配置
    """
    try:
        # 引擎配置目录
        config_dir = Path("configs") / "engines" / engine_type.lower()
        config_file = config_dir / f"{engine_name}.yaml"
        
        # 检查配置文件是否存在
        if not config_file.exists():
            logger.warning(f"引擎配置文件不存在: {config_file}，使用默认配置")
            
            # 创建默认引擎配置
            engine_cfg = CN()
            engine_cfg.NAME = engine_name
            return engine_cfg
        
        # 从文件加载引擎配置
        engine_cfg = CN()
        engine_cfg.merge_from_file(str(config_file))
        
        # 完成配置后冻结，防止修改
        engine_cfg.freeze()
        
        return engine_cfg
        
    except Exception as e:
        logger.error(f"创建引擎配置出错: {str(e)}")
        raise
