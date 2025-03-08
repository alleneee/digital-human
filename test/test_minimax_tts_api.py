"""
根据官方文档测试MiniMax TTS API
文档链接: https://platform.minimaxi.com/document/T2A%20V2?key=66719005a427f0c8a5701643
"""

import os
import json
import asyncio
import aiohttp
import base64
import logging
import re
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Any, List

# 用于修复Base64编码的函数
def fix_base64_padding(encoded_data: str) -> str:
    """修复Base64字符串的填充"""
    # 移除可能的非Base64字符
    encoded_data = re.sub(r'[^A-Za-z0-9+/=]', '', encoded_data)
    # 添加正确的填充
    missing_padding = len(encoded_data) % 4
    if missing_padding:
        encoded_data += '=' * (4 - missing_padding)
    return encoded_data

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()
MINIMAX_GROUP_ID = os.getenv("MINIMAX_GROUP_ID", "")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")

# 测试输出目录
TEST_OUTPUT_DIR = Path("./test_outputs")
TEST_OUTPUT_DIR.mkdir(exist_ok=True)

# API端点
TTS_API_ENDPOINT = "https://api.minimax.chat/v1/t2a_v2"

# 定义常量
DEFAULT_MODEL = "speech-01-turbo"
DEFAULT_VOICE = "female-shaonv"

async def create_test_payload(text: str, voice_id: str = DEFAULT_VOICE) -> Dict[str, Any]:
    """创建测试用的请求参数"""
    return {
        "model": DEFAULT_MODEL,
        "text": text,
        "stream": False,
        "timber_weights": [
            {
                "voice_id": voice_id,
                "weight": 1
            }
        ],
        "voice_setting": {
            "voice_id": "",
            "speed": 1,  # 使用整数而不是浮点数
            "vol": 1,    # 使用整数而不是浮点数
            "pitch": 0,   # 使用整数而不是浮点数
            "emotion": "happy"
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3"
        }
    }

