# -*- coding: utf-8 -*-
'''
TTS 工厂类，用于创建不同的 TTS 引擎实例
'''

from ..builder import TTSEngines
from ..engineBase import BaseEngine
from typing import List
from yacs.config import CfgNode as CN
import logging

# 配置日志
logger = logging.getLogger(__name__)

__all__ = ["TTSFactory"]

class TTSFactory():
    """
    TTS 工厂类，用于创建不同的 TTS 引擎实例
    """
    @staticmethod
    def create(config: CN) -> BaseEngine:
        """
        根据配置创建 TTS 引擎实例
        
        参数:
            config: 配置对象
            
        返回:
            TTS 引擎实例
        """
        if config.NAME in TTSEngines.list():
            logger.info(f"[TTSFactory] 创建引擎: {config.NAME}")
            return TTSEngines.get(config.NAME)(config)
        else:
            raise RuntimeError(f"[TTSFactory] 请检查配置，支持的 TTS 引擎: {TTSEngines.list()}")
    
    @staticmethod
    def list() -> List:
        """
        获取所有注册的 TTS 引擎列表
        
        返回:
            TTS 引擎列表
        """
        return TTSEngines.list()
