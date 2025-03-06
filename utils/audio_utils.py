"""
音频处理工具函数
提供音频格式转换、检测和处理的通用功能
"""

import os
import io
import time
import hashlib
import logging
import asyncio
import aiofiles
import wave
from pathlib import Path
from typing import Optional, Tuple, Dict, Union, BinaryIO
from enum import Enum

logger = logging.getLogger(__name__)

# 音频格式枚举
class AudioFormat(Enum):
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    WEBM = "webm"
    UNKNOWN = "unknown"

# 音频缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "audio")
os.makedirs(CACHE_DIR, exist_ok=True)

# 缓存有效期 (单位: 秒)
CACHE_TTL = 86400 * 7  # 7天

async def detect_audio_format(audio_data: bytes) -> AudioFormat:
    """
    检测音频数据的格式
    
    参数:
        audio_data: 音频二进制数据
        
    返回:
        检测到的AudioFormat枚举
    """
    # 检查文件头部特征
    if len(audio_data) < 12:
        return AudioFormat.UNKNOWN
    
    # WAV 格式: RIFF....WAVE
    if audio_data[0:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
        return AudioFormat.WAV
    
    # MP3 格式: ID3 或 0xFF 0xFB
    if audio_data[0:3] == b'ID3' or (audio_data[0] == 0xFF and (audio_data[1] & 0xE0) == 0xE0):
        return AudioFormat.MP3
    
    # OGG 格式: OggS
    if audio_data[0:4] == b'OggS':
        return AudioFormat.OGG
    
    # WEBM 格式检测较复杂，这里简化处理
    if audio_data[0:4] == b'\x1A\x45\xDF\xA3':
        return AudioFormat.WEBM
    
    return AudioFormat.UNKNOWN

async def get_wav_info(wav_data: bytes) -> Tuple[int, int, int]:
    """
    获取WAV文件的采样率、通道数和采样宽度
    
    参数:
        wav_data: WAV音频二进制数据
        
    返回:
        (采样率, 通道数, 采样宽度)元组
    """
    try:
        with io.BytesIO(wav_data) as wav_io:
            with wave.open(wav_io, 'rb') as wav:
                sample_rate = wav.getframerate()
                channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                return sample_rate, channels, sample_width
    except Exception as e:
        logger.error(f"读取WAV信息出错: {e}")
        # 默认返回常见的WAV参数
        return 16000, 1, 2

def compute_content_hash(text: str, voice_id: str = "", extra_params: Dict = None) -> str:
    """
    计算内容哈希值，用于缓存键
    
    参数:
        text: 文本内容
        voice_id: 声音ID
        extra_params: 额外参数
    
    返回:
        哈希字符串
    """
    hash_content = f"{text}:{voice_id}"
    
    # 添加额外参数到哈希内容
    if extra_params:
        for key in sorted(extra_params.keys()):
            hash_content += f":{key}={extra_params[key]}"
    
    # 计算MD5哈希
    return hashlib.md5(hash_content.encode('utf-8')).hexdigest()

async def get_cached_audio(cache_key: str) -> Optional[bytes]:
    """
    从缓存中获取音频数据
    
    参数:
        cache_key: 缓存键
        
    返回:
        缓存的音频数据，如果未找到返回None
    """
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.bin")
    
    try:
        # 检查文件是否存在
        if not os.path.exists(cache_path):
            return None
        
        # 检查缓存是否过期
        file_mtime = os.path.getmtime(cache_path)
        if time.time() - file_mtime > CACHE_TTL:
            logger.info(f"缓存已过期: {cache_key}")
            os.remove(cache_path)
            return None
        
        # 读取缓存文件
        async with aiofiles.open(cache_path, "rb") as f:
            audio_data = await f.read()
            logger.info(f"从缓存加载音频: {cache_key}, 大小: {len(audio_data)} 字节")
            return audio_data
            
    except Exception as e:
        logger.error(f"读取缓存出错: {e}")
        return None

async def save_to_cache(cache_key: str, audio_data: bytes) -> bool:
    """
    保存音频数据到缓存
    
    参数:
        cache_key: 缓存键
        audio_data: 音频二进制数据
        
    返回:
        保存成功返回True
    """
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.bin")
    
    try:
        async with aiofiles.open(cache_path, "wb") as f:
            await f.write(audio_data)
            logger.info(f"音频已缓存: {cache_key}, 大小: {len(audio_data)} 字节")
        return True
    except Exception as e:
        logger.error(f"保存缓存出错: {e}")
        return False

def clean_old_cache() -> int:
    """
    清理过期的缓存文件
    
    返回:
        清理的文件数量
    """
    count = 0
    now = time.time()
    
    try:
        for filename in os.listdir(CACHE_DIR):
            file_path = os.path.join(CACHE_DIR, filename)
            if os.path.isfile(file_path):
                file_mtime = os.path.getmtime(file_path)
                if now - file_mtime > CACHE_TTL:
                    os.remove(file_path)
                    count += 1
        
        if count > 0:
            logger.info(f"已清理 {count} 个过期缓存文件")
        
        return count
    except Exception as e:
        logger.error(f"清理缓存出错: {e}")
        return 0

def split_text_into_sentences(text: str, max_chars: int = 200) -> list:
    """
    将文本分割成句子，用于流式处理
    
    参数:
        text: 要分割的文本
        max_chars: 每个句子的最大字符数
        
    返回:
        分割后的句子列表
    """
    # 标点符号列表，用于划分句子
    delimiters = ['。', '！', '？', '；', '.', '!', '?', ';', '\n']
    
    result = []
    current = ""
    
    # 逐字符扫描文本
    for char in text:
        current += char
        
        # 如果当前积累的文本以分隔符结尾且不为空
        if current and any(current.endswith(d) for d in delimiters):
            result.append(current)
            current = ""
        
        # 如果当前积累的文本超过最大字符数且不为空，强制断句
        elif len(current) >= max_chars:
            # 尝试在单词边界处断句（针对英文）
            if ' ' in current:
                last_space = current.rstrip().rfind(' ')
                if last_space > max_chars * 0.7:  # 如果空格位置在后70%位置
                    result.append(current[:last_space])
                    current = current[last_space+1:]
                else:
                    result.append(current)
                    current = ""
            else:
                # 针对中文等无空格语言，直接按长度断句
                result.append(current)
                current = ""
    
    # 处理剩余的文本
    if current:
        result.append(current)
    
    return result
