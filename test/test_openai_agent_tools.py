#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试OpenAI Agent工具调用
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
import json
from datetime import datetime
import argparse
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入OpenAI Agent
from engine.agent.openai_agent import OpenAIAgent

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_openai_agent_tools():
    """测试OpenAI Agent工具调用"""
    # 加载环境变量
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="测试OpenAI Agent工具调用")
    parser.add_argument("--query", type=str, help="用户查询")
    parser.add_argument("--model", type=str, default="gpt-4o", help="OpenAI模型名称")
    parser.add_argument("--output", type=str, help="输出文件路径")
    args = parser.parse_args()
    
    # 检查环境变量
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("缺少必要的环境变量: OPENAI_API_KEY")
        logger.error("请设置这些环境变量后再运行测试")
        return
    
    # 获取查询
    query = args.query
    if not query:
        query = input("请输入用户查询: ")
    
    if not query:
        logger.error("未提供用户查询")
        return
    
    logger.info(f"开始测试OpenAI Agent工具调用...")
    logger.info(f"查询: {query}")
    logger.info(f"模型: {args.model}")
    
    try:
        # 初始化Agent
        agent = OpenAIAgent(
            model=args.model,
            config={
                "tools": {
                    "enable_web_search": True,  # 内置WebSearchTool
                    "enable_custom_search": True,  # 自定义增强型搜索工具
                    "google_results": 5,
                    "detailed_results": 2,
                    "enable_weather": False,
                    "enable_kb_search": False
                }
            }
        )
        
        # 执行查询
        start_time = datetime.now()
        response = await agent.run(query)
        end_time = datetime.now()
        
        # 计算处理时间
        processing_time = (end_time - start_time).total_seconds()
        
        # 输出结果
        logger.info(f"处理完成，耗时: {processing_time:.2f} 秒")
        
        # 保存结果
        if args.output:
            output_path = args.output
        else:
            # 创建输出目录
            output_dir = Path(__file__).parent.parent / "test_outputs" / "openai_agent"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成输出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sanitized_query = "".join(c if c.isalnum() else "_" for c in query[:30])
            output_path = output_dir / f"agent_{sanitized_query}_{timestamp}.txt"
        
        # 写入结果
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"查询: {query}\n")
            f.write(f"时间: {datetime.now().isoformat()}\n")
            f.write(f"处理时间: {processing_time:.2f} 秒\n")
            f.write(f"模型: {args.model}\n")
            f.write("\n" + "=" * 80 + "\n\n")
            f.write(response)
        
        logger.info(f"结果已保存到: {output_path}")
        
        # 打印结果
        print("\n" + "=" * 80)
        print(f"查询: {query}")
        print("=" * 80 + "\n")
        print(response)
        print("\n" + "=" * 80)
        
    except Exception as e:
        logger.error(f"测试出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_openai_agent_tools()) 