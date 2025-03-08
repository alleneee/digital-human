# -*- coding: utf-8 -*-
'''
API路由模块，提供HTTP接口
'''

import logging
import base64
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, File, UploadFile, Body, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from utils.protocol import AudioMessage, TextMessage, AudioFormatType
from utils.singleton import Singleton
import asyncio
import tempfile
import os
import time
import uuid

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api", tags=["数字人API"])

# 定义请求模型
class AudioChatRequest(BaseModel):
    """音频对话请求模型"""
    audio_data: str = Field(..., description="Base64编码的音频数据")
    audio_format: str = Field(default="wav", description="音频格式，例如：wav, mp3")
    sample_rate: int = Field(default=16000, description="采样率")
    sample_width: int = Field(default=2, description="采样宽度")
    context_id: Optional[str] = Field(default=None, description="对话上下文ID")
    skip_asr: bool = Field(default=False, description="是否跳过语音识别")
    skip_llm: bool = Field(default=False, description="是否跳过语言模型")
    skip_tts: bool = Field(default=False, description="是否跳过语音合成")

class TextChatRequest(BaseModel):
    """文本对话请求模型"""
    text: str = Field(..., description="输入文本")
    context_id: Optional[str] = Field(default=None, description="对话上下文ID")
    skip_tts: bool = Field(default=False, description="是否跳过语音合成")

class ASRRequest(BaseModel):
    """语音识别请求模型"""
    audio_data: str = Field(..., description="Base64编码的音频数据")
    audio_format: str = Field(default="wav", description="音频格式，例如：wav, mp3")
    sample_rate: int = Field(default=16000, description="采样率")
    sample_width: int = Field(default=2, description="采样宽度")

class TTSRequest(BaseModel):
    """语音合成请求模型"""
    text: str = Field(..., description="待合成文本")
    voice_id: Optional[str] = Field(default=None, description="语音ID")

# 定义响应模型
class AudioChatResponse(BaseModel):
    """音频对话响应模型"""
    input_text: Optional[str] = Field(default=None, description="识别的输入文本")
    response_text: str = Field(..., description="回复文本")
    audio_data: Optional[str] = Field(default=None, description="Base64编码的音频数据")
    audio_format: Optional[str] = Field(default=None, description="音频格式")
    sample_rate: Optional[int] = Field(default=None, description="采样率")
    sample_width: Optional[int] = Field(default=None, description="采样宽度")
    context_id: str = Field(..., description="对话上下文ID")
    took_ms: float = Field(..., description="处理耗时(毫秒)")

class TextChatResponse(BaseModel):
    """文本对话响应模型"""
    response_text: str = Field(..., description="回复文本")
    audio_data: Optional[str] = Field(default=None, description="Base64编码的音频数据")
    audio_format: Optional[str] = Field(default=None, description="音频格式")
    sample_rate: Optional[int] = Field(default=None, description="采样率")
    sample_width: Optional[int] = Field(default=None, description="采样宽度")
    context_id: str = Field(..., description="对话上下文ID")
    took_ms: float = Field(..., description="处理耗时(毫秒)")

class ASRResponse(BaseModel):
    """语音识别响应模型"""
    text: str = Field(..., description="识别结果文本")
    took_ms: float = Field(..., description="处理耗时(毫秒)")
    
class TTSResponse(BaseModel):
    """语音合成响应模型"""
    audio_data: str = Field(..., description="Base64编码的音频数据")
    audio_format: str = Field(..., description="音频格式")
    sample_rate: int = Field(..., description="采样率")
    sample_width: int = Field(..., description="采样宽度")
    took_ms: float = Field(..., description="处理耗时(毫秒)")

# 实现API路由
class APIService(metaclass=Singleton):
    """API服务类，管理会话和引擎实例"""
    
    def __init__(self):
        """初始化API服务"""
        self.contexts = {}  # 存储对话上下文
        self.pipeline = None  # 对话流水线实例
        self.speech_processor = None  # 语音处理器实例
        
    def set_pipeline(self, pipeline):
        """设置对话流水线实例"""
        self.pipeline = pipeline
        
    def set_speech_processor(self, speech_processor):
        """设置语音处理器实例"""
        self.speech_processor = speech_processor
        
    def get_context(self, context_id: str) -> Dict[str, Any]:
        """获取对话上下文"""
        if not context_id or context_id not in self.contexts:
            # 创建新的上下文
            context_id = context_id or str(uuid.uuid4())
            self.contexts[context_id] = {
                "messages": [],
                "created_at": time.time(),
                "last_access": time.time()
            }
        else:
            # 更新访问时间
            self.contexts[context_id]["last_access"] = time.time()
            
        return self.contexts[context_id]
    
    def update_context(self, context_id: str, message: Dict[str, Any]):
        """更新对话上下文"""
        context = self.get_context(context_id)
        context["messages"].append(message)
        
    def clear_old_contexts(self, max_age_hours: int = 24):
        """清理旧的上下文"""
        now = time.time()
        old_contexts = []
        
        for context_id, context in self.contexts.items():
            age_hours = (now - context["last_access"]) / 3600
            if age_hours > max_age_hours:
                old_contexts.append(context_id)
                
        for context_id in old_contexts:
            del self.contexts[context_id]
            
        return len(old_contexts)

# 创建全局API服务实例
api_service = APIService()

def get_api_service():
    """获取API服务实例"""
    return api_service

