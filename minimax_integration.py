"""
MiniMax API 集成模块
提供与MiniMax大模型API的集成，包括文本生成、语音识别、语音合成等功能
支持最新的T2A_V2版本，并增加流式处理能力
"""

import os
import json
import logging
import asyncio
import aiohttp
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, AsyncGenerator, Callable
from dotenv import load_dotenv
from utils.audio_utils import compute_content_hash, get_cached_audio, save_to_cache, split_text_into_sentences

# 配置日志
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()
MINIMAX_GROUP_ID = os.getenv("MINIMAX_GROUP_ID", "")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")

# MiniMax API端点
LLM_API_ENDPOINT = "https://api.minimax.chat/v1/text/chatcompletion_v2"
TTS_API_ENDPOINT = "https://api.minimax.chat/v1/t2a_v2"
TTS_LEGACY_API_ENDPOINT = "https://api.minimax.chat/v1/text_to_speech"  # 旧版本TTS API

# 常量定义
DEFAULT_LLM_MODEL = "MiniMax-Text-01"  # MiniMax对话大模型
DEFAULT_TTS_MODEL = "speech-01"  # 语音合成模型
DEFAULT_VOICE_TYPE = "general"  # 语音类型
DEFAULT_VOICE = "female-general-24"  # 默认语音角色
DEFAULT_SAMPLE_RATE = 24000  # 默认采样率


