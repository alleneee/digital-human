# -*- coding: utf-8 -*-
'''
音频处理工具函数
'''

import io
import logging
from pydub import AudioSegment

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