@router.post("/audio_chat", response_model=AudioChatResponse)
async def audio_chat(request: AudioChatRequest, api_service: APIService = Depends(get_api_service)):
    """音频对话接口"""
    start_time = time.time()
    
    # 检查是否初始化
    if not api_service.pipeline:
        raise HTTPException(status_code=500, detail="对话流水线未初始化")
    
    try:
        # 解码音频数据
        audio_data = base64.b64decode(request.audio_data)
        
        # 构建音频消息
        audio_format = AudioFormatType(request.audio_format)
        audio_message = AudioMessage(
            data=audio_data,
            format=audio_format,
            sampleRate=request.sample_rate,
            sampleWidth=request.sample_width
        )
        
        # 获取上下文
        context_id = request.context_id or str(uuid.uuid4())
        context = api_service.get_context(context_id)["messages"]
        
        # 处理对话
        result = await api_service.pipeline.process(
            audio_input=audio_message,
            conversation_context=context,
            skip_asr=request.skip_asr,
            skip_llm=request.skip_llm,
            skip_tts=request.skip_tts
        )
        
        # 检查处理是否出错
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # 构建响应
        response = {
            "input_text": result.get("input_text"),
            "response_text": result.get("response_text", ""),
            "context_id": context_id,
            "took_ms": (time.time() - start_time) * 1000
        }
        
        # 如果有音频输出，添加到响应
        audio_output = result.get("audio_output")
        if audio_output:
            response["audio_data"] = base64.b64encode(audio_output.data).decode("utf-8")
            response["audio_format"] = audio_output.format.value
            response["sample_rate"] = audio_output.sampleRate
            response["sample_width"] = audio_output.sampleWidth
        
        # 更新上下文
        api_service.update_context(context_id, {
            "role": "user",
            "content": result.get("input_text", "")
        })
        api_service.update_context(context_id, {
            "role": "assistant",
            "content": result.get("response_text", "")
        })
        
        return response
    
    except Exception as e:
        logger.error(f"音频对话处理错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/text_chat", response_model=TextChatResponse)
async def text_chat(request: TextChatRequest, api_service: APIService = Depends(get_api_service)):
    """文本对话接口"""
    start_time = time.time()
    
    # 检查是否初始化
    if not api_service.pipeline:
        raise HTTPException(status_code=500, detail="对话流水线未初始化")
    
    try:
        # 获取上下文
        context_id = request.context_id or str(uuid.uuid4())
        context = api_service.get_context(context_id)["messages"]
        
        # 处理文本对话
        llm_result = await api_service.pipeline.llm_only(
            text_input=request.text,
            conversation_context=context
        )
        
        if not llm_result:
            raise HTTPException(status_code=500, detail="语言模型处理失败")
        
        response_text = llm_result.data
        
        # 构建响应
        response = {
            "response_text": response_text,
            "context_id": context_id,
            "took_ms": (time.time() - start_time) * 1000
        }
        
        # 如果不跳过TTS，生成语音
        if not request.skip_tts:
            audio_output = await api_service.pipeline.tts_only(response_text)
            
            if audio_output:
                response["audio_data"] = base64.b64encode(audio_output.data).decode("utf-8")
                response["audio_format"] = audio_output.format.value
                response["sample_rate"] = audio_output.sampleRate
                response["sample_width"] = audio_output.sampleWidth
        
        # 更新上下文
        api_service.update_context(context_id, {
            "role": "user",
            "content": request.text
        })
        api_service.update_context(context_id, {
            "role": "assistant",
            "content": response_text
        })
        
        return response
    
    except Exception as e:
        logger.error(f"文本对话处理错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/asr", response_model=ASRResponse)
async def speech_recognition(request: ASRRequest, api_service: APIService = Depends(get_api_service)):
    """语音识别接口"""
    start_time = time.time()
    
    # 检查是否初始化
    if not api_service.pipeline:
        raise HTTPException(status_code=500, detail="对话流水线未初始化")
    
    try:
        # 解码音频数据
        audio_data = base64.b64decode(request.audio_data)
        
        # 构建音频消息
        audio_format = AudioFormatType(request.audio_format)
        audio_message = AudioMessage(
            data=audio_data,
            format=audio_format,
            sampleRate=request.sample_rate,
            sampleWidth=request.sample_width
        )
        
        # 进行语音识别
        result = await api_service.pipeline.asr_only(audio_message)
        
        if not result:
            raise HTTPException(status_code=500, detail="语音识别失败")
        
        # 构建响应
        response = {
            "text": result.data,
            "took_ms": (time.time() - start_time) * 1000
        }
        
        return response
    
    except Exception as e:
        logger.error(f"语音识别处理错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest, api_service: APIService = Depends(get_api_service)):
    """语音合成接口"""
    start_time = time.time()
    
    # 检查是否初始化
    if not api_service.pipeline:
        raise HTTPException(status_code=500, detail="对话流水线未初始化")
    
    try:
        # 进行语音合成
        result = await api_service.pipeline.tts_only(request.text)
        
        if not result:
            raise HTTPException(status_code=500, detail="语音合成失败")
        
        # 构建响应
        response = {
            "audio_data": base64.b64encode(result.data).decode("utf-8"),
            "audio_format": result.format.value,
            "sample_rate": result.sampleRate,
            "sample_width": result.sampleWidth,
            "took_ms": (time.time() - start_time) * 1000
        }
        
        return response
    
    except Exception as e:
        logger.error(f"语音合成处理错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "timestamp": time.time()}
