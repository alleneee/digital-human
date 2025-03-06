# -*- coding: utf-8 -*-
'''
Deepgram TTS 引擎实现
'''

from ..builder import TTSEngines
from ..engineBase import BaseEngine
from typing import List, Optional, Union
from yacs.config import CfgNode as CN
from utils import logger, TextMessage, AudioMessage, AudioFormatType
import logging

# 配置日志
logger = logging.getLogger(__name__)

__all__ = ["DeepgramAPI"]


@TTSEngines.register()
class DeepgramAPI(BaseEngine):
    """
    Deepgram TTS API
    """
    def checkKeys(self) -> List[str]:
        """
        检查必要的配置项
        
        返回:
            必要的配置项列表
        """
        return ["NAME", "API_KEY", "VOICE", "MODEL"]
    
    def setup(self):
        """
        设置 Deepgram 客户端
        """
        try:
            from deepgram import DeepgramClient
            self.client = DeepgramClient(self.cfg.API_KEY)
            self.options = {
                "voice": self.cfg.get("VOICE", "aura"),
                "model": self.cfg.get("MODEL", "aura"),
                "sample_rate": self.cfg.get("SAMPLE_RATE", 16000),
                "encoding": "linear16",
                "container": "wav"
            }
            logger.info(f"[DeepgramTTS] 客户端设置成功")
        except Exception as e:
            logger.error(f"[DeepgramTTS] 设置失败: {str(e)}")
            raise RuntimeError(f"[DeepgramTTS] 设置失败: {str(e)}")
    
    async def run(self, input: Union[TextMessage, List[TextMessage]], **kwargs) -> Optional[AudioMessage]:
        """
        运行 Deepgram TTS
        
        参数:
            input: TextMessage 或 List[TextMessage]
            **kwargs: Deepgram TTS 的其他参数
                voice: str, 声音名称
                model: str, 模型名称
                rate: float, 语速 (0.5-2.0)
                pitch: float, 音调 (-1.0-1.0)
            
        返回:
            AudioMessage: 合成的音频
        """
        if isinstance(input, List):
            if len(input) == 0:
                logger.warning(f"[DeepgramTTS] 输入列表为空")
                return None
            # 如果是列表，则连接所有文本
            text = " ".join([msg.data for msg in input if isinstance(msg, TextMessage)])
        elif isinstance(input, TextMessage):
            text = input.data
        else:
            logger.warning(f"[DeepgramTTS] 输入不是 TextMessage")
            return None
        
        if not text:
            logger.warning(f"[DeepgramTTS] 文本数据为空")
            return None
        
        try:
            # 构建请求选项
            options = self.options.copy()
            
            # 覆盖默认参数
            if "voice" in kwargs:
                options["voice"] = kwargs["voice"]
            if "model" in kwargs:
                options["model"] = kwargs["model"]
            
            # 添加速率和音高控制（如果提供）
            if "rate" in kwargs:
                options["speaking_rate"] = float(kwargs["rate"])
            if "pitch" in kwargs:
                options["pitch"] = float(kwargs["pitch"])
            
            # 发送请求到 Deepgram
            response = await self.client.speak.sync(
                text,
                options
            )
            
            # 获取音频字节数据
            audio_data = response.buffer
            
            if audio_data:
                # 创建音频消息
                message = AudioMessage(
                    data=audio_data,
                    desc=text,
                    format=AudioFormatType.WAV,
                    sampleRate=options.get("sample_rate", 16000),
                    sampleWidth=2  # 16bit
                )
                return message
            else:
                logger.warning(f"[DeepgramTTS] 返回的音频数据为空")
                return None
                
        except Exception as e:
            logger.error(f"[DeepgramTTS] 运行失败: {str(e)}")
            return None
