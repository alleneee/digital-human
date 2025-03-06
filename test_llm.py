# -*- coding: utf-8 -*-
'''
测试 LLM 实现
'''

import asyncio
import os
import logging
from utils import config, TextMessage
from engine.llm import LLMFactory

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_llm():
    """
    测试 LLM 引擎
    """
    try:
        # 加载 MiniMax LLM 配置
        config_path = os.path.join(os.path.dirname(__file__), "configs/engines/llm/minimaxAPI.yaml")
        if not os.path.exists(config_path):
            logger.error(f"LLM 配置文件不存在: {config_path}")
            return
            
        logger.info(f"加载 LLM 配置: {config_path}")
        llm_config = config.load_yaml(config_path)
        
        # 创建 LLM 引擎
        logger.info("创建 LLM 引擎")
        llm_engine = LLMFactory.create(llm_config)
        
        # 获取用户输入
        user_input = input("请输入问题: ")
        if not user_input:
            logger.error("输入为空")
            return
            
        # 创建文本消息
        text_message = TextMessage(
            data=user_input,
            desc="user"
        )
        
        # 调用 LLM 引擎生成回复
        logger.info("开始生成回复")
        result = await llm_engine.run(text_message)
        
        if result:
            logger.info(f"生成的回复: {result.data}")
        else:
            logger.error("生成回复失败")
            
        # 关闭引擎会话
        await llm_engine.close()
    except Exception as e:
        logger.error(f"测试过程中出现错误: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm())
