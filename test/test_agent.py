#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试OpenAI Agent功能
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import load_config
from engine.agent.agent_factory import AgentFactory
from engine.agent.openai_agent import OpenAIAgent

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_agent():
    """测试Agent功能"""
    try:
        # 加载配置
        config = load_config("configs/agent.yaml")
        
        if not config or not config.AGENT.ENABLED:
            logger.error("Agent功能未启用，请检查配置")
            return
        
        # 创建Agent实例
        agent = AgentFactory.create(config.AGENT)
        
        if not agent:
            logger.error("创建Agent实例失败")
            return
        
        # 测试查询
        queries = [
            "今天上海的天气怎么样？",
            "帮我查询一下关于人工智能的最新进展",
            "解释一下什么是数字人技术"
        ]
        
        for query in queries:
            logger.info(f"测试查询: {query}")
            
            # 处理查询
            response = await agent.process(query)
            
            # 输出结果
            logger.info(f"Agent回复: {response.text}")
            logger.info(f"元数据: {response.metadata}")
            logger.info("-" * 50)
            
        logger.info("测试完成")
        
    except Exception as e:
        logger.error(f"测试出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_agent()) 