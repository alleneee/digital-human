# -*- coding: utf-8 -*-
'''
Edge TTS 引擎实现
'''

from ..builder import TTSEngines
from ..engineBase import BaseEngine
import edge_tts
from typing import List, Optional, Union
import logging
from utils import TextMessage, AudioMessage, AudioFormatType
from utils.audio import mp3ToWav

# 配置日志
logger = logging.getLogger(__name__)

__all__ = ["EdgeAPI"]


@TTSEngines.register("EdgeAPI")
class EdgeAPI(BaseEngine):
    """
    Edge TTS API
    """
    def checkKeys(self) -> List[str]:
        """
        检查必要的配置项
        
        返回:
            必要的配置项列表
        """
        return ["PER", "RATE", "VOL", "PIT"]
    
    async def run(self, input: Union[TextMessage, List[TextMessage]], **kwargs) -> Optional[AudioMessage]:
        """
        运行 Edge TTS
        
        参数:
            input: TextMessage 或 List[TextMessage]
            **kwargs: Edge TTS 的其他参数
                voice: str, 声音名称
                rate: str, 语速 (如 "+10%", "-5%")
                volume: str, 音量 (如 "+10%", "-5%")
                pitch: str, 音调 (如 "+10%", "-5%")
            
        返回:
            AudioMessage: 合成的音频
        """
        try:
            # 处理输入
            if isinstance(input, List):
                if len(input) == 0:
                    logger.warning(f"[EdgeTTS] 输入列表为空")
                    return None
                # 如果是列表，则连接所有文本
                text = " ".join([msg.data for msg in input if isinstance(msg, TextMessage)])
            elif isinstance(input, TextMessage):
                text = input.data
            else:
                logger.warning(f"[EdgeTTS] 输入不是 TextMessage")
                return None
            
            if not text:
                logger.warning(f"[EdgeTTS] 文本数据为空")
                return None
            
            # 获取参数
            voice = self.cfg.PER
            rate = self.cfg.RATE
            volume = self.cfg.VOL
            pitch = self.cfg.PIT
            
            # 覆盖默认参数
            if 'voice' in kwargs and kwargs['voice']:
                voice = kwargs['voice']
            if 'rate' in kwargs and kwargs['rate']:
                rate = kwargs['rate']
            if 'volume' in kwargs and kwargs['volume']:
                volume = kwargs['volume']
            if 'pitch' in kwargs and kwargs['pitch']:
                pitch = kwargs['pitch']
            
            # 创建 Edge TTS 通信对象
            communicate = edge_tts.Communicate(
                text=text, 
                voice=voice,
                rate=rate,
                volume=volume,
                pitch=pitch
            )
            
            # 获取音频数据
            data = b''
            async for message in communicate.stream():
                if message["type"] == "audio":
                    data += message["data"]
            
            if not data:
                logger.warning(f"[EdgeTTS] 生成的音频数据为空")
                return None
            
            # MP3 转 WAV
            wav_data = mp3ToWav(data)
            
            # 创建音频消息
            message = AudioMessage(
                data=wav_data, 
                desc=text,
                format=AudioFormatType.WAV,
                sampleRate=16000,
                sampleWidth=2,
            )
            return message
        except Exception as e:
            logger.error(f"[EdgeTTS] 运行失败: {e}")
            return None
