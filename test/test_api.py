"""
测试API模块
提供用于测试数字人功能的简单API
"""

import os
import base64
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, Optional

from minimax_integration import get_minimax_integration

# 配置日志
logger = logging.getLogger(__name__)

# 创建API路由
test_router = APIRouter(prefix="/test", tags=["测试"])

# 初始化MiniMax集成实例
minimax = get_minimax_integration()

@test_router.get("/")
async def test_index():
    """测试首页，重定向到静态测试页面"""
    return {"url": "/static/test/index.html"}

@test_router.post("/tts")
async def test_tts(request: Request):
    """测试文本转语音API"""
    try:
        # 获取请求数据
        data = await request.json()
        text = data.get("text", "")
        voice_id = data.get("voice_id", "female-general-24")
        provider = data.get("provider", "minimax")
        
        if not text:
            raise HTTPException(status_code=400, detail="文本不能为空")
        
        # 调用MiniMax TTS API
        result = await minimax.text_to_speech(
            text=text,
            voice_id=voice_id,
            use_cache=True
        )
        
        if not result.get("success"):
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": result.get("error", "语音合成失败")
                }
            )
        
        # 获取音频数据和信息
        audio_data = result.get("audio_data", b"")
        if not audio_data:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "未获取到音频数据"
                }
            )
        
        # 将二进制音频数据转换为base64编码
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        
        return {
            "success": True,
            "audio_data": audio_base64,
            "duration": result.get("duration", 0),
            "cached": result.get("cached", False),
            "format": result.get("format", "mp3")
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"TTS测试API错误: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@test_router.post("/config")
async def update_test_config(request: Request):
    """更新测试配置"""
    try:
        # 获取请求数据
        data = await request.json()
        llm = data.get("llm", "google")
        stt = data.get("stt", "deepgram")
        tts = data.get("tts", "google")
        
        # 这里只是模拟更新配置，实际项目中应该保存到用户会话或数据库
        # 在实际项目中，这些配置可能会通过WebSocket连接传递
        
        return {
            "success": True,
            "config": {
                "llm": llm,
                "stt": stt,
                "tts": tts
            }
        }
        
    except Exception as e:
        logger.error(f"更新测试配置错误: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

# 添加测试API到应用的函数
def add_test_routes(app):
    """将测试路由添加到FastAPI应用"""
    # 添加API路由
    app.include_router(test_router, prefix="/api")
    
    # 添加静态文件路由
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # 添加路由重定向
    @app.get("/test")
    async def redirect_to_test():
        """重定向到测试页面"""
        return {"url": "/static/test/index.html"}
