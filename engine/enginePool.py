# -*- coding: utf-8 -*-
'''
引擎池，用于管理不同类型的引擎实例
'''

import logging
import os
from enum import Enum
from typing import Dict, Optional
from yacs.config import CfgNode as CN
from utils import config
from .engineBase import BaseEngine
from .asr import ASRFactory
from .llm import LLMFactory
from .tts import TTSFactory

# 配置日志
logger = logging.getLogger(__name__)

class EngineType(Enum):
    """引擎类型枚举"""
    ASR = "asr"  # 自动语音识别
    LLM = "llm"  # 大型语言模型
    TTS = "tts"  # 文本到语音

    def __str__(self):
        return str(self.value)

class EnginePool:
    """
    引擎池，用于管理不同类型的引擎实例
    """
    def __init__(self):
        """初始化引擎池"""
        self.engines = {
            EngineType.ASR: {},
            EngineType.LLM: {},
            EngineType.TTS: {}
        }
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs/engines")
        
    def getEngine(self, engine_type: EngineType, engine_name: str) -> Optional[BaseEngine]:
        """
        获取指定类型和名称的引擎实例
        
        参数:
            engine_type: 引擎类型
            engine_name: 引擎名称
            
        返回:
            引擎实例，如果不存在则创建新实例
        """
        # 如果引擎已存在，直接返回
        if engine_name in self.engines[engine_type]:
            return self.engines[engine_type][engine_name]
        
        # 否则创建新引擎
        try:
            # 构建配置文件路径
            config_path = os.path.join(self.config_dir, str(engine_type), f"{engine_name}.yaml")
            if not os.path.exists(config_path):
                logger.error(f"引擎配置文件不存在: {config_path}")
                return None
            
            # 加载配置
            engine_config = config.load_yaml(config_path)
            
            # 根据引擎类型创建实例
            engine = None
            if engine_type == EngineType.ASR:
                engine = ASRFactory.create(engine_config)
            elif engine_type == EngineType.LLM:
                engine = LLMFactory.create(engine_config)
            elif engine_type == EngineType.TTS:
                engine = TTSFactory.create(engine_config)
            
            # 存储并返回引擎实例
            if engine:
                self.engines[engine_type][engine_name] = engine
                logger.info(f"创建引擎成功: {engine_type} - {engine_name}")
                return engine
            else:
                logger.error(f"创建引擎失败: {engine_type} - {engine_name}")
                return None
                
        except Exception as e:
            logger.error(f"获取引擎异常: {engine_type} - {engine_name}, 错误: {e}")
            return None
    
    def listEngines(self, engine_type: EngineType) -> Dict[str, BaseEngine]:
        """
        列出指定类型的所有引擎
        
        参数:
            engine_type: 引擎类型
            
        返回:
            引擎名称到实例的映射
        """
        return self.engines[engine_type]
    
    async def closeAll(self):
        """
        关闭所有引擎
        """
        for engine_type in self.engines:
            for engine_name, engine in self.engines[engine_type].items():
                try:
                    if hasattr(engine, 'close'):
                        await engine.close()
                    logger.info(f"关闭引擎: {engine_type} - {engine_name}")
                except Exception as e:
                    logger.error(f"关闭引擎异常: {engine_type} - {engine_name}, 错误: {e}")
