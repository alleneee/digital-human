# -*- coding: utf-8 -*-
'''
音频处理工具函数
'''

import io
import os
import asyncio
import logging
import subprocess
import tempfile
from typing import Optional, Dict, Any, Tuple, List
from pydub import AudioSegment
from pydub.silence import split_on_silence, detect_silence

# 配置日志
logger = logging.getLogger(__name__)

def mp3ToWav(mp3_data: bytes) -> bytes:
    """
    将 MP3 格式的音频数据转换为 WAV 格式
    
    参数:
        mp3_data: MP3 格式的音频数据
        
    返回:
        WAV 格式的音频数据
    """
    try:
        # 从字节数据创建 AudioSegment
        audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
        
        # 设置参数
        audio = audio.set_frame_rate(16000)  # 设置采样率为 16kHz
        audio = audio.set_channels(1)        # 设置为单声道
        audio = audio.set_sample_width(2)    # 设置采样宽度为 16bit
        
        # 转换为 WAV 格式
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_data = wav_io.getvalue()
        
        return wav_data
    except Exception as e:
        logger.error(f"MP3 转 WAV 失败: {e}")
        return mp3_data  # 如果转换失败，返回原始数据

async def convert_audio_format(input_path: str, 
                             output_path: str, 
                             target_format: str = "wav",
                             target_sample_rate: int = 16000,
                             target_sample_width: int = 2,
                             target_channels: int = 1) -> bool:
    """
    转换音频格式
    
    参数:
        input_path: 输入音频文件路径
        output_path: 输出音频文件路径
        target_format: 目标格式
        target_sample_rate: 目标采样率
        target_sample_width: 目标样本宽度
        target_channels: 目标声道数
        
    返回:
        是否成功转换
    """
    try:
        # 加载音频文件
        audio = AudioSegment.from_file(input_path)
        
        # 应用转换参数
        if audio.frame_rate != target_sample_rate:
            audio = audio.set_frame_rate(target_sample_rate)
            
        if audio.sample_width != target_sample_width:
            audio = audio.set_sample_width(target_sample_width)
            
        if audio.channels != target_channels:
            audio = audio.set_channels(target_channels)
        
        # 导出为目标格式
        audio.export(output_path, format=target_format)
        
        return os.path.exists(output_path)
    except Exception as e:
        logger.error(f"音频格式转换失败: {str(e)}")
        return False

async def get_audio_duration(file_path: str) -> float:
    """
    获取音频文件时长（秒）
    
    参数:
        file_path: 音频文件路径
        
    返回:
        时长（秒）
    """
    try:
        audio = AudioSegment.from_file(file_path)
        return len(audio) / 1000.0  # 毫秒转秒
    except Exception as e:
        logger.error(f"获取音频时长失败: {str(e)}")
        return 0.0

async def detect_audio_silence(file_path: str, 
                             min_silence_len: int = 500,
                             silence_thresh: int = -40) -> List[Tuple[int, int]]:
    """
    检测音频文件中的静音部分
    
    参数:
        file_path: 音频文件路径
        min_silence_len: 最小静音长度（毫秒）
        silence_thresh: 静音阈值（dB）
        
    返回:
        静音片段列表，每个元素为 (开始时间, 结束时间) 的元组，单位毫秒
    """
    try:
        audio = AudioSegment.from_file(file_path)
        silence_ranges = detect_silence(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)
        return silence_ranges
    except Exception as e:
        logger.error(f"检测音频静音失败: {str(e)}")
        return []

async def split_audio_by_silence(file_path: str,
                               output_dir: str,
                               min_silence_len: int = 500,
                               silence_thresh: int = -40,
                               keep_silence: int = 100) -> List[str]:
    """
    根据静音分割音频文件
    
    参数:
        file_path: 音频文件路径
        output_dir: 输出目录
        min_silence_len: 最小静音长度（毫秒）
        silence_thresh: 静音阈值（dB）
        keep_silence: 保留静音长度（毫秒）
        
    返回:
        分割后的音频文件路径列表
    """
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 加载音频文件
        audio = AudioSegment.from_file(file_path)
        
        # 按静音分割
        chunks = split_on_silence(
            audio, 
            min_silence_len=min_silence_len, 
            silence_thresh=silence_thresh,
            keep_silence=keep_silence
        )
        
        if not chunks:
            logger.warning(f"音频未被分割: {file_path}")
            basename = os.path.basename(file_path)
            output_path = os.path.join(output_dir, basename)
            audio.export(output_path, format="wav")
            return [output_path]
        
        # 导出分割后的音频
        output_files = []
        for i, chunk in enumerate(chunks):
            basename = os.path.basename(file_path)
            name, ext = os.path.splitext(basename)
            output_path = os.path.join(output_dir, f"{name}_{i:03d}.wav")
            chunk.export(output_path, format="wav")
            output_files.append(output_path)
        
        return output_files
    except Exception as e:
        logger.error(f"分割音频失败: {str(e)}")
        return []
