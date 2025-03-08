# -*- coding: utf-8 -*-
'''
测试Kokoro TTS引擎
'''

import asyncio
import base64
import sys
import os
import logging

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.tts.kokoro_tts import KokoroTTSEngine
from utils.protocol import TextMessage

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_kokoro_tts():
    """测试Kokoro TTS引擎"""
    logger.info("开始测试Kokoro TTS引擎")
    
    # 创建配置
    config = {
        'lang_code': 'z',  # 中文
        'default_voice': 'zh_f1',
        'speed': 1.0,
    }
    
    # 初始化引擎
    engine = KokoroTTSEngine(config)
    
    # 等待引擎初始化
    initialized = await engine.initialize()
    if not initialized:
        logger.error("Kokoro TTS引擎初始化失败")
        return False
    
    # 测试文本
    cn_text = "欢迎使用Kokoro语音合成引擎，这是一个高质量的开源TTS模型。"
    en_text = "Welcome to Kokoro Text-to-Speech engine, a high-quality open-source TTS model."
    
    # 创建测试输出目录
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_outputs'))
    os.makedirs(output_dir, exist_ok=True)
    
    # 测试中文语音合成
    logger.info(f"测试中文语音合成: {cn_text}")
    cn_message = TextMessage(data=cn_text)
    cn_audio = await engine.synthesize(cn_message, voice_id='zh_f1')
    
    if cn_audio:
        # 保存到文件
        cn_output_path = os.path.join(output_dir, 'kokoro_cn_test.wav')
        with open(cn_output_path, 'wb') as f:
            f.write(cn_audio.data)
        logger.info(f"中文语音合成成功，已保存到: {cn_output_path}")
    else:
        logger.error("中文语音合成失败")
    
    # 测试英文语音合成
    logger.info(f"测试英文语音合成: {en_text}")
    # 为英文切换语言代码和声音
    engine.config['lang_code'] = 'a'  # 英语(美式)
    await engine.initialize()  # 重新初始化以应用新的语言代码
    
    en_message = TextMessage(data=en_text)
    en_audio = await engine.synthesize(en_message, voice_id='en_f1')
    
    if en_audio:
        # 保存到文件
        en_output_path = os.path.join(output_dir, 'kokoro_en_test.wav')
        with open(en_output_path, 'wb') as f:
            f.write(en_audio.data)
        logger.info(f"英文语音合成成功，已保存到: {en_output_path}")
    else:
        logger.error("英文语音合成失败")
    
    # 显示可用声音列表
    voices = engine.get_available_voices()
    logger.info(f"可用的声音列表: {voices}")
    
    return True

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_kokoro_tts())
