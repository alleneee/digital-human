# deepgram_integration.py
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    PrerecordedOptions,
    LiveOptions,
    FileSource,
    UrlSource,
    BufferSource
)
import io
import asyncio
import os
import logging
import hashlib
from functools import lru_cache
from dotenv import load_dotenv
import time

# 配置日志
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# 文本到哈希的映射，用于缓存
text_hash_map = {}

# 创建Deepgram客户端
def create_deepgram_client():
    """
    创建并返回已配置的Deepgram客户端
    """
    try:
        # 检查API密钥是否存在
        if not DEEPGRAM_API_KEY:
            logger.error("未找到Deepgram API密钥，请确保已设置DEEPGRAM_API_KEY环境变量")
            return None
            
        logger.info(f"使用Deepgram API密钥: {DEEPGRAM_API_KEY[:5]}...{DEEPGRAM_API_KEY[-5:] if len(DEEPGRAM_API_KEY) > 10 else ''}")
        
        # 设置Deepgram客户端选项
        options = DeepgramClientOptions(
            api_key=DEEPGRAM_API_KEY,
            verbose=True  # 启用Deepgram自身的调试日志
        )
        
        # 创建客户端
        client = DeepgramClient(options)
        logger.info("成功创建Deepgram客户端")
        return client
    except Exception as e:
        logger.error(f"创建Deepgram客户端时出错: {str(e)}", exc_info=True)
        return None

# 预录制音频转录
async def transcribe_audio_buffer(audio_data, language="zh-CN", format=None):
    """
    使用Deepgram将音频缓冲区转录为文本
    
    参数:
        audio_data (bytes): 音频数据字节
        language (str): 音频语言代码
        format (str): 音频格式MIME类型，如'audio/webm'
    
    返回:
        str: 转录的文本
    """
    try:
        # 记录详细的输入参数信息
        data_size = len(audio_data) if audio_data else 0
        logger.info(f"开始音频转录请求: 数据大小={data_size}字节, 语言={language}, 提供的格式={format}")
        
        # 检查音频数据是否有效
        if not audio_data or len(audio_data) < 100:
            logger.error(f"音频数据太小或为空: {data_size}字节")
            return None
        
        # 记录音频数据的签名并尝试自动检测格式
        prefix_hex = audio_data[:30].hex() if len(audio_data) >= 30 else audio_data.hex()
        logger.debug(f"音频数据前30字节: {prefix_hex}")
        
        # 自动检测音频格式(如果未提供)
        detected_format = None
        if not format:
            detected_format = detect_audio_format(audio_data)
            if detected_format:
                logger.info(f"自动检测到音频格式: {detected_format}")
                format = detected_format
            else:
                logger.warning("无法自动检测音频格式，使用默认值")
        
        # 创建Deepgram客户端
        logger.info("正在创建Deepgram客户端...")
        client = create_deepgram_client()
        if not client:
            logger.error("无法创建Deepgram客户端")
            return None
        logger.info("Deepgram客户端创建成功")
        
        # 确定最终使用的MIME类型
        mime_type = format or "audio/webm"  # 默认使用webm
        logger.info(f"最终使用的MIME类型: {mime_type}")
        
        # 设置转录选项
        logger.info(f"设置Deepgram转录选项: 模型=nova-2, 语言={language}")
        options = PrerecordedOptions(
            model="nova-2",
            language=language,
            smart_format=True,
            punctuate=True,
            endpointing=200,
            mimetype=mime_type
        )
        
        logger.info("正在准备发送转录请求到Deepgram...")
        start_time = time.time()
        
        # 创建BufferSource
        buffer_source = BufferSource(buffer=audio_data)
        
        # 发送转录请求
        logger.info("发送请求到Deepgram API...")
        try:
            response = await client.listen.prerecorded.v("1").transcribe_file(
                buffer_source,
                options
            )
            
            process_time = time.time() - start_time
            logger.info(f"Deepgram请求完成，处理时间: {process_time:.2f}秒")
        except Exception as api_error:
            logger.error(f"Deepgram API调用失败: {str(api_error)}", exc_info=True)
            return None
        
        # 解析响应
        if response and hasattr(response, "results"):
            logger.info("成功收到Deepgram响应")
            # 获取第一个替代转录结果
            try:
                transcript = response.results.channels[0].alternatives[0].transcript
                if transcript:
                    logger.info(f"Deepgram转录成功: '{transcript}'")
                    return transcript
                else:
                    logger.warning("Deepgram返回空转录")
            except (AttributeError, IndexError) as e:
                logger.error(f"解析Deepgram响应时出错: {str(e)}", exc_info=True)
                # 尝试打印响应结构以便调试
                try:
                    logger.debug(f"响应结构: {response.to_dict()}")
                except:
                    logger.debug("无法序列化响应对象")
        else:
            logger.warning("Deepgram返回的结果格式异常")
            if response:
                logger.debug(f"响应对象类型: {type(response)}")
                logger.debug(f"响应对象属性: {dir(response)}")
        
        return None
        
    except Exception as e:
        logger.error(f"音频转录处理过程中出现未处理异常: {str(e)}", exc_info=True)
        return None

