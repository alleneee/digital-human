# -*- coding: utf-8 -*-
'''
OpenAI LLM 引擎实现
'''

import asyncio
import json
import aiohttp
import logging
from typing import List, Optional, Dict, Any, Union
from yacs.config import CfgNode as CN
from utils.protocol import TextMessage
from ..engineBase import BaseEngine
from ..builder import LLMEngines

# 配置日志
logger = logging.getLogger(__name__)

@LLMEngines.register()
class OpenAILLM(BaseEngine):
    """
    OpenAI LLM 引擎实现
    """
    
    def checkKeys(self) -> List[str]:
        """
        检查必要的配置项
        """
        return ["NAME", "API_KEY", "MODEL"]
    
    def setup(self):
        """
        初始化 OpenAI LLM 引擎
        """
        self.api_key = self.cfg.API_KEY
        self.model = self.cfg.MODEL
        self.temperature = self.cfg.get("TEMPERATURE", 0.7)
        self.max_tokens = self.cfg.get("MAX_TOKENS", 1500)
        self.system_prompt = self.cfg.get("SYSTEM_PROMPT", "你是一个友好的AI助手，能够提供简洁明了的回答。")
        self.timeout = self.cfg.get("TIMEOUT_S", 10)
        self.stream = self.cfg.get("STREAM", False)
        
        # OpenAI API 端点
        self.api_url = "https://api.openai.com/v1/chat/completions"
        
        logger.info(f"[OpenAILLM] 引擎初始化完成，模型: {self.model}")
    
    async def run(self, input: Union[TextMessage, List[TextMessage]], **kwargs) -> Optional[TextMessage]:
        """
        运行 OpenAI LLM 引擎，生成回复
        
        参数:
            input: 输入文本消息或消息列表
            **kwargs: 额外参数
                - context: 对话上下文，包含之前的消息
                
        返回:
            生成的回复文本消息
        """
        try:
            # 构建消息
            messages = []
            
            # 添加系统提示
            if self.system_prompt:
                messages.append({
                    "role": "system",
                    "content": self.system_prompt
                })
            
            # 添加上下文消息
            context = kwargs.get("context", [])
            if context:
                for msg in context:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        messages.append(msg)
            
            # 添加当前输入消息
            if isinstance(input, list):
                for msg in input:
                    messages.append({
                        "role": "user",
                        "content": msg.data
                    })
            else:
                messages.append({
                    "role": "user",
                    "content": input.data
                })
            
            # 构建请求数据
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": self.stream
            }
            
            # 设置请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 发起请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"[OpenAILLM] API请求失败: {response.status}, {error_text}")
                        return None
                    
                    if not self.stream:
                        # 非流式响应
                        result = await response.json()
                        response_text = result["choices"][0]["message"]["content"].strip()
                    else:
                        # 流式响应（累积所有的消息片段）
                        response_text = ""
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith("data: ") and line != "data: [DONE]":
                                try:
                                    data = json.loads(line[6:])
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        if "content" in delta:
                                            response_text += delta["content"]
                                except Exception as e:
                                    logger.error(f"[OpenAILLM] 解析流响应错误: {str(e)}")
            
            # 创建回复消息
            response_message = TextMessage(
                data=response_text,
                desc="OpenAI生成的回复"
            )
            
            return response_message
            
        except asyncio.TimeoutError:
            logger.error(f"[OpenAILLM] API请求超时")
            return None
        except Exception as e:
            logger.error(f"[OpenAILLM] 处理出错: {str(e)}")
            return None
