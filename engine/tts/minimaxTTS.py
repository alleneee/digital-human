# -*- coding: utf-8 -*-
'''
MiniMax TTS 引擎实现
'''

from ..builder import TTSEngines
from ..engineBase import BaseEngine
from typing import List, Optional, Union
from yacs.config import CfgNode as CN
import logging
from utils import TextMessage, AudioMessage, AudioFormatType
import aiohttp
import json
import base64

# 配置日志
logger = logging.getLogger(__name__)

__all__ = ["MiniMaxAPI"]


@TTSEngines.register()
class MiniMaxAPI(BaseEngine):
    """
    MiniMax TTS API
    """
    def checkKeys(self) -> List[str]:
        """
        检查必要的配置项
        
        返回:
            必要的配置项列表
        """
        return ["NAME", "API_KEY", "GROUP_ID"]
    
    def setup(self):
        """
        设置 MiniMax 客户端
        """
        try:
            self.api_key = self.cfg.API_KEY
            self.group_id = self.cfg.GROUP_ID
            self.api_version = self.cfg.get("API_VERSION", "T2A_V2")  # 默认使用V2版本
            
            # 根据API版本设置不同的基础URL
            if self.api_version == "T2A_V2":
                self.base_url = "https://api.minimax.chat/v1/t2a_v2"
            else:  # 老版本T2A
                self.base_url = "https://api.minimax.chat/v1/text_to_speech"
            
            # 设置默认选项
            self.options = {}
            
            # T2A版本的特定参数
            if self.api_version == "T2A":
                self.options.update({
                    "voice_id": self.cfg.get("VOICE_ID", "male-qn-qingse"),
                    "speed": self.cfg.get("SPEED", 1.0),
                    "vol": self.cfg.get("VOLUME", 1.0),
                    "pitch": self.cfg.get("PITCH", 0)
                })
            # T2A_V2版本的特定参数
            else:
                self.options.update({
                    "voice_type": self.cfg.get("VOICE_TYPE", "general"),  # general, character, clone
                    "voice_id": self.cfg.get("VOICE_ID", "female-general-24"),  # 新版本的voice_id
                    "audio_sample_rate": self.cfg.get("SAMPLE_RATE", 24000),
                    "speed": self.cfg.get("SPEED", 1.0),
                    "style": self.cfg.get("STYLE", "general")
                })
            
            logger.info(f"[MiniMaxTTS] 客户端设置成功，API 版本 {self.api_version}")
        except Exception as e:
            logger.error(f"[MiniMaxTTS] 设置失败: {str(e)}")
            raise RuntimeError(f"[MiniMaxTTS] 设置失败: {str(e)}")
    
    async def run(self, input: Union[TextMessage, List[TextMessage]], **kwargs) -> Optional[AudioMessage]:
        """
        运行 MiniMax TTS
        
        参数:
            input: TextMessage 或 List[TextMessage]
            **kwargs: MiniMax TTS 的其他参数
                T2A版本参数:
                  voice_id: str, 声音ID
                  speed: float, 语速 (0.5-2.0)
                  vol: float, 音量 (0.0-2.0)
                  pitch: int, 音调 (-12 to 12)
                
                T2A_V2版本参数:
                  voice_type: str, 声音类型 (general, character, clone)
                  voice_id: str, 声音ID
                  audio_sample_rate: int, 采样率
                  speed: float, 语速 (0.5-2.0)
                  style: str, 风格
            
        返回:
            AudioMessage: 合成的音频
        """
        if isinstance(input, List):
            if len(input) == 0:
                logger.warning(f"[MiniMaxTTS] 输入列表为空")
                return None
            # 如果是列表，则连接所有文本
            text = " ".join([msg.data for msg in input if isinstance(msg, TextMessage)])
        elif isinstance(input, TextMessage):
            text = input.data
        else:
            logger.warning(f"[MiniMaxTTS] 输入不是 TextMessage")
            return None
        
        if not text:
            logger.warning(f"[MiniMaxTTS] 文本数据为空")
            return None
        
        try:
            # 构建请求选项
            options = self.options.copy()
            
            # 覆盖默认参数
            for key in kwargs:
                if key in options:
                    options[key] = kwargs[key]
            
            # 构建完整URL，包含group_id
            url = f"{self.base_url}?GroupId={self.group_id}"
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 根据API版本构建不同的请求体
            if self.api_version == "T2A_V2":
                payload = {
                    "model_name": "speech-01",  # 固定值
                    "text": text,
                    "type": options.get("voice_type", "general"),
                    "voice_id": options.get("voice_id", "female-general-24"),
                    "config": {
                        "audio_sample_rate": options.get("audio_sample_rate", 24000),
                        "speed": options.get("speed", 1.0),
                        "style": options.get("style", "general")
                    }
                }
            else:  # T2A版本
                payload = {
                    "text": text,
                    "voice_id": options.get("voice_id", "male-qn-qingse"),
                    "model_id": "speech-01",
                    "speed": options.get("speed", 1.0),
                    "vol": options.get("vol", 1.0),
                    "pitch": options.get("pitch", 0)
                }
            
            # 发送请求
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"[MiniMaxTTS] API 请求失败: {response.status}, {error_text}")
                        return None
                    
                    result = await response.json()
                    
                    # 检查API返回
                    audio_data = None
                    # 不同版本API返回的音频字段名不同
                    if self.api_version == "T2A_V2":
                        if "audio_data" in result:
                            audio_data = base64.b64decode(result["audio_data"])
                        else:
                            logger.error(f"[MiniMaxTTS] 响应中没有 audio_data (T2A_V2): {result}")
                            return None
                    else:  # T2A版本
                        if "base64_audio" in result:
                            audio_data = base64.b64decode(result["base64_audio"])
                        else:
                            logger.error(f"[MiniMaxTTS] 响应中没有 base64_audio (T2A): {result}")
                            return None
                    
                    # 确定采样率
                    sample_rate = 16000
                    if self.api_version == "T2A_V2":
                        sample_rate = options.get("audio_sample_rate", 24000)
                    
                    # 创建音频消息 (MiniMax返回的是mp3格式)
                    message = AudioMessage(
                        data=audio_data,
                        desc=text,
                        format=AudioFormatType.MP3,  # MiniMax返回MP3格式
                        sampleRate=sample_rate,
                        sampleWidth=2      # 默认值
                    )
                    return message
                
        except Exception as e:
            logger.error(f"[MiniMaxTTS] 运行失败: {str(e)}")
            return None