# 实时音频转录设置
async def setup_live_transcription(callback_function, language="zh-CN"):
    """
    设置实时音频转录
    
    参数:
        callback_function: 当接收到转录结果时调用的函数
        language (str): 音频语言代码
        
    返回:
        object: Deepgram实时转录连接
    """
    try:
        # 创建Deepgram客户端
        client = create_deepgram_client()
        if not client:
            logger.error("无法创建Deepgram客户端用于实时转录")
            return None
        
        # 创建实时转录连接
        live_transcription = client.listen.live.v("1")
        
        # 设置转录选项
        options = LiveOptions(
            model="nova-3",           # 使用最新的Nova-3模型
            language=language,        # 设置语言
            smart_format=True,        # 智能格式化
            punctuate=True,           # 添加标点符号
            interim_results=True,     # 接收中间结果
            endpointing=True,         # 自动句子终止检测
            encoding="linear16",      # 音频编码格式
            sample_rate=16000,        # 采样率
            channels=1                # 单声道
        )
        
        # 设置消息处理函数
        @live_transcription.on_message
        async def on_message(result):
            # 只处理包含转录结果的消息
            if result.is_final and result.channel and result.channel.alternatives:
                text = result.channel.alternatives[0].transcript
                if text.strip():
                    await callback_function(text)
        
        # 设置错误处理函数
        @live_transcription.on_error
        async def on_error(error):
            logger.error(f"实时转录错误: {error}")
        
        # 设置关闭处理函数
        @live_transcription.on_close
        async def on_close():
            logger.info("实时转录连接已关闭")
        
        # 开始连接
        await live_transcription.start(options)
        logger.info(f"实时转录已启动，语言: {language}")
        return live_transcription
        
    except Exception as e:
        logger.error(f"设置实时转录失败: {e}")
        return None

# 为TTS响应添加缓存
@lru_cache(maxsize=100)
async def _cached_text_to_speech(text_hash, voice, language):
    """缓存版本的TTS，使用文本哈希作为键"""
    # 从哈希中恢复原始文本
    text = text_hash_map.get(text_hash)
    if not text:
        logger.warning(f"缓存中未找到文本哈希: {text_hash}")
        return None
    
    logger.debug(f"缓存未命中，生成语音: {text[:30]}...")
    return await _text_to_speech_impl(text, voice, language)

# 实际的TTS实现
async def _text_to_speech_impl(text, voice, language):
    """内部TTS实现，不带缓存"""
    try:
        # 创建Deepgram客户端
        client = create_deepgram_client()
        if not client:
            logger.error("无法创建Deepgram客户端用于TTS")
            return None
        
        # 中文检测，如果是中文使用aura-mandarin声音
        if language == "zh-CN" and "mandarin" not in voice:
            voice = "aura-mandarin"
            
        # 发送TTS请求
        response = await client.speak.v("1").stream(
            text=text,
            voice=voice,
            model="aura",
            encoding="mp3",     # 输出编码格式
            container="mp3",    # 容器格式
            sample_rate=24000   # 采样率
        )
        
        # 返回音频数据
        return response.audio_data
            
    except Exception as e:
        logger.error(f"文本转语音错误: {e}")
        return None

# 带缓存的文本转语音函数
async def text_to_speech_cached(text, voice="aura-asteria-en", language="zh-CN"):
    """带缓存的文本转语音版本"""
    # 计算文本哈希
    text_hash = hashlib.md5(text.encode()).hexdigest()
    
    # 存储文本和哈希的映射
    text_hash_map[text_hash] = text
    
    # 调用缓存版本
    logger.debug(f"使用缓存版本的TTS，文本哈希: {text_hash}")
    return await _cached_text_to_speech(text_hash, voice, language)

