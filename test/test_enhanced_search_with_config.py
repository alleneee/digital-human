#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用项目配置系统测试增强型网络搜索工具
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
from utils.protocol import TextMessage

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_enhanced_search_with_config():
    """使用项目配置系统测试增强型网络搜索工具"""
    try:
        # 确保环境变量已设置
        required_vars = ["OPENAI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_SEARCH_ENGINE_ID", "FIRECRAWL_API_KEY"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            logger.error(f"缺少必要的环境变量: {', '.join(missing_vars)}")
            logger.error("请设置这些环境变量后再运行测试")
            return
        
        logger.info("开始测试增强型网络搜索工具（使用项目配置）...")
        
        # 加载配置
        config_path = Path(__file__).parent.parent / "configs" / "agent.yaml"
        if not config_path.exists():
            logger.error(f"配置文件不存在: {config_path}")
            return
            
        config = load_config(str(config_path))
        
        if not config or not config.AGENT.ENABLED:
            logger.error("Agent功能未启用，请检查配置")
            return
        
        # 创建Agent实例
        agent = AgentFactory.create(config.AGENT)
        
        if not agent:
            logger.error("创建Agent实例失败")
            return
        
        # 测试查询
        test_queries = [
            "数字人技术的最新进展是什么？",
            "中国2024年的经济发展趋势如何？",
            "人工智能在医疗领域的应用有哪些？"
        ]
        
        # 创建结果目录
        results_dir = Path(__file__).parent.parent / "test_outputs" / "enhanced_search_config"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # 执行测试查询
        for i, query in enumerate(test_queries, 1):
            logger.info(f"测试查询 {i}/{len(test_queries)}: {query}")
            
            # 构建上下文
            context = {
                "session_id": f"test_session_{i}",
                "test_mode": True,
                "search_tool": "enhanced_web_search"  # 指示Agent使用增强型搜索工具
            }
            
            # 处理查询
            start_time = datetime.now()
            response = await agent.process(query, conversation_context=context)
            end_time = datetime.now()
            
            # 计算处理时间
            processing_time = (end_time - start_time).total_seconds()
            
            # 输出结果
            logger.info(f"查询完成: {query}")
            logger.info(f"处理时间: {processing_time:.2f} 秒")
            logger.info(f"回复长度: {len(response.text)} 字符")
            
            # 保存结果到文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_file = results_dir / f"result_{i}_{timestamp}.json"
            
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump({
                    "query": query,
                    "response": response.text,
                    "metadata": response.metadata,
                    "processing_time": processing_time,
                    "timestamp": timestamp
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"结果已保存到: {result_file}")
            logger.info("-" * 80)
            
            # 打印回复内容
            print(f"\n查询: {query}\n")
            print(f"回复:\n{response.text}\n")
            print("-" * 80)
            
            # 等待一段时间，避免API限制
            await asyncio.sleep(2)
        
        logger.info("增强型网络搜索工具测试完成（使用项目配置）")
        
    except Exception as e:
        logger.error(f"测试出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_enhanced_search_with_config()) 