async def test_according_to_docs():
    """根据官方文档测试MiniMax TTS API"""
    logger.info("开始根据官方文档测试MiniMax TTS API...")
    
    # 创建HTTP会话
    async with aiohttp.ClientSession() as session:
        # MiniMax API端点
        endpoint = TTS_API_ENDPOINT
        
        # 测试文本
        test_text = "真正的危险不是计算机开始像人一样思考，而是人开始像计算机一样思考。计算机只是可以帮我们处理一些简单事务。"
        
        # 创建多个测试场景
        test_cases = [
            # 测试1: 使用默认female-shaonv音色
            {
                "name": "默认女声(shaonv)",
                "payload": await create_test_payload(test_text)
            },
            # 测试2: 男声
            {
                "name": "男声(male-qn-qingse)",
                "payload": await create_test_payload(test_text, "male-qn-qingse")
            },
            # 测试3: 多音色混合
            {
                "name": "混合音色",
                "payload": {
                    "model": DEFAULT_MODEL,
                    "text": test_text,
                    "stream": False,
                    "timber_weights": [
                        {"voice_id": "male-qn-qingse", "weight": 1},
                        {"voice_id": "female-shaonv", "weight": 1}
                    ],
                    "voice_setting": {
                        "voice_id": "",
                        "speed": 1,  # 使用整数而不是浮点数
                        "vol": 1,    # 使用整数而不是浮点数
                        "pitch": 0,   # 使用整数而不是浮点数
                        "emotion": "happy"
                    },
                    "audio_setting": {
                        "sample_rate": 32000,
                        "bitrate": 128000,
                        "format": "mp3"
                    }
                }
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
        
            name = test_case["name"]
            payload = test_case["payload"]
            
            # 构建完整URL，使用查询参数添加group_id
            url = f"{endpoint}?GroupId={MINIMAX_GROUP_ID}"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {MINIMAX_API_KEY}"
            }
            
            logger.info(f"测试 {i}/{len(test_cases)} - {name}")
            logger.info(f"请求URL: {url}")
            
            try:
                async with session.post(url,
                                    headers=headers,
                                    json=payload,
                                    timeout=30) as response:
                    status = response.status
                    logger.info(f"测试 {i} - {name} 响应状态码: {status}")
                    
                    if status != 200:
                        try:
                            response_json = await response.json()
                            logger.error(f"测试 {i} - {name} 请求失败: {response_json}")
                        except:
                            response_text = await response.text()
                            logger.error(f"测试 {i} - {name} 请求失败: {response_text[:200]}")
                    else:
                        # 检查内容类型
                        content_type = response.headers.get('Content-Type', '')
                        logger.info(f"测试 {i} - {name} 响应内容类型: {content_type}")
                        
                        if 'application/json' in content_type:
                            result = await response.json()
                            logger.info(f"测试 {i} - {name} 响应头部: {json.dumps(dict(response.headers), ensure_ascii=False)}")
                            
                            # 检查是否包含错误信息
                            if "base_resp" in result and result["base_resp"].get("status_code", 0) != 0:
                                error_msg = result["base_resp"].get("status_msg", "未知错误")
                                logger.error(f"测试 {i} - {name} 错误: {error_msg}")
                                continue
                                
                            logger.info(f"测试 {i} - {name} 响应内容: {json.dumps(result, ensure_ascii=False)[:500]}...")
                        
                            # 检查是否包含 data.audio 字段
                            if "data" in result and "audio" in result["data"]:
                                try:
                                    # 从 data.audio 提取音频数据，并修复Base64填充
                                    fixed_base64 = fix_base64_padding(result["data"]["audio"])
                                    audio_data = base64.b64decode(fixed_base64)
                                    output_path = TEST_OUTPUT_DIR / f"test_tts_output_{i}_{name.replace(' ', '_')}.mp3"
                                    
                                    with open(output_path, "wb") as f:
                                        f.write(audio_data)
                                        
                                    logger.info(f"✓ 测试 {i} - {name} 音频数据已保存到: {output_path}")
                                    found = True
                                except Exception as e:
                                    logger.error(f"解码音频数据时出错: {str(e)}")
                                    # 保存原始数据用于调试
                                    raw_output_path = TEST_OUTPUT_DIR / f"test_tts_raw_{i}_{name.replace(' ', '_')}.txt"
                                    with open(raw_output_path, "w") as f:
                                        f.write(result["data"]["audio"][:1000])  # 只保存前1000个字符
                                    logger.info(f"已保存原始音频数据片段到: {raw_output_path}")
                            else:
                                # 检查其他可能的字段路径
                                paths_to_check = [
                                    ("audio_data",),
                                    ("audio",),
                                    ("base64_audio",),
                                    ("audio_file",)
                                ]
                                
                                found = False
                                for path in paths_to_check:
                                    # 检查平面字段
                                    if path[0] in result:
                                        try:
                                            # 修复Base64填充并解码
                                            fixed_base64 = fix_base64_padding(result[path[0]])
                                            audio_data = base64.b64decode(fixed_base64)
                                            field_name = path[0]
                                            output_path = TEST_OUTPUT_DIR / f"test_tts_output_{i}_{name.replace(' ', '_')}_{field_name}.mp3"
                                            
                                            with open(output_path, "wb") as f:
                                                f.write(audio_data)
                                                
                                            logger.info(f"✓ 测试 {i} - {name} 音频数据({field_name})已保存到: {output_path}")
                                            found = True
                                            break
                                        except Exception as e:
                                            logger.warning(f"解码字段 {path[0]} 时出错: {str(e)}")
                                
                                if not found:
                                    logger.warning(f"测试 {i} - {name} 响应中未找到音频数据")
                                    logger.info(f"响应结构: {result.keys()}")
                                    if "data" in result:
                                        logger.info(f"data 字段内容: {result['data'].keys() if isinstance(result['data'], dict) else 'not a dict'}")
                        else:
                            # 可能是直接返回二进制数据
                            response_bytes = await response.read()
                            output_path = TEST_OUTPUT_DIR / f"test_tts_binary_output_{i}_{name.replace(' ', '_')}.mp3"
                            
                            with open(output_path, "wb") as f:
                                f.write(response_bytes)
                                
                            logger.info(f"✓ 测试 {i} - {name} 二进制响应已保存到: {output_path}")
            
            except Exception as e:
                logger.error(f"测试 {i} - {name} 请求异常: {str(e)}")
            
            # 添加短暂延迟避免请求过快
            await asyncio.sleep(2)
        
        logger.info("MiniMax TTS API测试完成")

if __name__ == "__main__":
    asyncio.run(test_according_to_docs())
