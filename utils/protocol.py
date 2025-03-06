# -*- coding: utf-8 -*-
'''
消息协议定义
'''

from enum import Enum
from uuid import uuid4
from typing import Optional
from pydantic import BaseModel, Field

# 支持的音频格式类型
class AudioFormatType(Enum):
    """
    音频格式类型
    """
    MP3 = "mp3"
    WAV = "wav"
    WEBM = "webm"
    OGG = "ogg"

    def __str__(self):
        return str(self.value)

class BaseMessage(BaseModel):
    """
    基础消息协议
    """
    id: str = Field(default_factory=lambda: str(uuid4()))

class AudioMessage(BaseMessage):
    """
    音频消息
    """
    data: bytes
    format: AudioFormatType
    sampleRate: int
    sampleWidth: int
    desc: Optional[str] = None

class TextMessage(BaseMessage):
    """
    文本消息
    """
    data: Optional[str] = None
    desc: Optional[str] = None
