# audio_processor.py
import logging
import backoff
import os
from typing import Optional, Dict, Any, AsyncGenerator, Callable
from yacs.config import CfgNode as CN
from utils import config, AudioMessage, TextMessage, AudioFormatType
from engine.asr import ASRFactory
from engine.llm import LLMFactory
from integrations.deepgram import text_to_speech_cached
from integrations.minimax import get_minimax_integration
from utils.audio_utils import detect_audio_format, split_text_into_sentences

# 配置日志
logger = logging.getLogger(__name__)

class AudioProcessor:
    """音频处理类，封装转录和TTS功能"""
    
    def __init__(self, default_language="zh-CN"):
        self.default_language = default_language
        self.tts_voice = "aura-mandarin"
        
        # 初始化 ASR 引擎
        self._init_asr_engine()
        
        # 初始化 LLM 引擎
        self._init_llm_engine()
        
    def _init_asr_engine(self):
        """
        初始化 ASR 引擎
        """
        try:
            # 优先尝试加载 FunASR 本地模型配置
            funasr_config_path = os.path.join(os.path.dirname(__file__), "configs/engines/asr/funasrLocal.yaml")
            if os.path.exists(funasr_config_path):
                asr_config = config.load_yaml(funasr_config_path)
                self.asr_engine = ASRFactory.create(asr_config)
                logger.info(f"本地 FunASR 引擎初始化成功: {self.asr_engine.name}")
                return
            
            # 如果没有本地模型配置或加载失败，回退到 Deepgram
            config_path = os.path.join(os.path.dirname(__file__), "configs/engines/asr/deepgramAPI.yaml")
            if os.path.exists(config_path):
                asr_config = config.load_yaml(config_path)
                self.asr_engine = ASRFactory.create(asr_config)
                logger.info(f"Deepgram ASR 引擎初始化成功: {self.asr_engine.name}")
            else:
                logger.error(f"ASR 配置文件不存在: {config_path}")
                self.asr_engine = None
        except Exception as e:
            logger.error(f"ASR 引擎初始化失败: {e}")
            self.asr_engine = None
            
    def _init_llm_engine(self):
        """
        初始化 LLM 引擎
        """
        try:
            # 加载 MiniMax LLM 配置
            config_path = os.path.join(os.path.dirname(__file__), "configs/engines/llm/minimaxAPI.yaml")
            if os.path.exists(config_path):
                llm_config = config.load_yaml(config_path)
                self.llm_engine = LLMFactory.create(llm_config)
                logger.info(f"LLM 引擎初始化成功: {self.llm_engine.name}")
            else:
                logger.error(f"LLM 配置文件不存在: {config_path}")
                self.llm_engine = None
        except Exception as e:
            logger.error(f"LLM 引擎初始化失败: {e}")
            self.llm_engine = None
    
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        giveup=lambda e: isinstance(e, ValueError)
    )
    async def transcribe(self, audio_data, language=None, format=None):
        """
        转录音频，带自动重试
        
        参数:
            audio_data (bytes): 音频数据
            language (str, 可选): 语言代码，默认使用实例默认语言
            format (str, 可选): 音频MIME类型，如"audio/webm"
        
        返回:
            str: 转录的文本，失败时返回None
        """
        try:
            lang = language or self.default_language
            logger.info(f"开始转录音频，语言: {lang}, 格式: {format}")
            
            if self.asr_engine is None:
                logger.error("ASR 引擎未初始化")
                return None
            
            # 准备音频格式
            audio_format = AudioFormatType.WEBM  # 默认格式
            if format:
                if "wav" in format.lower():
                    audio_format = AudioFormatType.WAV
                elif "mp3" in format.lower():
                    audio_format = AudioFormatType.MP3
                elif "ogg" in format.lower():
                    audio_format = AudioFormatType.OGG
            
            # 创建音频消息
            audio_message = AudioMessage(
                data=audio_data,
                format=audio_format,
                sampleRate=16000,  # 默认采样率
                sampleWidth=2      # 默认采样宽度
            )
            
            # 调用 ASR 引擎进行转录
            result = await self.asr_engine.run(audio_message, language=lang)
            
            if result and isinstance(result, TextMessage) and result.data:
                transcript = result.data
                logger.info(f"转录成功: {transcript[:50]}...")
                return transcript
            else:
                logger.warning("转录结果为空")
                return None
            
        except Exception as e:
            logger.error(f"转录失败: {e}")
            return None
            
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        giveup=lambda e: isinstance(e, ValueError)
    )
    async def synthesize(self, text, language=None, tts_engine="minimax", use_cache=True, **kwargs):
        """
        将文本转换为语音，带自动重试
        
        参数:
            text (str): 要转换为语音的文本
            language (str, 可选): 语言代码，默认使用实例默认语言
            tts_engine (str, 可选): 语音合成引擎，支持"minimax"和"deepgram"
            use_cache (bool, 可选): 是否使用缓存
            **kwargs: 额外的引擎特定参数
        
        返回:
            dict: 包含音频数据和元信息的字典，失败时返回None
        """
        try:
            lang = language or self.default_language
            voice = kwargs.get("voice", self.tts_voice)
            speed = kwargs.get("speed", 1.0)
            sample_rate = kwargs.get("sample_rate", 24000)
            
            # 为中文选择合适的声音
            if lang == "zh-CN" and "mandarin" not in voice and tts_engine == "deepgram":
                voice = "aura-mandarin"
                
            logger.info(f"开始文本转语音，引擎: {tts_engine}, 语言: {lang}, 声音: {voice}")
            
            # 根据选择的引擎调用不同的TTS服务
            if tts_engine.lower() == "minimax":
                # 使用MiniMax TTS
                minimax = get_minimax_integration()
                result = await minimax.text_to_speech(
                    text=text,
                    voice_id=voice,  # 使用适当的映射
                    speed=speed,
                    sample_rate=sample_rate,
                    use_cache=use_cache,
                    api_version="T2A_V2"  # 使用最新版API
                )
                
                if result.get("success"):
                    audio_data = result.get("audio_data")
                    audio_format = result.get("format", "mp3")
                    from_cache = result.get("from_cache", False)
                    
                    logger.info(f"MiniMax TTS成功: {len(audio_data)} 字节" + 
                                (" (来自缓存)" if from_cache else ""))
                    
                    return {
                        "success": True,
                        "audio_data": audio_data,
                        "format": audio_format,
                        "sample_rate": sample_rate,
                        "from_cache": from_cache
                    }
                else:
                    error = result.get("error", "未知错误")
                    logger.warning(f"MiniMax TTS失败: {error}")
                    return {
                        "success": False,
                        "error": error
                    }
            else:
                # 使用Deepgram TTS（旧实现）
                audio_data = await text_to_speech_cached(text, voice, lang)
                
                if audio_data:
                    # 尝试检测音频格式
                    audio_format = detect_audio_format(audio_data) or "mp3"
                    logger.info(f"Deepgram TTS成功: {len(audio_data)} 字节")
                    
                    return {
                        "success": True,
                        "audio_data": audio_data,
                        "format": audio_format,
                        "from_cache": False  # Deepgram缓存状态未知
                    }
                else:
                    logger.warning("Deepgram TTS结果为空")
                    return {
                        "success": False,
                        "error": "没有生成音频数据"
                    }
            
        except Exception as e:
            logger.error(f"文本转语音失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def set_language(self, language):
        """设置默认语言"""
        logger.info(f"设置默认语言: {language}")
        self.default_language = language
        
    def set_voice(self, voice):
        """设置TTS声音"""
        logger.info(f"设置TTS声音: {voice}")
        self.tts_voice = voice
        
    def get_settings(self):
        """获取当前音频处理设置"""
        return {
            "language": self.default_language,
            "voice": self.tts_voice
        }
        
    async def synthesize_streaming(self, text, language=None, max_chunk_size=200, use_cache=True, **kwargs):
        """
        流式合成语音，将长文本分成多个片段逐个处理
        
        参数:
            text (str): 要转换为语音的文本
            language (str, 可选): 语言代码，默认使用实例默认语言
            max_chunk_size (int, 可选): 切分文本的最大字符数
            use_cache (bool, 可选): 是否使用缓存
            **kwargs: 额外的引擎特定参数
            
        返回:
            AsyncGenerator: 异步生成器，返回音频数据块
        """
        try:
            lang = language or self.default_language
            voice = kwargs.get("voice", self.tts_voice)
            speed = kwargs.get("speed", 1.0)
            sample_rate = kwargs.get("sample_rate", 24000)
            callback = kwargs.get("callback", None)
            
            logger.info(f"开始流式文本转语音，语言: {lang}, 声音: {voice}")
            
            # 使用MiniMax TTS进行流式合成
            minimax = get_minimax_integration()
            async for chunk_result in minimax.text_to_speech_streaming(
                text=text,
                voice_id=voice,
                speed=speed,
                sample_rate=sample_rate,
                use_cache=use_cache,
                max_chunk_size=max_chunk_size,
                callback=callback
            ):
                yield chunk_result
                
        except Exception as e:
            logger.error(f"流式文本转语音失败: {e}")
            yield {
                "success": False,
                "error": str(e)
            }
        
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        giveup=lambda e: isinstance(e, ValueError)
    )
    async def generate_response(self, text, system_prompt=None):
        """
        使用 LLM 引擎生成回复，带自动重试
        
        参数:
            text (str): 用户输入文本
            system_prompt (str, 可选): 系统提示词
        
        返回:
            str: 生成的回复，失败时返回None
        """
        try:
            if self.llm_engine is None:
                logger.error("LLM 引擎未初始化")
                return None
                
            logger.info(f"开始生成回复，输入: {text[:50]}...")
            
            # 创建文本消息
            text_message = TextMessage(
                data=text,
                desc="user"
            )
            
            # 调用 LLM 引擎生成回复
            kwargs = {}
            if system_prompt:
                kwargs["system_prompt"] = system_prompt
                
            result = await self.llm_engine.run(text_message, **kwargs)
            
            if result and isinstance(result, TextMessage) and result.data:
                response = result.data
                logger.info(f"生成回复成功: {response[:50]}...")
                return response
            else:
                logger.warning("生成回复结果为空")
                return None
                
        except Exception as e:
            logger.error(f"生成回复失败: {e}")
            return None
            
    async def close(self):
        """
        关闭所有引擎会话
        """
        try:
            if hasattr(self, 'llm_engine') and self.llm_engine:
                await self.llm_engine.close()
                logger.info("LLM 引擎会话已关闭")
        except Exception as e:
            logger.error(f"关闭 LLM 引擎会话失败: {e}")