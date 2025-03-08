# -*- coding: utf-8 -*-
'''
TTS 引擎模块
'''

from .ttsFactory import TTSFactory

# 导入引擎注册模块，确保引擎被注册
# EdgeTTS 已经直接在文件中注册
from .edgeTTS import EdgeAPI
from .register_kokoro import KokoroTTSWrapper

__all__ = ["TTSFactory"]
