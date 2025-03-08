# -*- coding: utf-8 -*-
'''
测试TTS引擎
'''

import asyncio
import logging
import os
from pathlib import Path
from engine.tts.edgeTTS import EdgeAPI
from yacs.config import CfgNode as CN
from utils import TextMessage, AudioMessage

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_edge_tts():
    """测试Edge TTS引擎"""
    try:
        logger.info("测试Edge TTS引擎...")
        
        # 创建Edge TTS配置
        cfg = CN()
        cfg.NAME = "EdgeAPI"
        cfg.PER = "zh-CN-XiaoxiaoNeural"  # 默认中文女声
        cfg.RATE = "+0%"                  # 正常语速
        cfg.VOL = "+0%"                   # 正常音量 
        cfg.PIT = "+0%"                   # 正常音调
        
        # 初始化Edge TTS对象
        tts = EdgeAPI(cfg)
        
        # 准备测试文本
        test_text = "你好，我是数字人。我正在测试语音合成功能。"
        test_message = TextMessage(data=test_text)
        
        logger.info(f"合成文本: '{test_text}'")
        
        # 调用TTS引擎
        audio_msg = await tts.run(test_message)
        
        if audio_msg and isinstance(audio_msg, AudioMessage):
            # 保存音频文件
            output_dir = Path("test_outputs")
            output_dir.mkdir(exist_ok=True)
            
            output_path = output_dir / "tts_test_output.wav"
            with open(output_path, "wb") as f:
                f.write(audio_msg.data)
                
            logger.info(f"已保存语音合成结果到: {output_path}")
            return output_path
        else:
            logger.error("未能成功生成语音")
            return None
            
    except Exception as e:
        logger.error(f"测试过程出错: {str(e)}")
        return None

if __name__ == "__main__":
    # 运行测试
    result = asyncio.run(test_edge_tts())
    if result:
        print(f"\n语音合成成功，文件保存在: {result}")
    else:
        print("\n测试失败，语音合成未成功")
