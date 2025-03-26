#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数字人框架与EchoMimicV2集成模块
"""

import os
import sys
import logging
import asyncio
import aiofiles
import aiohttp
import tempfile
from pathlib import Path
import numpy as np
import json
import base64
from typing import Dict, List, Optional, Any, Union
import subprocess

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EchoMimicIntegration:
    """EchoMimicV2集成类，处理digital-human的TTS输出并生成视频"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化EchoMimicV2集成
        
        Args:
            config: 配置参数，包含echomimic的路径和各种生成选项
        """
        self.config = config
        self.echomimic_path = config.get("echomimic_path", "/Users/niko/echomimic_v2")
        self.ref_image_path = config.get("ref_image_path", "")
        self.pose_dir_path = config.get("pose_dir_path", "")
        self.output_dir = Path(config.get("output_dir", os.path.join(self.echomimic_path, "outputs")))
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # 视频生成参数
        self.video_params = {
            "width": config.get("width", 512),
            "height": config.get("height", 512),
            "length": config.get("length", 120),
            "steps": config.get("steps", 25),
            "sample_rate": config.get("sample_rate", 16000),
            "cfg": config.get("cfg", 3.5),
            "fps": config.get("fps", 25),
            "context_frames": config.get("context_frames", 16),
            "context_overlap": config.get("context_overlap", 4),
            "quantization_input": config.get("quantization_input", True),
            "seed": config.get("seed", -1)
        }
        
        # 验证必要的文件路径
        self._validate_paths()
        
    def _validate_paths(self) -> None:
        """验证所需的路径和文件是否存在"""
        if not os.path.exists(self.echomimic_path):
            raise FileNotFoundError(f"EchoMimicV2路径不存在: {self.echomimic_path}")
        
        if not self.ref_image_path or not os.path.exists(self.ref_image_path):
            logger.warning(f"参考图像路径不存在或未设置: {self.ref_image_path}")
        
        if not self.pose_dir_path or not os.path.exists(self.pose_dir_path):
            logger.warning(f"姿势数据目录不存在或未设置: {self.pose_dir_path}")
    
    async def save_audio_to_file(self, audio_data: bytes, audio_format: str = "mp3") -> str:
        """
        将音频数据保存到临时文件
        
        Args:
            audio_data: 音频数据的二进制内容
            audio_format: 音频格式 (mp3, wav等)
            
        Returns:
            临时音频文件的路径
        """
        # 创建临时目录用于存储音频
        temp_dir = Path(tempfile.mkdtemp())
        audio_path = temp_dir / f"tts_output.{audio_format}"
        
        # 写入音频数据
        async with aiofiles.open(audio_path, 'wb') as f:
            await f.write(audio_data)
        
        logger.info(f"音频已保存到: {audio_path}")
        return str(audio_path)
    
    async def generate_video_from_audio(self, audio_path: str, ref_image_path: Optional[str] = None, 
                                   pose_dir_path: Optional[str] = None) -> str:
        """
        使用EchoMimicV2从音频生成视频
        
        Args:
            audio_path: 音频文件路径
            ref_image_path: 可选，参考图像路径，未提供时使用默认值
            pose_dir_path: 可选，姿势数据目录路径，未提供时使用默认值
            
        Returns:
            生成的视频文件路径
        """
        # 使用提供的值或默认值
        ref_image = ref_image_path or self.ref_image_path
        pose_dir = pose_dir_path or self.pose_dir_path
        
        if not ref_image or not os.path.exists(ref_image):
            raise ValueError(f"必须提供有效的参考图像路径: {ref_image}")
        
        if not pose_dir or not os.path.exists(pose_dir):
            raise ValueError(f"必须提供有效的姿势数据目录: {pose_dir}")
        
        # 组织调用EchoMimicV2的命令
        cmd = [
            "python", 
            os.path.join(self.echomimic_path, "infer.py"),
            "--refimg", ref_image,
            "--audio", audio_path,
            "--pose", pose_dir,
            "--width", str(self.video_params["width"]),
            "--height", str(self.video_params["height"]),
            "--length", str(self.video_params["length"]),
            "--steps", str(self.video_params["steps"]),
            "--sample_rate", str(self.video_params["sample_rate"]),
            "--cfg", str(self.video_params["cfg"]),
            "--fps", str(self.video_params["fps"]),
            "--context_frames", str(self.video_params["context_frames"]),
            "--context_overlap", str(self.video_params["context_overlap"]),
            "--seed", str(self.video_params["seed"]),
            "--output_dir", str(self.output_dir)
        ]
        
        if self.video_params["quantization_input"]:
            cmd.append("--quantization")
        
        # 创建子进程执行命令
        logger.info(f"开始生成视频，命令: {' '.join(cmd)}")
        
        try:
            # 使用asyncio处理子进程
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 等待进程完成
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"视频生成失败: {stderr.decode()}")
                raise RuntimeError(f"视频生成失败，返回码: {process.returncode}")
            
            # 解析输出，获取生成的视频路径
            output = stdout.decode()
            logger.info(f"视频生成成功: {output}")
            
            # 查找生成的视频文件
            video_files = list(self.output_dir.glob("*_ws.mp4"))
            if not video_files:
                raise FileNotFoundError("未找到生成的视频文件")
            
            # 返回最新的视频文件
            latest_video = max(video_files, key=os.path.getctime)
            return str(latest_video)
            
        except Exception as e:
            logger.error(f"视频生成过程中发生错误: {str(e)}")
            raise
    
    async def process_tts_output(self, tts_output: bytes, audio_format: str = "mp3") -> str:
        """
        处理TTS输出生成视频
        
        Args:
            tts_output: TTS生成的音频数据
            audio_format: 音频格式
            
        Returns:
            生成的视频文件路径
        """
        try:
            # 保存音频到文件
            audio_path = await self.save_audio_to_file(tts_output, audio_format)
            
            # 生成视频
            video_path = await self.generate_video_from_audio(audio_path)
            
            return video_path
        except Exception as e:
            logger.error(f"处理TTS输出时发生错误: {str(e)}")
            raise
    
    async def process_base64_audio(self, base64_audio: str, audio_format: str = "mp3") -> str:
        """
        处理Base64编码的音频数据生成视频
        
        Args:
            base64_audio: Base64编码的音频数据
            audio_format: 音频格式
            
        Returns:
            生成的视频文件路径
        """
        try:
            # 解码Base64音频数据
            audio_data = base64.b64decode(base64_audio)
            
            # 处理音频数据生成视频
            return await self.process_tts_output(audio_data, audio_format)
        except Exception as e:
            logger.error(f"处理Base64音频时发生错误: {str(e)}")
            raise

    @staticmethod
    async def get_available_pose_dirs(echomimic_path: str = "/Users/niko/echomimic_v2") -> List[str]:
        """
        获取EchoMimicV2资产目录下可用的姿势数据集列表
        
        Args:
            echomimic_path: EchoMimicV2项目路径
            
        Returns:
            可用姿势数据集的目录名列表
        """
        assets_path = Path(echomimic_path) / "assets"
        pose_dirs = []
        
        if assets_path.exists() and assets_path.is_dir():
            for item in assets_path.iterdir():
                if item.is_dir() and (item / "0.npy").exists():
                    pose_dirs.append(str(item))
        
        return pose_dirs
    
    @staticmethod
    async def get_available_reference_images(echomimic_path: str = "/Users/niko/echomimic_v2") -> List[str]:
        """
        获取EchoMimicV2资产目录下可用的参考图像列表
        
        Args:
            echomimic_path: EchoMimicV2项目路径
            
        Returns:
            可用参考图像的文件路径列表
        """
        assets_path = Path(echomimic_path) / "assets"
        ref_images = []
        
        if assets_path.exists() and assets_path.is_dir():
            for item in assets_path.glob("**/*.png"):
                if item.is_file() and "reference" in item.name.lower():
                    ref_images.append(str(item))
            
            for item in assets_path.glob("**/*.jpg"):
                if item.is_file() and "reference" in item.name.lower():
                    ref_images.append(str(item))
        
        return ref_images
