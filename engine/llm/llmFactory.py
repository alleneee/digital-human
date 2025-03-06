# -*- coding: utf-8 -*-
'''
LLM 工厂类，用于创建不同的 LLM 引擎实例
'''

from ..builder import LLMEngines
from ..engineBase import BaseEngine
from typing import List
from yacs.config import CfgNode as CN
import logging

# 配置日志
logger = logging.getLogger(__name__)

__all__ = ["LLMFactory"]

class LLMFactory():
    """
    LLM 工厂类，用于创建不同的 LLM 引擎实例
    """
    @staticmethod
    def create(config: CN) -> BaseEngine:
        """
        根据配置创建 LLM 引擎实例
        
        参数:
            config: 配置对象
            
        返回:
            LLM 引擎实例
        """
        if config.NAME in LLMEngines.list():
            logger.info(f"[LLMFactory] 创建引擎: {config.NAME}")
            return LLMEngines.get(config.NAME)(config)
        else:
            raise RuntimeError(f"[LLMFactory] 请检查配置，支持的 LLM 引擎: {LLMEngines.list()}")
    
    @staticmethod
    def list() -> List:
        """
        获取所有注册的 LLM 引擎列表
        
        返回:
            LLM 引擎列表
        """
        return LLMEngines.list()
