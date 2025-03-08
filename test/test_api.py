# -*- coding: utf-8 -*-
'''
测试API接口
'''

import asyncio
import aiohttp
import logging
from pathlib import Path
import base64
import json
import argparse

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_health_check(base_url: str = "http://localhost:8000"):
    """测试健康检查接口"""
    try:
        url = f"{base_url}/health"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                result = await response.json()
                logger.info(f"健康检查接口响应: {result}")
                return result
    except Exception as e:
        logger.error(f"健康检查接口测试失败: {str(e)}")
        return None

async def test_text_chat(text: str, base_url: str = "http://localhost:8000"):
    """测试文本聊天接口"""
    try:
        url = f"{base_url}/api/chat/text"
        data = {"text": text}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"文本聊天接口响应: {result}")
                    
                    # 如果有音频数据，保存到文件
                    if "audio" in result and result["audio"]:
                        audio_data = base64.b64decode(result["audio"])
                        output_dir = Path("test_outputs")
                        output_dir.mkdir(exist_ok=True)
                        
                        output_path = output_dir / "api_text_chat_output.wav"
                        with open(output_path, "wb") as f:
                            f.write(audio_data)
                            
                        logger.info(f"已保存文本聊天响应音频到: {output_path}")
                    
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"文本聊天接口请求失败: {response.status}, {error_text}")
                    return None
    except Exception as e:
        logger.error(f"文本聊天接口测试失败: {str(e)}")
        return None

async def test_audio_chat(audio_path: str, base_url: str = "http://localhost:8000"):
    """测试音频聊天接口"""
    try:
        url = f"{base_url}/api/chat/audio"
        
        # 读取音频文件
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        
        # Base64编码
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        
        # 准备请求数据
        data = {
            "audio": audio_base64,
            "format": Path(audio_path).suffix[1:].lower()  # 文件扩展名作为格式
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"音频聊天接口响应: {result}")
                    
                    # 如果有音频数据，保存到文件
                    if "audio" in result and result["audio"]:
                        audio_data = base64.b64decode(result["audio"])
                        output_dir = Path("test_outputs")
                        output_dir.mkdir(exist_ok=True)
                        
                        output_path = output_dir / "api_audio_chat_output.wav"
                        with open(output_path, "wb") as f:
                            f.write(audio_data)
                            
                        logger.info(f"已保存音频聊天响应音频到: {output_path}")
                    
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"音频聊天接口请求失败: {response.status}, {error_text}")
                    return None
    except Exception as e:
        logger.error(f"音频聊天接口测试失败: {str(e)}")
        return None

async def test_asr(audio_path: str, base_url: str = "http://localhost:8000"):
    """测试ASR接口"""
    try:
        url = f"{base_url}/api/asr"
        
        # 读取音频文件
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        
        # Base64编码
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        
        # 准备请求数据
        data = {
            "audio": audio_base64,
            "format": Path(audio_path).suffix[1:].lower()  # 文件扩展名作为格式
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"ASR接口响应: {result}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"ASR接口请求失败: {response.status}, {error_text}")
                    return None
    except Exception as e:
        logger.error(f"ASR接口测试失败: {str(e)}")
        return None

async def test_tts(text: str, base_url: str = "http://localhost:8000"):
    """测试TTS接口"""
    try:
        url = f"{base_url}/api/tts"
        data = {"text": text}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"TTS接口响应: {result}")
                    
                    # 保存音频数据
                    if "audio" in result and result["audio"]:
                        audio_data = base64.b64decode(result["audio"])
                        output_dir = Path("test_outputs")
                        output_dir.mkdir(exist_ok=True)
                        
                        output_path = output_dir / "api_tts_output.wav"
                        with open(output_path, "wb") as f:
                            f.write(audio_data)
                            
                        logger.info(f"已保存TTS接口响应音频到: {output_path}")
                    
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"TTS接口请求失败: {response.status}, {error_text}")
                    return None
    except Exception as e:
        logger.error(f"TTS接口测试失败: {str(e)}")
        return None

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="测试数字人API接口")
    parser.add_argument("--base_url", type=str, default="http://localhost:8000", help="API基础URL")
    parser.add_argument("--test", type=str, choices=["health", "text", "audio", "asr", "tts", "all"], 
                        default="all", help="要测试的接口")
    parser.add_argument("--text", type=str, default="你好，我是谁？", help="文本聊天或TTS的输入文本")
    parser.add_argument("--audio", type=str, default="test_outputs/advanced_audio_简短语音.mp3", 
                       help="音频聊天或ASR的输入音频文件路径")
    
    args = parser.parse_args()
    
    # 创建输出目录
    Path("test_outputs").mkdir(exist_ok=True)
    
    # 运行测试
    loop = asyncio.get_event_loop()
    
    if args.test == "health" or args.test == "all":
        print("\n===== 测试健康检查接口 =====")
        result = loop.run_until_complete(test_health_check(args.base_url))
        
    if args.test == "text" or args.test == "all":
        print("\n===== 测试文本聊天接口 =====")
        result = loop.run_until_complete(test_text_chat(args.text, args.base_url))
        
    if args.test == "audio" or args.test == "all":
        print("\n===== 测试音频聊天接口 =====")
        result = loop.run_until_complete(test_audio_chat(args.audio, args.base_url))
        
    if args.test == "asr" or args.test == "all":
        print("\n===== 测试ASR接口 =====")
        result = loop.run_until_complete(test_asr(args.audio, args.base_url))
        
    if args.test == "tts" or args.test == "all":
        print("\n===== 测试TTS接口 =====")
        result = loop.run_until_complete(test_tts(args.text, args.base_url))
