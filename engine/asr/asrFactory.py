# -*- coding: utf-8 -*-
'''
ASR 工厂类实现
'''

from ..builder import ASREngines
from ..engineBase import BaseEngine
from typing import List
from yacs.config import CfgNode as CN
import logging

# 配置日志
logger = logging.getLogger(__name__)

class ASRFactory:
    """
    语音识别工厂类，用于创建不同的 ASR 引擎实例
    """
    @staticmethod
    def create(config: CN) -> BaseEngine:
        """
        创建 ASR 引擎实例
        
        参数:
            config: 配置信息
            
        返回:
            BaseEngine: ASR 引擎实例
        """
        if config.NAME in ASREngines.list():
            logger.info(f"[ASRFactory] 创建引擎: {config.NAME}")
            return ASREngines.get(config.NAME)(config)
        else:
            supported_engines = ASREngines.list()
            raise RuntimeError(f"[ASRFactory] 请检查配置，支持的 ASR 引擎: {supported_engines}")
    
    @staticmethod
    def list() -> List:
        """
        获取所有支持的 ASR 引擎列表
        
        返回:
            List: 支持的 ASR 引擎列表
        """
        return ASREngines.list()
