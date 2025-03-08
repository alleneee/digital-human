# -*- coding: utf-8 -*-
'''
测试 TTS 引擎
'''

import asyncio
import os
import argparse
from utils.configParser import ConfigParser
from engine.tts import TTSFactory
from utils import TextMessage
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_tts(config_path, text, output_file):
    """
    测试 TTS 引擎
    
    参数:
        config_path: 配置文件路径
        text: 要转换的文本
        output_file: 输出音频文件路径
    """
    try:
        # 加载配置
        config = ConfigParser.load(config_path)
        logger.info(f"加载配置: {config_path}")
        
        # 创建 TTS 引擎
        tts_engine = TTSFactory.create(config)
        logger.info(f"创建 TTS 引擎: {config.NAME}")
        
        # 创建文本消息
        text_message = TextMessage(data=text)
        logger.info(f"文本消息: {text}")
        
        # 运行 TTS 引擎
        logger.info("开始生成音频...")
        audio_message = await tts_engine.run(text_message)
        
        if audio_message:
            # 保存音频文件
            with open(output_file, 'wb') as f:
                f.write(audio_message.data)
            logger.info(f"音频已保存到: {output_file}")
            
            # 输出音频信息
            logger.info(f"音频格式: {audio_message.format.name}")
            logger.info(f"采样率: {audio_message.sampleRate} Hz")
            logger.info(f"采样宽度: {audio_message.sampleWidth} bytes")
            logger.info(f"音频长度: {len(audio_message.data)} bytes")
        else:
            logger.error("生成音频失败")
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)

def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='测试 TTS 引擎')
    parser.add_argument('--config', type=str, required=True, help='TTS 引擎配置文件路径')
    parser.add_argument('--text', type=str, default='你好，这是一个测试。', help='要转换的文本')
    parser.add_argument('--output', type=str, default='output.wav', help='输出音频文件路径')
    
    args = parser.parse_args()
    
    # 运行测试
    asyncio.run(test_tts(args.config, args.text, args.output))

if __name__ == '__main__':
    main()
