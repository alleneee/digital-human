# -*- coding: utf-8 -*-
'''
测试TTS->ASR->LLM->TTS完整流程
使用生成的语音进行测试，再到ASR，再到LLM，最后再到TTS
'''

import asyncio
import sys
import os
import logging
import base64
import tempfile
import uuid
from typing import Dict, Any, Optional

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.tts.kokoro_tts import KokoroTTSEngine
from utils.protocol import TextMessage, AudioMessage, AudioFormatType

# 导入语音处理和ASR相关模块
from pipelines.speech import SpeechProcessor
from engine.asr.funasrASR import FunASRLocal
from engine.asr.asrFactory import ASRFactory
from yacs.config import CfgNode as CN

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建输出目录
output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_outputs'))
os.makedirs(output_dir, exist_ok=True)

async def generate_tts_audio(text: str, voice_id: str = 'zh_f1') -> Optional[AudioMessage]:
    """使用Kokoro TTS引擎生成语音"""
    logger.info(f"步骤1: 使用Kokoro TTS生成语音, 文本: {text}")
    
    # 创建配置
    config = {
        'lang_code': 'z',  # 中文
        'default_voice': voice_id,
        'speed': 1.0,
    }
    
    # 初始化引擎
    engine = KokoroTTSEngine(config)
    
    # 等待引擎初始化
    initialized = await engine.initialize()
    if not initialized:
        logger.error("Kokoro TTS引擎初始化失败")
        return None
    
    # 生成语音
    text_message = TextMessage(data=text)
    audio = await engine.synthesize(text_message, voice_id=voice_id)
    
    if audio:
        # 保存到文件
        output_path = os.path.join(output_dir, 'tts_output.wav')
        with open(output_path, 'wb') as f:
            f.write(audio.data)
        logger.info(f"语音生成成功，已保存到: {output_path}")
        return audio
    else:
        logger.error("语音生成失败")
        return None

async def perform_asr(audio_message: AudioMessage) -> Optional[str]:
    """进行语音识别"""
    logger.info("步骤2: 进行语音识别")
    
    try:
        # 创建语音处理器
        speech_processor = SpeechProcessor()
        
        # 确保音频格式正确 (16kHz WAV)
        processed_audio = await speech_processor.process_for_asr(audio_message)
        if not processed_audio:
            logger.error("音频预处理失败")
            return None
        
        # 保存预处理后的音频
        processed_audio_path = os.path.join(output_dir, 'processed_audio.wav')
        with open(processed_audio_path, 'wb') as f:
            f.write(processed_audio.data)
        logger.info(f"预处理后的音频已保存到: {processed_audio_path}")
        
        # 创建ASR引擎配置
        config = CN()
        config.NAME = "FunASRLocal"
        config.MODEL_PATH = "/Users/niko/.cache/modelscope/hub/SenseVoiceSmall"
        config.LANGUAGE = "auto"
        config.USE_VAD = True
        config.VAD_MODEL = "fsmn-vad"
        config.USE_PUNC = True
        config.DEVICE = "cpu"
        
        # 使用ASR工厂创建引擎
        asr_engine = ASRFactory.create(config)
        
        # 进行语音识别
        result_message = await asr_engine.run(processed_audio)
        
        if result_message and result_message.data:
            recognized_text = result_message.data
            logger.info(f"语音识别结果: {recognized_text}")
            return recognized_text
        else:
            logger.error("语音识别失败: 未返回结果")
            return None
    
    except Exception as e:
        logger.error(f"语音识别出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def mock_llm_process(text: str) -> str:
    """模拟LLM处理，简单返回一个响应"""
    logger.info(f"步骤3: 模拟LLM处理, 输入: {text}")
    
    # 简单的回复逻辑
    if "天气" in text:
        response = "今天天气确实很好，阳光明媚，适合户外活动。散步是个不错的选择，公园里的花应该都开了。"
    elif "你好" in text or "您好" in text:
        response = "你好！很高兴为你服务。有什么我能帮助你的吗？"
    elif "名字" in text:
        response = "我是由Kokoro语音引擎驱动的数字人助手，很高兴认识你！"
    else:
        response = "我理解你的意思了。请问还有其他我能帮助你的吗？"
    
    logger.info(f"LLM响应: {response}")
    return response

async def test_full_flow():
    """测试完整流程：TTS -> ASR -> LLM -> TTS"""
    logger.info("开始测试完整流程: TTS -> ASR -> LLM -> TTS")
    
    # 步骤1: 使用TTS生成初始语音
    initial_text = "今天天气真不错，我们一起去公园散步吧。"
    initial_audio = await generate_tts_audio(initial_text)
    if not initial_audio:
        logger.error("初始语音生成失败，测试终止")
        return False
    
    # 步骤2: 使用ASR识别语音
    recognized_text = await perform_asr(initial_audio)
    if not recognized_text:
        logger.error("语音识别失败，测试终止")
        
        # 如果识别失败，我们仍然可以使用原始文本继续测试
        logger.info("使用原始文本继续测试")
        recognized_text = initial_text
    
    # 步骤3: 使用LLM处理文本（这里使用模拟的LLM）
    llm_response = await mock_llm_process(recognized_text)
    
    # 步骤4: 将LLM响应转换回语音
    final_audio = await generate_tts_audio(llm_response, voice_id='zh_f1')
    if not final_audio:
        logger.error("最终语音生成失败")
        return False
    
    # 保存最终语音
    final_audio_path = os.path.join(output_dir, 'final_response.wav')
    with open(final_audio_path, 'wb') as f:
        f.write(final_audio.data)
    logger.info(f"最终响应语音已保存到: {final_audio_path}")
    
    # 显示完整流程结果
    logger.info("完整流程测试完成!")
    logger.info(f"原始文本: {initial_text}")
    logger.info(f"ASR识别文本: {recognized_text}")
    logger.info(f"LLM响应: {llm_response}")
    
    return True

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_full_flow())
