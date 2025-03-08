"""
MiniMax TTS API简化测试脚本
专门测试文本到语音转换功能，包含各种参数组合
"""

import os
import json
import asyncio
import aiohttp
import base64
import logging
from dotenv import load_dotenv

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

async def test_minimax_tts():
    """测试MiniMax TTS API"""
    logger.info("开始测试MiniMax TTS API...")
    
    # 创建HTTP会话
    async with aiohttp.ClientSession() as session:
        # MiniMax API端点
        # 尝试两个不同的API端点
        endpoints = [
            "https://api.minimax.chat/v1/t2a_v2",  # 新版TTS API
            "https://api.minimax.chat/v1/text_to_speech"  # 旧版TTS API
        ]
        
        for endpoint in endpoints:
            logger.info(f"测试端点: {endpoint}")
            
            # 构建不同的请求参数组合
            if "t2a_v2" in endpoint:
                payloads = [
                    # 组合1：最基本参数
                    {
                        "model": "speech-01",
                        "text": "这是一个简单的测试文本"
                    },
                    # 组合2：带类型和声音
                    {
                        "model": "speech-01",
                        "text": "这是一个带声音参数的测试",
                        "voice_id": "female-general-24",
                        "type": "general"
                    },
                    # 组合3：完整参数
                    {
                        "model": "speech-01",
                        "text": "这是一个完整参数的测试",
                        "type": "general",
                        "voice_id": "female-general-24",
                        "config": {
                            "audio_sample_rate": 24000,
                            "speed": 1.0,
                            "style": "general"
                        }
                    }
                ]
            else:  # 旧版API
                payloads = [
                    # 旧版API参数
                    {
                        "text": "这是旧版API的测试",
                        "model_id": "speech-01",
                        "voice_id": "female-general-24"
                    },
                    # 旧版API完整参数
                    {
                        "text": "这是旧版API的完整参数测试",
                        "model_id": "speech-01",
                        "voice_id": "female-general-24",
                        "speed": 1.0,
                        "vol": 1.0,
                        "pitch": 0
                    }
                ]
            
            for i, payload in enumerate(payloads):
                # 构建完整URL
                url = f"{endpoint}?GroupId={MINIMAX_GROUP_ID}"
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {MINIMAX_API_KEY}",
                    "X-Minimax-Group-Id": MINIMAX_GROUP_ID
                }
                
                logger.info(f"测试组合 {i+1}: {json.dumps(payload, ensure_ascii=False)}")
                
                try:
                    async with session.post(url,
                                        headers=headers,
                                        json=payload,
                                        timeout=10) as response:
                        status = response.status
                        
                        if status != 200:
                            response_json = await response.json()
                            logger.error(f"请求失败: {status} - {response_json}")
                        else:
                            # 尝试解析响应
                            try:
                                result = await response.json()
                                if "audio_data" in result or "base64_audio" in result:
                                    audio_data_key = "audio_data" if "audio_data" in result else "base64_audio"
                                    audio_data_len = len(result[audio_data_key])
                                    logger.info(f"✓ 成功获取音频数据，Base64长度: {audio_data_len}")
                                else:
                                    logger.warning(f"响应中没有音频数据: {result}")
                            except:
                                response_bytes = await response.read()
                                # 检查是否是二进制音频数据
                                if response.headers.get('Content-Type', '').startswith('audio/'):
                                    logger.info(f"✓ 成功获取二进制音频数据，长度: {len(response_bytes)}字节")
                                else:
                                    logger.warning(f"无法解析响应: {response_bytes[:100]}...")
                
                except Exception as e:
                    logger.error(f"请求异常: {e}")
                
                # 添加间隔防止请求过快
                await asyncio.sleep(1)
            
            # 不同端点之间添加间隔
            await asyncio.sleep(2)
        
        logger.info("MiniMax TTS API测试完成")

if __name__ == "__main__":
    asyncio.run(test_minimax_tts())
