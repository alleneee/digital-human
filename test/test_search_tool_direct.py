#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接测试增强型网络搜索工具函数
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
import json
from datetime import datetime
import argparse
from dotenv import load_dotenv  # 添加dotenv导入

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 加载环境变量
load_dotenv()  # 添加这一行来加载.env文件

# 确保使用正确的API密钥
os.environ["GOOGLE_API_KEY"] = "AIzaSyCMwymZYRgEe_VSKkZLDirDOi9X2uJnRX4"
os.environ["GOOGLE_SEARCH_ENGINE_ID"] = "9341ae4a64c3942d5"
os.environ["FIRECRAWL_API_KEY"] = "fc-e78e5fc62c4041a8a082c15d1743cae9"

# 直接导入我们自己实现的工具函数
from engine.agent.tools import enhanced_web_search, _google_search_raw, _select_best_urls, _firecrawl_specific_url

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_search_tool_direct():
    """直接测试增强型网络搜索工具函数"""
    parser = argparse.ArgumentParser(description="直接测试增强型网络搜索工具")
    parser.add_argument("--query", type=str, help="搜索查询")
    parser.add_argument("--google-results", type=int, default=8, help="Google搜索结果数量")
    parser.add_argument("--detailed-results", type=int, default=3, help="详细内容结果数量")
    parser.add_argument("--language", type=str, default="zh-CN", help="搜索语言")
    parser.add_argument("--output", type=str, help="输出文件路径")
    args = parser.parse_args()
    
    # 检查环境变量
    required_vars = ["GOOGLE_API_KEY", "GOOGLE_SEARCH_ENGINE_ID", "FIRECRAWL_API_KEY"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"缺少必要的环境变量: {', '.join(missing_vars)}")
        logger.error("请设置这些环境变量后再运行测试")
        return
    
    # 获取查询
    query = args.query
    if not query:
        query = input("请输入搜索查询: ")
    
    if not query:
        logger.error("未提供搜索查询")
        return
    
    logger.info(f"开始测试增强型网络搜索工具...")
    logger.info(f"查询: {query}")
    logger.info(f"Google结果数: {args.google_results}")
    logger.info(f"详细内容数: {args.detailed_results}")
    logger.info(f"语言: {args.language}")
    
    try:
        # 执行搜索
        start_time = datetime.now()
        
        # 直接调用内部函数进行测试
        google_results = await _google_search_raw(query, args.google_results, args.language)
        logger.info(f"Google搜索结果数量: {len(google_results)}")
        
        selected_urls = _select_best_urls(google_results, args.detailed_results)
        logger.info(f"选择的URL数量: {len(selected_urls)}")
        logger.info(f"选择的URL: {selected_urls}")
        
        # 测试Firecrawl API
        for url in selected_urls[:1]:  # 只测试第一个URL
            logger.info(f"测试Firecrawl API，URL: {url}")
            content = await _firecrawl_specific_url(url)
            logger.info(f"Firecrawl返回内容: {content}")
        
        # 正常执行搜索
        result = await enhanced_web_search(
            query=query,
            num_google_results=args.google_results,
            num_detailed_results=args.detailed_results,
            language=args.language
        )
        end_time = datetime.now()
        
        # 计算处理时间
        processing_time = (end_time - start_time).total_seconds()
        
        # 输出结果
        logger.info(f"搜索完成，耗时: {processing_time:.2f} 秒")
        logger.info(f"结果长度: {len(result)} 字符")
        
        # 保存结果
        if args.output:
            output_path = args.output
        else:
            # 创建输出目录
            output_dir = Path(__file__).parent.parent / "test_outputs" / "search_tool_direct"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成输出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sanitized_query = "".join(c if c.isalnum() else "_" for c in query[:30])
            output_path = output_dir / f"search_{sanitized_query}_{timestamp}.txt"
        
        # 写入结果
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"查询: {query}\n")
            f.write(f"时间: {datetime.now().isoformat()}\n")
            f.write(f"处理时间: {processing_time:.2f} 秒\n")
            f.write("\n" + "=" * 80 + "\n\n")
            f.write(result)
        
        logger.info(f"结果已保存到: {output_path}")
        
        # 打印结果
        print("\n" + "=" * 80)
        print(f"查询: {query}")
        print("=" * 80 + "\n")
        print(result)
        print("\n" + "=" * 80)
        
    except Exception as e:
        logger.error(f"测试出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_search_tool_direct()) 