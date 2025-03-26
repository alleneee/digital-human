#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试增强型网络搜索工具
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import load_config
from engine.agent.agent_factory import AgentFactory
from engine.agent.openai_agent import OpenAIAgent
from agents import Agent, Runner, trace

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_enhanced_search():
    """测试增强型网络搜索工具"""
    try:
        # 确保环境变量已设置
        required_vars = ["OPENAI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_SEARCH_ENGINE_ID", "FIRECRAWL_API_KEY"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            logger.error(f"缺少必要的环境变量: {', '.join(missing_vars)}")
            logger.error("请设置这些环境变量后再运行测试")
            return
        
        logger.info("开始测试增强型网络搜索工具...")
        
        # 创建一个简单的Agent实例，直接使用OpenAI Agent库
        agent = Agent(
            name="搜索助手",
            instructions="""
            你是一个专业的搜索助手，擅长使用增强型网络搜索工具获取信息。
            当用户提出问题时，你应该：
            1. 使用增强型网络搜索工具查找相关信息
            2. 分析和总结搜索结果
            3. 提供清晰、准确的回答
            4. 引用信息来源
            
            请始终使用中文回答问题。
            """,
            model="gpt-4o",
            tools=["enhanced_web_search"]  # 使用增强型网络搜索工具
        )
        
        # 测试查询
        test_queries = [
            "数字人技术的最新进展是什么？",
            "中国2024年的经济发展趋势如何？",
            "人工智能在医疗领域的应用有哪些？"
        ]
        
        # 创建结果目录
        results_dir = Path(__file__).parent.parent / "test_outputs" / "enhanced_search"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # 执行测试查询
        for i, query in enumerate(test_queries, 1):
            logger.info(f"测试查询 {i}/{len(test_queries)}: {query}")
            
            # 使用trace记录执行过程
            with trace(f"搜索查询: {query}"):
                # 运行Agent
                result = await Runner.run(agent, query)
                
                # 输出结果
                logger.info(f"查询完成: {query}")
                logger.info(f"回复长度: {len(result.final_output)} 字符")
                
                # 保存结果到文件
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                result_file = results_dir / f"result_{i}_{timestamp}.json"
                
                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "query": query,
                        "response": result.final_output,
                        "run_id": result.run_id,
                        "timestamp": timestamp
                    }, f, ensure_ascii=False, indent=2)
                
                logger.info(f"结果已保存到: {result_file}")
                logger.info("-" * 80)
                
                # 打印回复内容
                print(f"\n查询: {query}\n")
                print(f"回复:\n{result.final_output}\n")
                print("-" * 80)
                
                # 等待一段时间，避免API限制
                await asyncio.sleep(2)
        
        logger.info("增强型网络搜索工具测试完成")
        
    except Exception as e:
        logger.error(f"测试出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_enhanced_search()) 