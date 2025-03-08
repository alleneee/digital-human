# -*- coding: utf-8 -*-
'''
注册Kokoro TTS引擎
'''

from ..builder import TTSEngines
from .kokoro_tts import KokoroTTSEngine

# 注册Kokoro TTS引擎
@TTSEngines.register("kokoro")
class KokoroTTSWrapper(KokoroTTSEngine):
    """
    注册Kokoro TTS引擎到引擎系统
    """
    def __init__(self, config):
        """
        初始化Kokoro TTS引擎包装器
        
        参数:
            config: 引擎配置
        """
        # 转换配置格式
        engine_config = {
            'lang_code': getattr(config, 'LANG_CODE', 'z'),
            'default_voice': getattr(config, 'DEFAULT_VOICE', 'zh_f1'),
            'speed': getattr(config, 'SPEED', 1.0),
            'voice_tensor_path': getattr(config, 'VOICE_TENSOR_PATH', None),
            'temperature': getattr(config, 'TEMPERATURE', 0.6)
        }
        
        # 初始化引擎
        super().__init__(config=engine_config)
