# -*- coding: utf-8 -*-
'''
语音合成引擎基类定义
'''

from typing import List, Optional
from .engineBase import BaseEngine
from utils.protocol import TextMessage, AudioMessage
import logging

# 配置日志
logger = logging.getLogger(__name__)

class TTSEngine(BaseEngine):
    """
    语音合成引擎基类
    """
    
    async def run(self, input: TextMessage, **kwargs) -> Optional[AudioMessage]:
        """
        执行语音合成
        
        参数:
            input: 输入文本消息
            **kwargs: 额外参数，可包括:
                voice_id: 声音ID
                rate: 语速
                pitch: 音调
                volume: 音量
                
        返回:
            AudioMessage: 合成的音频消息
        """
        raise NotImplementedError("子类必须实现run方法")
