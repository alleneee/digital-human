# -*- coding: utf-8 -*-
'''
Deepgram ASR 引擎实现
'''

import asyncio
import json
from typing import List, Optional, Union
from yacs.config import CfgNode as CN
from ..engineBase import BaseEngine
from ..builder import ASREngines
from utils import AudioMessage, TextMessage
import logging

# 配置日志
logger = logging.getLogger(__name__)

@ASREngines.register()
class DeepgramAPI(BaseEngine):
    """
    Deepgram ASR API 实现
    """
    def checkKeys(self) -> List[str]:
        """
        检查必要的配置项
        """
        return ["NAME", "API_KEY"]
    
    def setup(self):
        """
        初始化 Deepgram 客户端
        """
        try:
            from deepgram import DeepgramClient
            self.client = DeepgramClient(self.cfg.API_KEY)
            # 保存支持的选项
            self.options = {
                "language": self.cfg.get("LANGUAGE", "zh-CN"),
                "model": self.cfg.get("MODEL", "nova-2"),
                "smart_format": self.cfg.get("SMART_FORMAT", True),
                "diarize": self.cfg.get("DIARIZE", False),
                "detect_language": self.cfg.get("DETECT_LANGUAGE", False)
            }
            logger.info(f"[DeepgramAPI] 客户端初始化成功")
        except Exception as e:
            logger.error(f"[DeepgramAPI] 初始化失败: {str(e)}")
            raise RuntimeError(f"[DeepgramAPI] 初始化失败: {str(e)}")
    
    async def run(self, input: Union[AudioMessage, List[AudioMessage]], **kwargs) -> Optional[TextMessage]:
        """
        运行 Deepgram ASR 识别
        
        参数:
            input: AudioMessage 或 List[AudioMessage]
            **kwargs: 额外参数，可包括:
                language: 语言代码
                model: 模型名称
                smart_format: 是否启用智能格式化
                diarize: 是否启用说话人分离
                detect_language: 是否启用语言检测
            
        返回:
            TextMessage: 识别结果
        """
        if isinstance(input, List):
            if len(input) == 0:
                logger.warning(f"[DeepgramAPI] 输入列表为空")
                return None
            input = input[0]  # 只处理第一条音频
        
        if not isinstance(input, AudioMessage):
            logger.warning(f"[DeepgramAPI] 输入不是 AudioMessage 类型")
            return None
        
        if len(input.data) == 0:
            logger.warning(f"[DeepgramAPI] 音频数据为空")
            return None
        
        try:
            # 构建请求选项
            options = self.options.copy()
            # 覆盖默认参数
            for key in options.keys():
                if key.lower() in kwargs:
                    options[key] = kwargs[key.lower()]
            
            # 准备音频数据
            audio_data = input.data
            
            # 设置编码和采样率
            if hasattr(input, "sampleWidth"):
                options["encoding"] = "linear16" if input.sampleWidth == 2 else "mulaw"
            if hasattr(input, "sampleRate"):
                options["sample_rate"] = input.sampleRate
            
            # 检测音频格式
            mimetype = None
            if hasattr(input, "format"):
                format_str = str(input.format).lower()
                if format_str == "wav":
                    mimetype = "audio/wav"
                elif format_str == "mp3":
                    mimetype = "audio/mp3"
                elif format_str == "webm":
                    mimetype = "audio/webm"
                elif format_str == "ogg":
                    mimetype = "audio/ogg"
            
            if mimetype:
                options["mimetype"] = mimetype
            
            logger.info(f"[DeepgramAPI] 开始识别，选项: {options}")
            
            # 发送请求到 Deepgram
            response = await self.client.listen.prerecorded.transcribe_audio(
                {"buffer": audio_data},
                options
            )
            
            # 提取结果
            result = response.results
            if result and "channels" in result and len(result["channels"]) > 0:
                # 获取识别结果
                transcription = result["channels"][0]["alternatives"][0]["transcript"]
                if transcription:
                    logger.info(f"[DeepgramAPI] 识别成功: {transcription[:50]}...")
                    return TextMessage(data=transcription)
                else:
                    logger.warning(f"[DeepgramAPI] 识别结果为空")
                    return None
            else:
                logger.warning(f"[DeepgramAPI] Deepgram 未返回结果")
                return None
        except Exception as e:
            logger.error(f"[DeepgramAPI] 识别失败: {str(e)}")
            return None
