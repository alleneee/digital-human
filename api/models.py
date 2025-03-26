# -*- coding: utf-8 -*-
'''
API数据模型定义
'''

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

# 视频生成相关模型

class VideoGenerationRequest(BaseModel):
    """视频生成请求模型"""
    audio_data: str = Field(..., description="Base64编码的音频数据")
    audio_format: str = Field(default="mp3", description="音频格式，例如：wav, mp3")
    ref_image_path: Optional[str] = Field(default=None, description="参考图像路径")
    pose_dir_path: Optional[str] = Field(default=None, description="姿势数据目录路径")

class TextToVideoRequest(BaseModel):
    """文本到视频生成请求模型"""
    text: str = Field(..., description="待合成文本")
    voice_id: Optional[str] = Field(default=None, description="语音ID")
    ref_image_path: Optional[str] = Field(default=None, description="参考图像路径")
    pose_dir_path: Optional[str] = Field(default=None, description="姿势数据目录路径")

class VideoGenerationResponse(BaseModel):
    """视频生成响应模型"""
    video_path: str = Field(..., description="生成的视频文件路径")
    took_ms: float = Field(..., description="处理耗时(毫秒)")

# Agent相关模型

class AgentRequest(BaseModel):
    """Agent请求模型"""
    query: str = Field(..., description="用户查询")
    conversation_id: Optional[str] = Field(default=None, description="对话ID(用于上下文跟踪)")
    use_tools: Optional[bool] = Field(default=True, description="是否允许使用工具")
    context: Optional[Dict[str, Any]] = Field(default=None, description="额外上下文信息")

class AgentResponse(BaseModel):
    """Agent响应模型"""
    text: str = Field(..., description="回复文本")
    took_ms: float = Field(..., description="处理耗时(毫秒)")
    run_id: Optional[str] = Field(default=None, description="运行ID")
    tools_used: Optional[List[str]] = Field(default=None, description="使用的工具列表")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="其他元数据")
