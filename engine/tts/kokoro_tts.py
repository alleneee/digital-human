# -*- coding: utf-8 -*-
'''
Kokoro TTS引擎模块
'''

import logging
import tempfile
import os
import torch
import asyncio
from typing import Dict, Any, List, Optional, Tuple
import soundfile as sf
from utils.protocol import TextMessage, AudioMessage, AudioFormatType
from utils.singleton import Singleton

# 配置日志
logger = logging.getLogger(__name__)

class KokoroTTSEngine(metaclass=Singleton):
    """
    Kokoro TTS引擎
    """
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化Kokoro TTS引擎
        
        参数:
            config: 引擎配置
        """
        self.config = config or {}
        self.pipeline = None
        self.is_ready = False
        self.temp_files = []
        self.voices = {
            # 英语声音
            'en_m1': 'ae_soft',   # 英语-男声1
            'en_m2': 'ae_calm',   # 英语-男声2
            'en_f1': 'af_heart',  # 英语-女声1
            'en_f2': 'af_prose',  # 英语-女声2
            
            # 默认使用英文声音说中文
            'zh_m1': 'ae_soft',  # 中文-男声1
            'zh_f1': 'af_heart',  # 中文-女声1
            
            # 日语声音 (需要安装misaki[ja])
            'ja_m1': 'j1',  # 日语-男声1
            'ja_f1': 'j2',  # 日语-女声1
            
            # 更多语言可根据需要添加
        }
        self.default_voice = self.config.get('default_voice', 'zh_f1')
        self.sample_rate = 24000  # Kokoro默认采样率
        
    def __del__(self):
        """
        析构函数，清理临时文件
        """
        self.cleanup()
        
    def cleanup(self):
        """
        清理临时文件
        """
        for file_path in self.temp_files:
            if os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {file_path}, 错误: {str(e)}")
        self.temp_files = []

    async def initialize(self):
        """
        初始化Kokoro TTS引擎
        """
        if self.is_ready:
            return True
            
        try:
            logger.info("正在初始化Kokoro TTS引擎...")
            
            # 导入Kokoro
            from kokoro import KPipeline
            
            # 获取语言设置
            lang_code = self.config.get('lang_code', 'z')  # 默认中文
            
            # 初始化Kokoro Pipeline
            self.pipeline = KPipeline(lang_code=lang_code)
            
            # 加载自定义声音模型（如果配置了）
            voice_tensor_path = self.config.get('voice_tensor_path')
            if voice_tensor_path and os.path.exists(voice_tensor_path):
                logger.info(f"加载自定义声音模型: {voice_tensor_path}")
                self.custom_voice = torch.load(voice_tensor_path, weights_only=True)
            else:
                self.custom_voice = None
                
            self.is_ready = True
            logger.info("Kokoro TTS引擎初始化成功")
            return True
            
        except ImportError as e:
            logger.error(f"Kokoro库导入失败: {str(e)}")
            logger.error("请确认已安装Kokoro: pip install kokoro>=0.8.4 soundfile")
            return False
        except Exception as e:
            logger.error(f"Kokoro TTS引擎初始化失败: {str(e)}")
            return False
            
    async def synthesize(self, text_message: TextMessage, voice_id: str = None) -> Optional[AudioMessage]:
        """
        使用Kokoro进行语音合成
        
        参数:
            text_message: 文本消息
            voice_id: 语音ID
            
        返回:
            合成的音频消息
        """
        if not self.is_ready:
            success = await self.initialize()
            if not success:
                logger.error("Kokoro TTS引擎未就绪")
                return None
                
        try:
            # 获取文本内容
            text = text_message.data
            if not text:
                logger.warning("合成文本为空")
                return None
                
            logger.info(f"开始Kokoro语音合成: {text[:30]}...")
            
            # 确定使用的声音
            voice = self.custom_voice
            if not voice:
                voice_id = voice_id or self.default_voice
                if voice_id in self.voices:
                    voice = self.voices[voice_id]
                else:
                    voice = self.default_voice
                    if voice in self.voices:
                        voice = self.voices[voice]
            
            # 创建临时文件保存合成结果
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp:
                output_path = temp.name
                self.temp_files.append(output_path)
            
            # 设置合成参数
            speed = self.config.get('speed', 1.0)
            
            # 生成音频
            audio_segments = []
            generator = self.pipeline(
                text, 
                voice=voice,
                speed=speed, 
                split_pattern=r'\n+'
            )
            
            for _, _, audio in generator:
                audio_segments.append(audio)
            
            # 将所有音频段合并
            if audio_segments:
                combined_audio = torch.cat(audio_segments, dim=0).numpy()
                
                # 保存到临时文件
                sf.write(output_path, combined_audio, self.sample_rate)
                
                # 读取合成的音频文件
                with open(output_path, 'rb') as f:
                    audio_data = f.read()
                
                # 创建音频消息
                audio_message = AudioMessage(
                    data=audio_data,
                    format=AudioFormatType.WAV,
                    sampleRate=self.sample_rate,
                    sampleWidth=2,  # 16位采样
                    desc=f"Kokoro TTS: {text[:30]}..."
                )
                
                logger.info(f"Kokoro语音合成成功: {len(audio_data)} 字节")
                return audio_message
            else:
                logger.warning("Kokoro没有生成任何音频片段")
                return None
                
        except Exception as e:
            logger.error(f"Kokoro语音合成失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
        finally:
            # 清理临时文件
            self.cleanup()
            
    def get_available_voices(self) -> Dict[str, str]:
        """
        获取可用的语音列表
        
        返回:
            语音ID和描述的字典
        """
        voices = {
            'en_m1': '英语-男声1 (柔和)',
            'en_m2': '英语-男声2 (平静)',
            'en_f1': '英语-女声1 (温暖)',
            'en_f2': '英语-女声2 (叙事)',
            'zh_m1': '中文-男声1',
            'zh_f1': '中文-女声1',
            'ja_m1': '日语-男声1',
            'ja_f1': '日语-女声1',
        }
        
        if self.custom_voice:
            voices['custom'] = '自定义声音'
            
        return voices
