# -*- coding: utf-8 -*-
'''
测试LLM引擎
'''

import asyncio
import logging
import os
from pathlib import Path
from engine.llm.openaiLLM import OpenAILLM
from yacs.config import CfgNode as CN
from utils import TextMessage

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_openai_llm():
    """测试OpenAI大语言模型"""
    try:
        logger.info("测试OpenAI LLM引擎...")
        
        # 获取API Key（从环境变量）
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("未设置OPENAI_API_KEY环境变量")
            return None
        
        # 创建OpenAI LLM配置
        cfg = CN()
        cfg.NAME = "OpenAILLM"
        cfg.API_KEY = api_key
        cfg.MODEL = "gpt-3.5-turbo"
        cfg.TEMPERATURE = 0.7
        cfg.MAX_TOKENS = 500
        cfg.SYSTEM_PROMPT = "你是一个友好的AI助手，能够提供简洁明了的回答。请用中文回复用户的问题。"
        cfg.TIMEOUT_S = 10
        cfg.STREAM = False
        
        # 初始化OpenAI LLM对象
        llm = OpenAILLM(cfg)
        
        # 准备测试文本
        test_text = "你好，请简单介绍一下自己"
        test_message = TextMessage(data=test_text)
        
        logger.info(f"发送测试文本: '{test_text}'")
        
        # 调用LLM引擎
        response = await llm.run(test_message)
        
        if response:
            logger.info(f"收到回复: '{response.data}'")
            return response.data
        else:
            logger.error("未收到回复")
            return None
            
    except Exception as e:
        logger.error(f"测试过程出错: {str(e)}")
        return None

if __name__ == "__main__":
    # 运行测试
    result = asyncio.run(test_openai_llm())
    if result:
        print(f"\n最终LLM回复结果:\n{result}")
    else:
        print("\n测试失败，未获得回复")
