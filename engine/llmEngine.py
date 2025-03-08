# -*- coding: utf-8 -*-
'''
大语言模型引擎基类定义
'''

from typing import List, Optional, Dict, Any
from .engineBase import BaseEngine
from utils.protocol import TextMessage
import logging

# 配置日志
logger = logging.getLogger(__name__)

class LLMEngine(BaseEngine):
    """
    大语言模型引擎基类
    """
    
    async def run(self, input: TextMessage, **kwargs) -> Optional[TextMessage]:
        """
        执行文本生成/对话
        
        参数:
            input: 输入文本消息
            **kwargs: 额外参数，可包括:
                context: 对话上下文
                system_prompt: 系统提示词
                temperature: 温度参数
                max_tokens: 最大生成token数
                
        返回:
            TextMessage: 生成的回复文本
        """
        raise NotImplementedError("子类必须实现run方法")
