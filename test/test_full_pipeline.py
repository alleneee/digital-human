# -*- coding: utf-8 -*-
'''
测试完整语音处理流程：TTS -> ASR -> LLM -> TTS
'''

import asyncio
import sys
import os
import logging
import base64
import time
import uuid

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.tts.kokoro_tts import KokoroTTSEngine
from utils.protocol import TextMessage, AudioMessage, AudioFormatType
from pipelines.speech import SpeechProcessor
from api.routes import AudioChatRequest, TextChatRequest, api_service

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建输出目录
output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_outputs'))
os.makedirs(output_dir, exist_ok=True)

async def generate_initial_audio():
    """使用Kokoro TTS引擎生成初始测试音频"""
    logger.info("步骤1: 使用Kokoro TTS生成初始语音")
    
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
        return None
    
    # 测试文本
    test_text = "今天天气真不错，我们一起去公园散步吧。"
    
    # 生成语音
    logger.info(f"合成文本: {test_text}")
    text_message = TextMessage(data=test_text)
    audio = await engine.synthesize(text_message, voice_id='zh_f1')
    
    if audio:
        # 保存到文件
        input_audio_path = os.path.join(output_dir, 'test_input.wav')
        with open(input_audio_path, 'wb') as f:
            f.write(audio.data)
        logger.info(f"初始语音生成成功，已保存到: {input_audio_path}")
        return audio
    else:
        logger.error("初始语音生成失败")
        return None

async def send_to_asr(audio_message):
    """将音频发送到ASR进行语音识别"""
    logger.info("步骤2: 发送音频到ASR进行语音识别")
    
    # 创建语音处理器
    speech_processor = SpeechProcessor()
    
    # 确保音频格式正确 (16kHz WAV)
    processed_audio = await speech_processor.process_for_asr(audio_message)
    if not processed_audio:
        logger.error("音频预处理失败")
        return None
    
    # 使用API服务的语音识别
    try:
        # 编码音频数据
        audio_data_b64 = base64.b64encode(processed_audio.data).decode('utf-8')
        
        # 创建ASR请求
        asr_request = {
            "audio_data": audio_data_b64,
            "audio_format": processed_audio.format.value,
            "sample_rate": processed_audio.sampleRate,
            "sample_width": processed_audio.sampleWidth
        }
        
        # 调用ASR
        start_time = time.time()
        asr_result = await api_service.speech_processor.recognize(
            processed_audio
        )
        
        if asr_result:
            logger.info(f"ASR识别结果: {asr_result}")
            return asr_result
        else:
            logger.error("ASR识别失败")
            return None
            
    except Exception as e:
        logger.error(f"ASR处理出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def send_to_llm_and_tts(text, context_id=None):
    """将文本发送到LLM处理，然后将回复转换为语音"""
    logger.info(f"步骤3: 将识别的文本发送到LLM: {text}")
    
    if not text:
        logger.error("无文本输入，无法处理")
        return None
    
    # 创建上下文ID
    context_id = context_id or str(uuid.uuid4())
    
    try:
        # 创建文本请求
        text_request = TextChatRequest(
            text=text,
            context_id=context_id,
            skip_tts=False
        )
        
        # 调用文本对话处理
        start_time = time.time()
        response = await api_service.pipeline.process(
            text_input=text,
            conversation_context=api_service.get_context(context_id)["messages"]
        )
        
        if "error" in response:
            logger.error(f"LLM处理失败: {response['error']}")
            return None
        
        # 提取结果
        response_text = response.get("response_text", "")
        audio_output = response.get("audio_output")
        
        # 保存结果
        if audio_output:
            # 保存音频
            output_audio_path = os.path.join(output_dir, 'test_output.wav')
            with open(output_audio_path, 'wb') as f:
                f.write(audio_output.data)
            logger.info(f"回复语音已保存到: {output_audio_path}")
        
        logger.info(f"LLM回复: {response_text}")
        
        return {
            "response_text": response_text,
            "audio_output": audio_output,
            "context_id": context_id,
            "took_ms": (time.time() - start_time) * 1000
        }
        
    except Exception as e:
        logger.error(f"LLM和TTS处理出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def test_full_pipeline():
    """测试完整的语音处理流程"""
    logger.info("开始测试完整语音处理流程")
    
    # 步骤1: 生成初始测试音频
    input_audio = await generate_initial_audio()
    if not input_audio:
        return False
    
    # 步骤2: 发送音频到ASR进行语音识别
    recognized_text = await send_to_asr(input_audio)
    if not recognized_text:
        return False
    
    # 步骤3: 将识别的文本发送到LLM处理，然后将回复转换为语音
    result = await send_to_llm_and_tts(recognized_text)
    if not result:
        return False
    
    logger.info("完整语音处理流程测试完成!")
    logger.info(f"最终响应: {result['response_text']}")
    
    # 测试音频聊天API
    await test_audio_chat_api(input_audio)
    
    return True

async def test_audio_chat_api(input_audio):
    """测试音频聊天API"""
    logger.info("额外测试: 音频聊天API")
    
    try:
        # 编码音频数据
        audio_data_b64 = base64.b64encode(input_audio.data).decode('utf-8')
        
        # 创建音频聊天请求
        chat_request = AudioChatRequest(
            audio_data=audio_data_b64,
            audio_format=input_audio.format.value,
            sample_rate=input_audio.sampleRate,
            sample_width=input_audio.sampleWidth,
            context_id=str(uuid.uuid4()),
            skip_asr=False,
            skip_llm=False,
            skip_tts=False
        )
        
        # 调用API
        start_time = time.time()
        response = await api_service.pipeline.process(
            audio_input=input_audio,
            conversation_context=api_service.get_context(chat_request.context_id)["messages"]
        )
        
        if "error" in response:
            logger.error(f"音频聊天API调用失败: {response['error']}")
            return False
        
        # 提取结果
        input_text = response.get("input_text")
        response_text = response.get("response_text", "")
        audio_output = response.get("audio_output")
        
        # 保存结果
        if audio_output:
            # 保存音频
            output_audio_path = os.path.join(output_dir, 'api_test_output.wav')
            with open(output_audio_path, 'wb') as f:
                f.write(audio_output.data)
            logger.info(f"API回复语音已保存到: {output_audio_path}")
        
        logger.info(f"识别的输入: {input_text}")
        logger.info(f"API回复: {response_text}")
        logger.info(f"处理耗时: {(time.time() - start_time) * 1000:.2f} ms")
        
        return True
        
    except Exception as e:
        logger.error(f"音频聊天API测试出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_full_pipeline())