# 保留原始函数以保持向后兼容
async def text_to_speech(text, voice="aura-asteria-en", language="zh-CN"):
    """
    使用Deepgram Aura将文本转换为语音
    
    参数:
        text (str): 要转换为语音的文本
        voice (str): 使用的语音名称(例如：aura-asteria-en, aura-mandarin)
        language (str): 文本语言代码
        
    返回:
        bytes: 音频数据
    """
    # 调用带缓存的版本
    return await text_to_speech_cached(text, voice, language)

# 测试Deepgram功能
async def test_deepgram():
    """
    测试Deepgram功能是否正常工作
    """
    logger.info("测试Deepgram功能...")
    
    # 测试TTS
    logger.info("测试文本转语音...")
    audio_data = await text_to_speech_cached("你好，这是一个测试。我是由Deepgram驱动的数字人。", language="zh-CN")
    if audio_data:
        with open("test_tts.mp3", "wb") as f:
            f.write(audio_data)
        logger.info("✓ TTS测试成功，音频已保存为test_tts.mp3")
    else:
        logger.error("✗ TTS测试失败")
    
    # 测试TTS缓存
    logger.info("测试TTS缓存...")
    start_time = asyncio.get_event_loop().time()
    audio_data2 = await text_to_speech_cached("你好，这是一个测试。我是由Deepgram驱动的数字人。", language="zh-CN")
    end_time = asyncio.get_event_loop().time()
    
    if audio_data2 and (end_time - start_time) < 0.1:
        logger.info(f"✓ TTS缓存测试成功，响应时间: {(end_time - start_time)*1000:.2f}ms")
    else:
        logger.warning(f"? TTS缓存测试可疑，响应时间: {(end_time - start_time)*1000:.2f}ms")
    
    return True

# 音频格式检测
def detect_audio_format(audio_data):
    """
    基于文件签名/魔数检测音频格式
    
    参数:
        audio_data: 要检测格式的二进制音频数据
    返回:
        检测到的MIME类型或None
    """
    if not audio_data or len(audio_data) < 12:
        return None
    
    try:
        # 检查WEBM格式(1A 45 DF A3)
        if audio_data[0:4] == b"\x1a\x45\xdf\xa3":
            return "audio/webm"
        
        # 检查MP3格式(ID3 或 MPEG帧头 FF FB)
        if audio_data[0:3] == b"ID3" or (audio_data[0:2] == b"\xff\xfb" or audio_data[0:2] == b"\xff\xfa"):
            return "audio/mpeg"
        
        # 检查WAV格式(RIFF....WAVE)
        if audio_data[0:4] == b"RIFF" and audio_data[8:12] == b"WAVE":
            return "audio/wav"
        
        # 检查Ogg格式(OggS)
        if audio_data[0:4] == b"OggS":
            return "audio/ogg"
        
        # 检查FLAC格式(fLaC)
        if audio_data[0:4] == b"fLaC":
            return "audio/flac"
        
        # 检查AAC ADTS格式(FF F1 或 FF F9)
        if (len(audio_data) > 2 and 
            (audio_data[0] == 0xFF and (audio_data[1] & 0xF0) == 0xF0)):
            return "audio/aac"
            
        # 检查Opus格式(在Ogg容器中)
        if audio_data[0:4] == b"OggS" and b"OpusHead" in audio_data[0:50]:
            return "audio/opus"
            
        # WebRTC编码的PCM数据通常没有明确的魔数标识
        # 可以通过数据模式来猜测
        if all(0 <= b <= 255 for b in audio_data[0:100]):
            # 简单检查是否有合理的音频模式(避免完全随机数据)
            non_zero = sum(1 for b in audio_data[0:100] if b != 0)
            if 10 <= non_zero <= 90:  # 如果0-255之间的值分布相对合理
                return "audio/webm"  # 返回通用格式，后续处理可能需要更多信息

        # 无法识别
        logger.warning(f"无法识别的音频格式，前12字节: {audio_data[0:12].hex()}")
        return None
    except Exception as e:
        logger.error(f"检测音频格式时出错: {str(e)}")
        return None

# 直接运行此文件时执行测试
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(test_deepgram())