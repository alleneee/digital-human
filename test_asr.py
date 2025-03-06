# -*- coding: utf-8 -*-
'''
测试 ASR 实现
'''

import asyncio
import os
import logging
from utils import config, AudioMessage, AudioFormatType
from engine.asr import ASRFactory

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_asr():
    """
    测试 ASR 引擎
    """
    try:
        # 加载 Deepgram ASR 配置
        config_path = os.path.join(os.path.dirname(__file__), "configs/engines/asr/deepgramAPI.yaml")
        if not os.path.exists(config_path):
            logger.error(f"ASR 配置文件不存在: {config_path}")
            return
            
        logger.info(f"加载 ASR 配置: {config_path}")
        asr_config = config.load_yaml(config_path)
        
        # 创建 ASR 引擎
        logger.info("创建 ASR 引擎")
        asr_engine = ASRFactory.create(asr_config)
        
        # 加载测试音频文件
        test_audio_path = input("请输入测试音频文件路径: ")
        if not os.path.exists(test_audio_path):
            logger.error(f"测试音频文件不存在: {test_audio_path}")
            return
            
        logger.info(f"加载测试音频文件: {test_audio_path}")
        with open(test_audio_path, "rb") as f:
            audio_data = f.read()
            
        # 确定音频格式
        audio_format = AudioFormatType.WAV
        if test_audio_path.endswith(".mp3"):
            audio_format = AudioFormatType.MP3
        elif test_audio_path.endswith(".webm"):
            audio_format = AudioFormatType.WEBM
        elif test_audio_path.endswith(".ogg"):
            audio_format = AudioFormatType.OGG
            
        # 创建音频消息
        audio_message = AudioMessage(
            data=audio_data,
            format=audio_format,
            sampleRate=16000,  # 默认采样率
            sampleWidth=2      # 默认采样宽度
        )
        
        # 调用 ASR 引擎进行转录
        logger.info("开始转录")
        result = await asr_engine.run(audio_message)
        
        if result:
            logger.info(f"转录结果: {result.data}")
        else:
            logger.error("转录失败")
    except Exception as e:
        logger.error(f"测试过程中出现错误: {e}")

if __name__ == "__main__":
    asyncio.run(test_asr())
