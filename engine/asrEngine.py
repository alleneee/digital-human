# -*- coding: utf-8 -*-
'''
语音识别引擎基类定义
'''

from typing import List, Optional, Union
from .engineBase import BaseEngine
from utils.protocol import AudioMessage, TextMessage
import logging

# 配置日志
logger = logging.getLogger(__name__)

class ASREngine(BaseEngine):
    """
    语音识别引擎基类
    """
    
    async def run(self, input: Union[AudioMessage, List[AudioMessage]], **kwargs) -> Optional[TextMessage]:
        """
        执行语音识别
        
        参数:
            input: 输入音频消息或音频消息列表
            **kwargs: 额外参数，可包括:
                language: 语言代码 (auto, zh, en等)
                use_itn: 是否使用标点和反向文本规范化
                
        返回:
            TextMessage: 识别结果文本
        """
        raise NotImplementedError("子类必须实现run方法")
