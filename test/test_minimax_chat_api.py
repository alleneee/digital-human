#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import asyncio
import aiohttp
import logging
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Any, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# API配置
MINIMAX_GROUP_ID = os.getenv('MINIMAX_GROUP_ID')
MINIMAX_API_KEY = os.getenv('MINIMAX_API_KEY')
DEFAULT_MODEL = 'MiniMax-Text-01'  # 默认对话模型
API_URL = f"https://api.minimax.chat/v1/text/chatcompletion_v2?GroupId={MINIMAX_GROUP_ID}"

# 确保输出目录存在
TEST_OUTPUT_DIR = Path('test_outputs')
TEST_OUTPUT_DIR.mkdir(exist_ok=True)

async def create_chat_payload(prompt: str) -> Dict[str, Any]:
    """创建对话API请求参数"""
    return {
        "model": DEFAULT_MODEL,
        "messages": [
            {
                "role": "system",
                "name": "MM智能助理", 
                "content": "MM智能助理是一款由MiniMax自研的，没有调用其他产品的接口的大型语言模型。MiniMax是一家中国科技公司，一直致力于进行大模型相关的研究。"
            },
            {
                "role": "user",
                "name": "用户", 
                "content": prompt
            }
        ],
        "stream": True
    }

async def test_chat_completion(prompt: str, test_name: str = "默认对话测试"):
    """测试对话API"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MINIMAX_API_KEY}"
    }
    
    payload = await create_chat_payload(prompt)
    
    logger.info(f"测试: {test_name}")
    logger.info(f"请求URL: {API_URL}")
    logger.info(f"请求参数: {json.dumps(payload, ensure_ascii=False)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=headers, json=payload) as response:
                logger.info(f"测试 - {test_name} 响应状态码: {response.status}")
                logger.info(f"测试 - {test_name} 响应内容类型: {response.content_type}")
                
                # 处理流式响应
                full_response = ""
                response_chunks = []
                
                async for chunk in response.content:
                    chunk_str = chunk.decode('utf-8')
                    
                    # 处理SSE格式的响应
                    if chunk_str.startswith('data: '):
                        chunk_str = chunk_str[6:]  # 去掉 'data: ' 前缀
                    
                    # 有时候会有空行或者心跳消息
                    if chunk_str.strip() and chunk_str.strip() != '[DONE]':
                        try:
                            chunk_data = json.loads(chunk_str)
                            response_chunks.append(chunk_data)
                            
                            # 如果有delta内容，添加到完整响应中
                            if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                                if 'delta' in chunk_data['choices'][0] and 'content' in chunk_data['choices'][0]['delta']:
                                    content = chunk_data['choices'][0]['delta']['content']
                                    full_response += content
                                    print(content, end='', flush=True)  # 实时打印内容
                        except json.JSONDecodeError:
                            logger.warning(f"无法解析JSON: {chunk_str}")
                
                print("\n")  # 换行
                
                # 保存完整响应到文件
                output_path = TEST_OUTPUT_DIR / f"chat_output_{test_name.replace(' ', '_')}.txt"
                with open(output_path, "w", encoding='utf-8') as f:
                    f.write(full_response)
                logger.info(f"✓ 测试 - {test_name} 响应已保存到: {output_path}")
                
                # 保存完整的响应块到JSON文件
                json_output_path = TEST_OUTPUT_DIR / f"chat_output_{test_name.replace(' ', '_')}_full.json"
                with open(json_output_path, "w", encoding='utf-8') as f:
                    json.dump(response_chunks, f, ensure_ascii=False, indent=2)
                logger.info(f"✓ 测试 - {test_name} 完整响应数据已保存到: {json_output_path}")
                
    except Exception as e:
        logger.error(f"测试 - {test_name} 请求异常: {str(e)}")

async def test_according_to_docs():
    """根据官方文档测试MiniMax对话API"""
    logger.info("开始根据官方文档测试MiniMax对话API...")
    
    # 测试用例
    test_cases = [
        {
            "name": "简单问候",
            "prompt": "你好，请介绍一下你自己"
        },
        {
            "name": "知识问答",
            "prompt": "什么是人工智能？请简要介绍一下"
        },
        {
            "name": "创意写作",
            "prompt": "请写一首关于春天的短诗"
        }
    ]
    
    # 执行测试
    for i, test_case in enumerate(test_cases, 1):
        name = test_case["name"]
        prompt = test_case["prompt"]
        
        logger.info(f"测试 {i}/{len(test_cases)} - {name}")
        await test_chat_completion(prompt, name)
        await asyncio.sleep(2)  # 适当延迟，避免API请求过于频繁
    
    logger.info("MiniMax对话API测试完成")

if __name__ == "__main__":
    asyncio.run(test_according_to_docs())
