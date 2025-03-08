# -*- coding: utf-8 -*-
'''
语音处理流水线
'''

import logging
import asyncio
import os
import tempfile
from typing import Optional, Dict, Any, Tuple, List
from utils.protocol import AudioMessage, AudioFormatType, TextMessage
from utils.audio import convert_audio_format, get_audio_duration

# 配置日志
logger = logging.getLogger(__name__)

class SpeechProcessor:
    """
    语音处理器：处理音频转换、静音检测、音频分段等功能
    """
    def __init__(self, config=None):
        """
        初始化语音处理器
        
        参数:
            config: 处理器配置
        """
        self.config = config or {}
        self.temp_files = []
        
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
    
    async def format_conversion(self, audio_message: AudioMessage, 
                               target_format: AudioFormatType,
                               target_sample_rate: int = 16000,
                               target_sample_width: int = 2) -> Optional[AudioMessage]:
        """
        音频格式转换
        
        参数:
            audio_message: 输入音频消息
            target_format: 目标格式
            target_sample_rate: 目标采样率
            target_sample_width: 目标样本宽度
            
        返回:
            转换后的音频消息
        """
        try:
            logger.info(f"音频格式转换: {audio_message.format} -> {target_format}, "
                       f"采样率: {audio_message.sampleRate} -> {target_sample_rate}")
            
            # 如果已经是目标格式和采样率，直接返回
            if (audio_message.format == target_format and 
                audio_message.sampleRate == target_sample_rate and
                audio_message.sampleWidth == target_sample_width):
                return audio_message
            
            # 将音频数据写入临时文件
            with tempfile.NamedTemporaryFile(delete=False, 
                                            suffix=f'.{audio_message.format.value}') as temp_in:
                temp_in.write(audio_message.data)
                input_path = temp_in.name
                self.temp_files.append(input_path)
            
            # 创建输出临时文件
            with tempfile.NamedTemporaryFile(delete=False, 
                                            suffix=f'.{target_format.value}') as temp_out:
                output_path = temp_out.name
                self.temp_files.append(output_path)
            
            # 执行格式转换
            converted = await convert_audio_format(
                input_path=input_path,
                output_path=output_path,
                target_format=target_format.value,
                target_sample_rate=target_sample_rate,
                target_sample_width=target_sample_width
            )
            
            if not converted:
                logger.error("音频格式转换失败")
                return None
            
            # 读取转换后的文件
            with open(output_path, 'rb') as f:
                converted_data = f.read()
            
            # 创建新的音频消息
            converted_message = AudioMessage(
                data=converted_data,
                format=target_format,
                sampleRate=target_sample_rate,
                sampleWidth=target_sample_width,
                desc=audio_message.desc
            )
            
            logger.info(f"音频格式转换成功: {len(converted_data)} 字节")
            return converted_message
            
        except Exception as e:
            logger.error(f"音频格式转换出错: {str(e)}")
            return None
        finally:
            # 清理临时文件
            self.cleanup()
    
    async def get_audio_info(self, audio_message: AudioMessage) -> Dict[str, Any]:
        """
        获取音频信息
        
        参数:
            audio_message: 输入音频消息
            
        返回:
            音频信息字典
        """
        try:
            # 将音频数据写入临时文件
            with tempfile.NamedTemporaryFile(delete=False, 
                                            suffix=f'.{audio_message.format.value}') as temp:
                temp.write(audio_message.data)
                file_path = temp.name
                self.temp_files.append(file_path)
            
            # 获取音频时长
            duration = await get_audio_duration(file_path)
            
            info = {
                "format": audio_message.format.value,
                "sample_rate": audio_message.sampleRate,
                "sample_width": audio_message.sampleWidth,
                "duration": duration,
                "size_bytes": len(audio_message.data)
            }
            
            return info
            
        except Exception as e:
            logger.error(f"获取音频信息出错: {str(e)}")
            return {"error": str(e)}
        finally:
            # 清理临时文件
            self.cleanup()
    
    async def process_for_asr(self, audio_message: AudioMessage) -> Optional[AudioMessage]:
        """
        为ASR处理优化音频
        
        参数:
            audio_message: 输入音频消息
            
        返回:
            处理后的音频消息
        """
        # 转换为16kHz采样率的WAV格式，适合大多数ASR引擎
        return await self.format_conversion(
            audio_message=audio_message,
            target_format=AudioFormatType.WAV,
            target_sample_rate=16000,
            target_sample_width=2
        )
