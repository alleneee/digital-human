"""
WebSocket服务器独立运行脚本
"""
import uvicorn
import logging
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json

# 从app.py导入必要的组件和功能
from app import (
    manager, is_deepgram_available, webrtc_handler, DEFAULT_LANGUAGE,
    process_audio, process_text_input, stop_talking, WebSocketDisconnect
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title="WebSocket Server")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    # 从查询参数中获取客户端ID，如果没有则生成唯一ID
    client_id = websocket.query_params.get("client_id")
    connection_id = client_id if client_id else str(id(websocket))
    logger.info(f"新的WebSocket连接: {connection_id}")
    
    # 接受连接
    await manager.connect(websocket, connection_id)
    
    try:
        # 检查WebRTC和Deepgram可用性
        deepgram_available = is_deepgram_available()
        logger.info(f"Deepgram可用性状态: {deepgram_available}")
        
        # 通知客户端WebRTC支持状态
        await manager.send_message(connection_id, {
            "type": "webrtc_support",
            "supported": deepgram_available
        })
        
        # 如果Deepgram可用，为此连接创建WebRTC会话
        if deepgram_available:
            logger.info(f"为连接 {connection_id} 创建WebRTC会话")
            
            # 定义消息回调函数
            async def send_transcription(conn_id, message):
                await manager.send_message(conn_id, message)
            
            # 创建WebRTC连接
            success = await webrtc_handler.create_connection(
                connection_id=connection_id,
                message_callback=send_transcription,
                language=manager.get_user_config(connection_id).get("language", DEFAULT_LANGUAGE)
            )
            
            if not success:
                logger.warning(f"无法为连接 {connection_id} 创建WebRTC会话")
        
        # 初始化音频处理器和LLM
        manager.initialize_audio_processor(connection_id)
        manager.initialize_llm(connection_id)
        
        # 主消息循环
        while True:
            # 等待接收消息
            data = await websocket.receive()
            
            # 处理二进制数据 (音频)
            if "bytes" in data:
                logger.debug(f"收到二进制数据 {len(data['bytes'])} 字节")
                
                # 如果WebRTC可用，使用WebRTC处理音频
                if deepgram_available and webrtc_handler.is_connected(connection_id):
                    await webrtc_handler.process_audio(connection_id, data["bytes"])
                else:
                    # 否则使用WebSocket处理音频
                    asyncio.create_task(process_audio(connection_id, data["bytes"]))
            
            # 处理文本数据 (JSON)
            elif "text" in data:
                logger.debug(f"收到文本数据: {data['text'][:100]}...")
                
                try:
                    # 解析JSON消息
                    message = json.loads(data["text"])
                    
                    # 根据消息类型处理
                    if message.get("type") == "text_input":
                        # 处理文本输入
                        text = message.get("text", "").strip()
                        if text:
                            asyncio.create_task(process_text_input(connection_id, text))
                    
                    elif message.get("type") == "config":
                        # 更新配置
                        config = message.get("config", {})
                        logger.info(f"更新用户配置: {config}")
                        
                        # 更新配置
                        manager.update_user_config(connection_id, config)
                        
                        # 如果语言设置变更且WebRTC处于活动状态，更新WebRTC语言设置
                        if deepgram_available and webrtc_handler.is_connected(connection_id):
                            language = config.get("language", DEFAULT_LANGUAGE)
                            await webrtc_handler.update_language(connection_id, language)
                    
                    elif message.get("type") == "ping":
                        # 处理ping消息，发送pong响应
                        await manager.send_message(connection_id, {"type": "pong"})
                    
                    elif message.get("type") == "stop_talking":
                        # 停止当前的语音合成
                        stop_talking(connection_id)
                except json.JSONDecodeError:
                    logger.error(f"无法解析JSON消息: {data['text']}")
    
    except WebSocketDisconnect:
        # 处理WebSocket断开
        logger.info(f"WebSocket连接关闭: {connection_id}")
        manager.disconnect(connection_id)
        
        # 关闭WebRTC连接如果存在
        if is_deepgram_available() and webrtc_handler.is_connected(connection_id):
            await webrtc_handler.close_connection(connection_id)
    except Exception as e:
        # 处理其他异常
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(connection_id)

if __name__ == "__main__":
    try:
        logger.info("启动WebSocket服务器在端口8001...")
        uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")
    except Exception as e:
        logger.critical(f"WebSocket服务器启动失败: {e}")
