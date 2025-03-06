# -*- coding: utf-8 -*-
'''
MiniMax LLM 引擎实现
'''

from ..builder import LLMEngines
from ..engineBase import BaseEngine
import json
import os
import aiohttp
from typing import List, Optional, Union
from utils import TextMessage
import logging

# 配置日志
logger = logging.getLogger(__name__)

__all__ = ["MinimaxAPI"]

@LLMEngines.register("MinimaxAPI")
class MinimaxAPI(BaseEngine): 
    """
    MiniMax LLM 引擎实现
    """
    def checkKeys(self) -> List[str]:
        """
        检查必要的配置项
        
        返回:
            必要的配置项列表
        """
        return ["GROUP_ID", "API_KEY", "MODEL", "LLM_URL"]
    
    def setup(self):
        """
        设置引擎，初始化 aiohttp 会话
        """
        self.session = None
        self.group_id = self.cfg.GROUP_ID
        self.api_key = self.cfg.API_KEY
        self.model = self.cfg.MODEL
        self.llm_url = self.cfg.LLM_URL
        
        # 验证必要的配置
        if not self.group_id or not self.api_key:
            logger.warning("[LLM] MiniMax GroupID 或 API Key 未配置")
    
    async def ensure_session(self):
        """
        确保 aiohttp 会话已创建
        
        返回:
            aiohttp 会话
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """
        关闭会话
        """
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def run(self, input: Union[TextMessage, List[TextMessage]], **kwargs) -> Optional[TextMessage]:
        """
        运行 LLM 引擎，生成回复
        
        参数:
            input: 输入文本消息或消息列表
            **kwargs: 其他参数
            
        返回:
            生成的文本消息
        """
        try:
            session = await self.ensure_session()
            
            # 处理系统提示词
            system_prompt = kwargs.get("system_prompt", "你是一个友好的AI数字人助手,名叫小智。请用自然、温暖、亲切的语气回答问题。")
            
            # 处理输入消息
            if isinstance(input, list):
                messages = [
                    {
                        "role": "user" if inp.desc == "user" else "assistant",
                        "content": inp.data
                    }
                    for inp in input
                ]
            else:
                messages = [
                    {
                        "role": "user",
                        "content": input.data
                    }
                ]
            
            # 设置请求参数
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 800)
            top_p = kwargs.get("top_p", 0.9)
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
                "stream": False,
                "reply_constraints": {
                    "sender_type": "BOT",
                    "sender_name": "小智"
                },
                "bot_setting": [
                    {
                        "bot_name": "小智",
                        "content": system_prompt
                    }
                ]
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "X-Minimax-Group-Id": self.group_id
            }
            
            logger.debug(f"[LLM] 发送 MiniMax LLM 请求: {json.dumps(payload, ensure_ascii=False)}")
            
            async with session.post(self.llm_url,
                                   headers=headers,
                                   json=payload) as response:
                status = response.status
                response_json = await response.json()
                
                logger.debug(f"[LLM] MiniMax LLM 响应状态: {status}, 响应内容: {json.dumps(response_json, ensure_ascii=False)}")
                
                if status != 200:
                    logger.error(f"[LLM] MiniMax LLM 请求失败: {status} - {response_json}")
                    return None
                
                # 检查响应中的 base_resp 错误信息
                if "base_resp" in response_json and response_json["base_resp"].get("status_code", 0) != 0:
                    error_msg = response_json["base_resp"].get("status_msg", "未知错误")
                    logger.error(f"[LLM] MiniMax LLM API 返回错误: {error_msg}")
                    return None
                
                # 提取回复内容
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    content = response_json["choices"][0]["message"]["content"]
                    message = TextMessage(data=content)
                    return message
                else:
                    logger.warning(f"[LLM] MiniMax LLM 响应中没有发现回复内容: {response_json}")
                    return None
                
        except Exception as e:
            logger.error(f"[LLM] 引擎运行失败: {e}", exc_info=True)
            return None