class MinimaxIntegration:
    """MiniMax API集成类，提供对MiniMax各项API的调用封装"""

    def __init__(self, group_id: str = MINIMAX_GROUP_ID, api_key: str = MINIMAX_API_KEY):
        """
        初始化MiniMax集成
        
        参数:
            group_id: MiniMax组织ID
            api_key: MiniMax API密钥
        """
        self.group_id = group_id
        self.api_key = api_key
        self.session = None

        # 验证必要的配置
        if not self.group_id or not self.api_key:
            logger.warning("MiniMax GroupID或API Key未配置，请设置环境变量MINIMAX_GROUP_ID和MINIMAX_API_KEY")

    async def ensure_session(self):
        """确保aiohttp会话已创建"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def chat_completion(self,
                              messages: List[Dict[str, str]],
                              model: str = DEFAULT_LLM_MODEL,
                              temperature: float = 0.7,
                              max_tokens: int = 800,
                              top_p: float = 0.9,
                              system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        调用MiniMax LLM API进行对话生成
        
        参数:
            messages: 对话历史消息，格式为[{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好！有什么可以帮助你的？"}]
            model: 使用的模型名称
            temperature: 温度参数，控制生成的随机性
            max_tokens: 最大生成的token数
            top_p: 核采样参数
            system_prompt: 系统提示词，定义助手的角色和行为
            
        返回:
            API响应结果
        """
        try:
            session = await self.ensure_session()

            if system_prompt is None:
                system_prompt = "你是一个友好的AI数字人助手,名叫小智。请用自然、温暖、亲切的语气回答问题。"

            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
                "stream": False,
                "reply_constraints": {
                    "sender_type": "BOT",
                    "sender_name": "小智"
                },
                "bot_setting": [
                    {
                        "bot_name": "小智",
                        "content": system_prompt
                    }
                ]
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "X-Minimax-Group-Id": self.group_id
            }

            logger.debug(f"发送MiniMax LLM请求: {json.dumps(payload, ensure_ascii=False)}")

            async with session.post(LLM_API_ENDPOINT,
                                    headers=headers,
                                    json=payload) as response:
                status = response.status
                response_json = await response.json()

                logger.debug(
                    f"MiniMax LLM响应状态: {status}, 响应内容: {json.dumps(response_json, ensure_ascii=False)}")

                if status != 200:
                    logger.error(f"MiniMax LLM请求失败: {status} - {response_json}")
                    return {
                        "success": False,
                        "status_code": status,
                        "error": response_json
                    }

                # 检查响应中的base_resp错误信息
                if "base_resp" in response_json and response_json["base_resp"].get("status_code", 0) != 0:
                    error_msg = response_json["base_resp"].get("status_msg", "未知错误")
                    logger.error(f"MiniMax LLM API返回错误: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "raw_response": response_json
                    }

                # 提取回复内容
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    content = response_json["choices"][0]["message"]["content"]
                    return {
                        "success": True,
                        "reply": content,
                        "raw_response": response_json
                    }
                else:
                    logger.warning(f"MiniMax LLM响应中没有发现回复内容: {response_json}")
                    return {
                        "success": False,
                        "error": "没有生成回复内容",
                        "raw_response": response_json
                    }

        except Exception as e:
            logger.error(f"调用MiniMax LLM API出错: {e}")
            return {
                "success": False,
                "error": str(e)
            }



    async def text_to_speech(self,
                             text: str,
                             voice_id: str = DEFAULT_VOICE,
                             voice_type: str = DEFAULT_VOICE_TYPE,
                             speed: float = 1.0,
                             sample_rate: int = DEFAULT_SAMPLE_RATE,
                             use_cache: bool = True,
                             api_version: str = "T2A_V2",
                             style: str = "general") -> Dict[str, Any]:
        """
        调用MiniMax TTS API进行语音合成
        
        参数:
            text: 需要合成语音的文本
            voice_id: 语音ID
            voice_type: 语音类型 (general, character, clone) - 仅适用于T2A_V2
            speed: 语速，0.5-2.0，1.0为标准语速
            sample_rate: 采样率 - 仅适用于T2A_V2
            use_cache: 是否使用缓存
            api_version: API版本，可选 "T2A_V2" 或 "T2A"
            style: 风格 - 仅适用于T2A_V2
            
        返回:
            合成结果，包含音频数据和格式信息
        """
        try:
            # 如果启用缓存，先检查缓存
            if use_cache:
                # 构建缓存参数
                cache_params = {
                    "speed": speed,
                    "api_version": api_version
                }
                
                if api_version == "T2A_V2":
                    cache_params.update({
                        "sample_rate": sample_rate,
                        "voice_type": voice_type,
                        "style": style
                    })
                
                cache_key = compute_content_hash(text, voice_id, cache_params)
                cached_audio = await get_cached_audio(cache_key)
                
                if cached_audio:
                    return {
                        "success": True,
                        "audio_data": cached_audio,
                        "format": "mp3",
                        "from_cache": True
                    }
            
            session = await self.ensure_session()
            
            # 根据API版本选择不同的端点和参数
            if api_version == "T2A_V2":
                endpoint = TTS_API_ENDPOINT
                
                payload = {
                    "model_name": DEFAULT_TTS_MODEL,
                    "text": text,
                    "type": voice_type,
                    "voice_id": voice_id,
                    "config": {
                        "audio_sample_rate": sample_rate,
                        "speed": speed,
                        "style": style
                    }
                }
            else:  # 旧版本T2A
                endpoint = TTS_LEGACY_API_ENDPOINT
                
                payload = {
                    "text": text,
                    "voice_id": voice_id,
                    "model_id": DEFAULT_TTS_MODEL,
                    "speed": speed,
                    "vol": 1.0,  # 默认音量
                    "pitch": 0    # 默认音调
                }
            
            # 构建完整URL，包含group_id
            url = f"{endpoint}?GroupId={self.group_id}"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "X-Minimax-Group-Id": self.group_id
            }

            logger.debug(f"发送MiniMax TTS请求: {json.dumps(payload, ensure_ascii=False)}")

            async with session.post(url,
                                    headers=headers,
                                    json=payload) as response:
                status = response.status
                
                if status != 200:
                    try:
                        response_json = await response.json()
                        logger.error(f"MiniMax TTS请求失败: {status} - {response_json}")
                        return {
                            "success": False,
                            "status_code": status,
                            "error": response_json
                        }
                    except:
                        error_text = await response.text()
                        logger.error(f"MiniMax TTS请求失败: {status} - {error_text}")
                        return {
                            "success": False,
                            "status_code": status,
                            "error": error_text
                        }
                
                # 根据API版本处理不同的响应格式
                if api_version == "T2A_V2":
                    # 新版API返回JSON，从中提取audio_data字段
                    result = await response.json()
                    logger.debug(f"MiniMax TTS API响应: {result}")
                    
                    # 检查响应中的错误信息
                    if "base_resp" in result and result["base_resp"].get("status_code", 0) != 0:
                        error_msg = result["base_resp"].get("status_msg", "未知错误")
                        logger.error(f"MiniMax TTS API返回错误: {error_msg}")
                        return {
                            "success": False,
                            "error": error_msg,
                            "raw_response": result
                        }
                    
                    # 提取音频数据
                    if "audio_data" in result:
                        audio_data = base64.b64decode(result["audio_data"])
                        
                        # 保存到缓存
                        if use_cache:
                            await save_to_cache(cache_key, audio_data)
                        
                        return {
                            "success": True,
                            "audio_data": audio_data,
                            "format": "mp3",  # 新版API总是返回MP3
                            "sample_rate": sample_rate,
                            "from_cache": False
                        }
                    else:
                        logger.warning(f"MiniMax TTS响应中没有音频数据: {result}")
                        return {
                            "success": False,
                            "error": "没有生成音频数据",
                            "raw_response": result
                        }
                        
                else:  # 旧版API
                    # 检查是否是JSON错误响应
                    content_type = response.headers.get('Content-Type', '')
                    if 'application/json' in content_type:
                        result = await response.json()
                        logger.debug(f"MiniMax TTS返回JSON: {result}")
                        
                        if "base64_audio" in result:
                            audio_data = base64.b64decode(result["base64_audio"])
                            
                            # 保存到缓存
                            if use_cache:
                                await save_to_cache(cache_key, audio_data)
                                
                            return {
                                "success": True,
                                "audio_data": audio_data,
                                "format": "mp3",
                                "from_cache": False
                            }
                        else:
                            return {
                                "success": False,
                                "error": "API返回的JSON中没有音频数据",
                                "raw_response": result
                            }
                    else:
                        # 直接获取音频数据
                        audio_data = await response.read()
                        
                        # 检查音频数据是否合理
                        if len(audio_data) < 100:  # 设置一个合理的最小阈值
                            try:
                                # 尝试解析为JSON，看是否是错误响应
                                error_json = json.loads(audio_data)
                                logger.error(f"MiniMax TTS返回错误: {error_json}")
                                return {
                                    "success": False,
                                    "error": f"API返回错误: {error_json}"
                                }
                            except:
                                # 不是JSON，记录原始数据
                                logger.error(f"MiniMax TTS返回的数据太小: {len(audio_data)} 字节, 内容: {audio_data}")
                                return {
                                    "success": False,
                                    "error": f"返回的音频数据太小: {len(audio_data)} 字节"
                                }
                        
                        # 保存到缓存
                        if use_cache:
                            await save_to_cache(cache_key, audio_data)
                        
                        logger.debug(f"MiniMax TTS响应成功，音频大小: {len(audio_data)} 字节")
                        
                        return {
                            "success": True,
                            "audio_data": audio_data,
                            "format": "mp3",  # 假设返回MP3
                            "from_cache": False
                        }

        except Exception as e:
            logger.error(f"调用MiniMax TTS API出错: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def text_to_speech_streaming(self,
                                     text: str,
                                     voice_id: str = DEFAULT_VOICE,
                                     voice_type: str = DEFAULT_VOICE_TYPE,
                                     speed: float = 1.0,
                                     sample_rate: int = DEFAULT_SAMPLE_RATE,
                                     use_cache: bool = True,
                                     max_chunk_size: int = 200,
                                     callback: Optional[Callable[[bytes, str], None]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式调用MiniMax TTS API进行语音合成
        
        参数:
            text: 需要合成语音的文本
            voice_id: 语音ID
            voice_type: 语音类型 (general, character, clone)
            speed: 语速，0.5-2.0，1.0为标准语速
            sample_rate: 采样率
            use_cache: 是否使用缓存
            max_chunk_size: 切分文本的最大字符数
            callback: 可选的回调函数，用于接收音频数据和描述
            
        返回:
            异步生成器，生成音频数据块
        """
        # 将文本切分成片段
        text_chunks = split_text_into_sentences(text, max_chunk_size)
        logger.info(f"文本被切分为 {len(text_chunks)} 个片段")
        
        for i, chunk in enumerate(text_chunks):
            if not chunk.strip():
                continue
                
            logger.info(f"处理第 {i+1}/{len(text_chunks)} 个文本片段: {chunk[:30]}...")
            
            result = await self.text_to_speech(
                text=chunk,
                voice_id=voice_id,
                voice_type=voice_type,
                speed=speed,
                sample_rate=sample_rate,
                use_cache=use_cache,
                api_version="T2A_V2",  # 流式处理总是使用最新版API
                style="general"
            )
            
            if result["success"] and "audio_data" in result:
                # 如果提供了回调函数，调用它
                if callback:
                    await callback(result["audio_data"], chunk)
                
                yield {
                    "success": True,
                    "audio_data": result["audio_data"],
                    "format": result.get("format", "mp3"),
                    "chunk_index": i,
                    "total_chunks": len(text_chunks),
                    "text": chunk,
                    "from_cache": result.get("from_cache", False)
                }
            else:
                error = result.get("error", "未知错误")
                logger.error(f"片段 {i+1} 处理失败: {error}")
                yield {
                    "success": False,
                    "error": error,
                    "chunk_index": i,
                    "total_chunks": len(text_chunks),
                    "text": chunk
                }


# 单例模式，确保只创建一个实例
_minimax_instance = None


def get_minimax_integration() -> MinimaxIntegration:
    """获取MiniMax集成实例"""
    global _minimax_instance
    if _minimax_instance is None:
        _minimax_instance = MinimaxIntegration()
    return _minimax_instance


# 用于测试的辅助函数


async def test_minimax_integration():
    """测试MiniMax集成功能"""
    minimax = get_minimax_integration()

    try:
        # 测试对话生成
        messages = [
            {"role": "user", "content": "你好，请介绍一下自己"}
        ]

        chat_result = await minimax.chat_completion(messages)
        print(f"对话生成结果: {chat_result}")

        if chat_result.get("success"):
            # 测试普通语音合成
            tts_result = await minimax.text_to_speech(chat_result["reply"])
            print(f"语音合成成功: {tts_result.get('success')}, 音频大小: {len(tts_result.get('audio_data', b''))} 字节")

            # 可以将音频保存到文件进行测试
            if tts_result.get("success"):
                with open("test_tts_output.mp3", "wb") as f:
                    f.write(tts_result["audio_data"])
                print("语音文件已保存到 test_tts_output.mp3")
                
            # 测试流式语音合成
            print("\n测试流式语音合成...")
            long_text = "这是一段较长的文本，用于测试流式语音合成功能。将长文本分成多个句子，逐句合成并返回。这样可以实现边合成边播放的效果，大大减少用户等待的时间。用户体验会更好。流式处理非常适合需要实时反馈的场景。"
            total_audio = b""
            
            async for chunk_result in minimax.text_to_speech_streaming(long_text):
                if chunk_result["success"]:
                    print(f"接收到第 {chunk_result['chunk_index']+1}/{chunk_result['total_chunks']} 个音频片段")
                    print(f"文本: {chunk_result['text']}")
                    print(f"音频大小: {len(chunk_result['audio_data'])} 字节")
                    print(f"是否来自缓存: {chunk_result['from_cache']}\n")
                    total_audio += chunk_result["audio_data"]
                else:
                    print(f"片段处理失败: {chunk_result.get('error')}")
                
            # 保存完整的流式合成音频
            if total_audio:
                with open("test_streaming_output.mp3", "wb") as f:
                    f.write(total_audio)
                print("流式合成音频已保存到 test_streaming_output.mp3")

    except Exception as e:
        print(f"测试过程中出现错误: {e}")
    finally:
        await minimax.close()


# 如果直接运行此文件，执行测试
if __name__ == "__main__":
    asyncio.run(test_minimax_integration())
