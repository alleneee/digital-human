# -*- coding: utf-8 -*-
'''
引擎注册构建器
'''

from utils import Registry

# 创建不同类型的引擎注册表
TTSEngines = Registry()  # 文本转语音引擎
ASREngines = Registry()  # 语音识别引擎
LLMEngines = Registry()  # 大语言模型引擎
