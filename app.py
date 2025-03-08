# app.py
import os
import asyncio
import json
import logging
import uvicorn
import tempfile
import base64
import shutil
import time
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File
from fastapi import BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from dotenv import load_dotenv
from datetime import datetime

# 导入测试API模块 - 暂时注释掉，因为模块不存在
# from test_api import add_test_routes

# 导入自定义模块
from audio_processor import AudioProcessor
from deepgram_integration import setup_live_transcription, detect_audio_format
from echomimic_integration import get_echomimic_generator
from webrtc_integration import webrtc_handler, is_deepgram_available
from minimax_integration import get_minimax_integration  # 导入MiniMax集成模块

# 导入LangChain和Gemini相关库
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 将日志级别从INFO改为DEBUG以获取更多信息
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("digital_human.log")
    ]
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MINIMAX_GROUP_ID = os.getenv("MINIMAX_GROUP_ID", "")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")

# 常量定义
DEFAULT_LANGUAGE = "zh-CN"
DEFAULT_VOICE = "aura-mandarin"

# API提供商配置
API_PROVIDERS = {
    "llm": ["google", "minimax"],  # 大语言模型提供商
    "stt": ["deepgram", "minimax"],  # 语音识别提供商
    "tts": ["google", "minimax"]  # 语音合成提供商
}

# 默认提供商设置
DEFAULT_PROVIDERS = {
    "llm": "google",
    "stt": "deepgram",
    "tts": "google"
}

# 创建FastAPI应用
app = FastAPI(title="数字人助手")

# 注意：先注册所有API路由，最后再挂载静态文件！
# WebSocket和API路由将在代码后面定义

# 这里暂时不挂载静态文件，将在所有API路由注册后再挂载
# 静态文件挂载将移动到文件末尾

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化LLM对话链
def create_llm_chain():
    """创建LangChain对话链，使用Gemini模型"""
    try:
        # 设置Gemini配置
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=GOOGLE_API_KEY,
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=800
        )
        
        # 设置提示模板
        template = """你是一个友好的AI数字人助手，名叫"小智"。你由Deepgram处理语音，由Google Gemini提供思考能力。
        
        请用自然、温暖、亲切的语气回答问题。你应该:
        - 给出简洁明了的回答，避免冗长
        - 表现出活泼、乐观的性格
        - 适当展示一些幽默感
        - 保持礼貌和专业性
        
        当前对话历史:
        {history}
        
        人类: {input}
        小智:"""
        
        prompt = PromptTemplate(
            input_variables=["history", "input"],
            template=template
        )
        
        # 设置会话记忆
        memory = ConversationBufferMemory(return_messages=True)
        
        # 创建对话链
        conversation_chain = ConversationChain(
            llm=llm,
            prompt=prompt,
            memory=memory,
            verbose=False
        )
        
        return conversation_chain
    
    except Exception as e:
        logger.error(f"创建LLM对话链失败: {e}")
        return None

# 分析文本生成表情动作控制信号
def analyze_response_for_animation(text):
    """分析回复文本，生成数字人表情和动作控制信号"""
    # 默认动画状态
    animation = {
        "expression": "neutral",  # 表情: neutral, happy, sad, surprised, angry, thinking
        "motion": "talking",      # 动作: idle, talking, nodding, thinking, greeting
        "intensity": 0.5,         # 强度: 0.0-1.0
        "duration": 2.0           # 持续时间(秒)
    }
    
    # 基于文本内容检测表情
    happy_words = ["高兴", "开心", "好", "棒", "喜欢", "爱", "感谢", "谢谢", "不错", "很好"]
    sad_words = ["悲伤", "难过", "伤心", "抱歉", "对不起", "遗憾", "可惜", "失望"]
    surprised_words = ["惊讶", "哇", "真的吗", "不会吧", "厉害", "难以置信", "意想不到"]
    thinking_words = ["思考", "让我想想", "考虑", "我认为", "可能", "也许", "推测", "分析"]
    angry_words = ["生气", "不满", "不行", "错误", "不对", "不能", "严重"]
    
    # 检测表情
    if any(word in text for word in happy_words):
        animation["expression"] = "happy"
        animation["motion"] = "nodding"
        animation["intensity"] = 0.7
    elif any(word in text for word in sad_words):
        animation["expression"] = "sad"
        animation["motion"] = "idle"
        animation["intensity"] = 0.6
    elif any(word in text for word in surprised_words):
        animation["expression"] = "surprised"
        animation["motion"] = "surprised"
        animation["intensity"] = 0.8
    elif any(word in text for word in thinking_words):
        animation["expression"] = "thinking"
        animation["motion"] = "thinking"
        animation["intensity"] = 0.5
    elif any(word in text for word in angry_words):
        animation["expression"] = "angry"
        animation["motion"] = "talking"
        animation["intensity"] = 0.6
    else:
        # 默认说话状态
        animation["expression"] = "neutral"
        animation["motion"] = "talking"
        animation["intensity"] = 0.5
    
    # 根据文本长度设置动画持续时间
    animation["duration"] = min(max(len(text) * 0.15, 2.0), 10.0)  # 2-10秒
    
    # 检测问题
    if "？" in text or "?" in text:
        animation["is_question"] = True
    
    return animation

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections = {}
        self.llm_chains = {}
        self.audio_processors = {}
        self.user_configs = {}
        self.connection_start_times = {}
        self.last_ping_times = {}
        self.connection_latencies = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """处理新的WebSocket连接"""
        # 接受连接
        await websocket.accept()
        
        # 保存连接
        self.active_connections[connection_id] = websocket
        
        # 为连接创建LLM对话链
        self.llm_chains[connection_id] = create_llm_chain()
        
        # 创建音频处理器
        self.audio_processors[connection_id] = AudioProcessor(DEFAULT_LANGUAGE)
        
        # 初始化用户配置
        self.user_configs[connection_id] = {
            "language": DEFAULT_LANGUAGE,
            "voice": DEFAULT_VOICE,
            "theme": "light",
            "providers": {
                "llm": DEFAULT_PROVIDERS["llm"],
                "stt": DEFAULT_PROVIDERS["stt"],
                "tts": DEFAULT_PROVIDERS["tts"]
            },
            "use_echomimic": True,
            "ref_image_path": None
        }
        
        logger.info(f"新连接: {connection_id}")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """处理WebSocket断开连接"""
        if connection_id not in self.active_connections:
            # 如果连接已经不存在，则跳过
            logger.debug(f"尝试断开已不存在的连接: {connection_id}")
            return
            
        logger.info(f"正在断开连接: {connection_id}")
        
        try:
            # 关闭实时转录
            if connection_id in self.audio_processors:
                try:
                    # 尝试清理音频处理器资源
                    audio_processor = self.audio_processors[connection_id]
                    # 如果音频处理器有close或cleanup方法，可以在这里调用
                    logger.debug(f"已清理音频处理器: {connection_id}")
                except Exception as e:
                    logger.warning(f"清理音频处理器时出错: {connection_id} - {str(e)}")
                finally:
                    del self.audio_processors[connection_id]
            
            # 清理LLM资源
            if connection_id in self.llm_chains:
                try:
                    # 清理LLM资源，如果有需要的话
                    logger.debug(f"已清理LLM资源: {connection_id}")
                except Exception as e:
                    logger.warning(f"清理LLM资源时出错: {connection_id} - {str(e)}")
                finally:
                    del self.llm_chains[connection_id]
                    
            # 清理用户配置
            if connection_id in self.user_configs:
                del self.user_configs[connection_id]
                logger.debug(f"已清理用户配置: {connection_id}")
            
            # 尝试关闭WebSocket连接（如果还没关闭）
            try:
                websocket = self.active_connections[connection_id]
                await websocket.close()
                logger.debug(f"已关闭WebSocket连接: {connection_id}")
            except Exception as e:
                # 可能已经关闭，忽略错误
                logger.debug(f"关闭WebSocket时出错(可能已关闭): {connection_id} - {str(e)}")
            
            # 删除连接引用
            del self.active_connections[connection_id]
            
            logger.info(f"连接已成功断开并清理: {connection_id}")
        
        except Exception as e:
            logger.error(f"断开连接过程中发生错误: {connection_id} - {str(e)}", exc_info=True)
            # 确保连接被移除，即使发生错误
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
    
    async def initialize_audio_processor(self, connection_id: str):
        """初始化指定连接的音频处理器"""
        if connection_id not in self.audio_processors:
            self.audio_processors[connection_id] = AudioProcessor(DEFAULT_LANGUAGE)
            logger.info(f"已为连接初始化音频处理器: {connection_id}")
    
    async def initialize_llm(self, connection_id: str):
        """初始化指定连接的LLM实例"""
        if connection_id not in self.llm_chains:
            # 这里根据需要初始化LLM
            self.llm_chains[connection_id] = create_llm_chain()
            logger.info(f"已为连接初始化LLM: {connection_id}")
    
    async def send_message(self, connection_id: str, message: dict):
        """向指定连接发送JSON消息"""
        try:
            if connection_id in self.active_connections:
                try:
                    await self.active_connections[connection_id].send_json(message)
                    return True
                except RuntimeError as e:
                    if "disconnect" in str(e).lower() or "closed" in str(e).lower():
                        logger.warning(f"发送消息到已断开的连接: {connection_id} - {str(e)}")
                        await self.disconnect(connection_id)
                    else:
                        logger.error(f"发送JSON消息错误: {connection_id} - {str(e)}")
                    return False
            else:
                logger.warning(f"尝试发送消息到不存在的连接: {connection_id}")
                return False
        
        except Exception as e:
            logger.error(f"发送消息时发生未知错误: {str(e)}", exc_info=True)
            await self.disconnect(connection_id)
            return False
    
    async def send_bytes(self, connection_id: str, data: bytes):
        """向指定连接发送二进制数据"""
        try:
            if connection_id in self.active_connections:
                try:
                    await self.active_connections[connection_id].send_bytes(data)
                    return True
                except RuntimeError as e:
                    if "disconnect" in str(e).lower() or "closed" in str(e).lower():
                        logger.warning(f"发送二进制数据到已断开的连接: {connection_id} - {str(e)}")
                        await self.disconnect(connection_id)
                    else:
                        logger.error(f"发送二进制数据错误: {connection_id} - {str(e)}")
                    return False
            else:
                logger.warning(f"尝试发送二进制数据到不存在的连接: {connection_id}")
                return False
        
        except Exception as e:
            logger.error(f"发送二进制数据时发生未知错误: {str(e)}", exc_info=True)
            await self.disconnect(connection_id)
            return False
    
    def get_llm_chain(self, connection_id: str):
        """获取指定连接的LLM对话链"""
        return self.llm_chains.get(connection_id)
        
    def get_audio_processor(self, connection_id: str):
        """获取指定连接的音频处理器"""
        return self.audio_processors.get(connection_id)
        
    def update_user_config(self, connection_id: str, config: dict):
        """更新用户配置"""
        if connection_id in self.user_configs:
            # 更新配置
            self.user_configs[connection_id].update(config)
            
            # 更新语言和语音设置
            if "language" in config and connection_id in self.audio_processors:
                self.audio_processors[connection_id].set_language(config["language"])
                
            if "voice" in config and connection_id in self.audio_processors:
                self.audio_processors[connection_id].set_voice(config["voice"])
                
            logger.info(f"已更新用户配置 {connection_id}: {config}")
            return True
            
        return False
        
    def get_user_config(self, connection_id: str):
        """获取用户配置"""
        return self.user_configs.get(connection_id, {})
        
    async def handle_ping(self, connection_id: str, ping_id: str, client_timestamp: float):
        """处理来自客户端的ping请求"""
        server_timestamp = time.time()
        latency = server_timestamp - client_timestamp
        
        # 更新最后一次ping时间和连接延迟
        self.last_ping_times[connection_id] = server_timestamp
        self.connection_latencies[connection_id] = latency
        
        # 返回pong响应
        await self.send_message(connection_id, {
            "type": "pong",
            "ping_id": ping_id,
            "client_timestamp": client_timestamp,
            "server_timestamp": server_timestamp,
            "latency": latency
        })
        
        logger.debug(f"Ping-Pong: 连接ID {connection_id}, 延迟: {latency:.2f}秒")
        
    def get_connection_status(self, connection_id: str):
        """获取连接状态信息"""
        if connection_id not in self.active_connections:
            return None
            
        return {
            "id": connection_id,
            "connected": True,
            "connected_since": self.connection_start_times.get(connection_id, 0),
            "latency": self.connection_latencies.get(connection_id, 0),
            "last_ping": self.last_ping_times.get(connection_id, 0)
        }

# 创建连接管理器
manager = ConnectionManager()

# WebSocket端点
# 修改为如下形式，确保正常处理WebSocket请求
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.info(f"新的WebSocket连接请求到/api/ws")
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
        # 正确地await协程函数
        await manager.initialize_audio_processor(connection_id)
        await manager.initialize_llm(connection_id)
        
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
                    
                    elif message.get("type") == "recording_started":
                        # 用户开始录音
                        logger.info(f"用户开始录音: {connection_id}")
                    
                    elif message.get("type") == "recording_stopped":
                        # 用户停止录音
                        logger.info(f"用户停止录音: {connection_id}")
                    
                    elif message.get("type") == "audio_input":
                        # 音频输入格式通知（处理后续二进制数据）
                        format_hint = message.get("format")
                        logger.info(f"即将处理音频输入，格式: {format_hint}")
                        
                        # 确认客户端音频已接收
                        await manager.send_message(connection_id, {
                            "type": "audio_received",
                            "format": format_hint,
                            "size": message.get("size", 0)
                        })
                    
                    elif message.get("type") == "transcription":
                        # 处理来自客户端的转写结果
                        text = message.get("text", "").strip()
                        is_final = message.get("final", False)
                        
                        if text and is_final:
                            logger.info(f"处理客户端转写: {text}")
                            asyncio.create_task(process_text_input(connection_id, text))
                    
                    elif message.get("type") == "ping":
                        # 处理ping请求
                        ping_id = message.get("ping_id", str(time.time()))
                        client_timestamp = message.get("timestamp", time.time())
                        await manager.handle_ping(connection_id, ping_id, client_timestamp)
                    
                    elif message.get("type") == "cached_messages":
                        # 处理客户端断线后重新发送的缓存消息
                        cached_messages = message.get("messages", [])
                        if cached_messages:
                            logger.info(f"处理客户端缓存消息: {len(cached_messages)} 条")
                            
                            # 按序处理所有缓存消息
                            for cached_msg in cached_messages:
                                msg_type = cached_msg.get("type")
                                
                                if msg_type == "text_input":
                                    text = cached_msg.get("text", "").strip()
                                    if text:
                                        asyncio.create_task(process_text_input(connection_id, text))
                                        
                                elif msg_type == "transcription":
                                    text = cached_msg.get("text", "").strip()
                                    is_final = cached_msg.get("final", False)
                                    if text and is_final:
                                        asyncio.create_task(process_text_input(connection_id, text))
                                        
                            # 发送确认消息
                            await manager.send_message(connection_id, {
                                "type": "cached_messages_received",
                                "count": len(cached_messages),
                                "timestamp": time.time()
                            })
                    
                    elif message.get("type") == "connection_status_request":
                        # 客户端请求连接状态信息
                        status = manager.get_connection_status(connection_id)
                        if status:
                            await manager.send_message(connection_id, {
                                "type": "connection_status",
                                "status": "connected",
                                **status,
                                "timestamp": time.time()
                            })
                    
                    else:
                        logger.warning(f"未知的消息类型: {message.get('type')}")
                
                except json.JSONDecodeError:
                    logger.error(f"无法解析JSON消息: {data['text'][:100]}...")
                except Exception as e:
                    logger.error(f"处理消息时出错: {str(e)}", exc_info=True)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket断开连接: {connection_id}")
    except RuntimeError as re:
        # 处理连接已断开的服务器错误
        if "disconnect message has been received" in str(re):
            logger.info(f"WebSocket已断开: {connection_id}")
        else:
            logger.error(f"WebSocket运行时错误: {str(re)}", exc_info=True)
    except Exception as e:
        logger.error(f"WebSocket处理出错: {str(e)}", exc_info=True)
    finally:
        try:
            # 关闭WebRTC连接
            if deepgram_available:
                try:
                    await webrtc_handler.close_connection(connection_id)
                except Exception as e:
                    logger.error(f"WebRTC关闭错误: {str(e)}", exc_info=True)
            
            # 断开WebSocket连接
            await manager.disconnect(connection_id)
        except Exception as e:
            logger.error(f"清理连接资源时出错: {str(e)}", exc_info=True)

# 处理音频数据
async def process_audio(connection_id: str, audio_data: bytes, format_hint: str = None):
    """处理从WebSocket接收到的音频数据"""
    logger.debug(f"开始处理音频，长度: {len(audio_data)} 字节，提示格式: {format_hint}")
    
    # 检查数据有效性
    if not audio_data or len(audio_data) == 0:
        logger.error("收到的音频数据为空")
        await manager.send_message(connection_id, {
            "type": "error",
            "message": "收到的音频数据为空"
        })
        return
    
    # 导入格式检测函数
    from deepgram_integration import detect_audio_format
    
    # 检测音频格式
    detected_format = format_hint
    if not detected_format:
        # 使用deepgram_integration中的检测函数
        detected_format = detect_audio_format(audio_data)
        if detected_format:
            logger.info(f"自动检测到的音频格式: {detected_format}")
        else:
            # 如果无法确定格式，默认使用webm
            detected_format = "audio/webm"
            logger.warning(f"无法检测音频格式，使用默认格式: {detected_format}")
    
    logger.info(f"处理音频数据: {len(audio_data)} 字节, 格式: {detected_format}")
    
    # 尝试使用临时文件保存音频用于调试
    temp_audio_file = None
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.audio', delete=False) as temp:
            temp.write(audio_data)
            temp_audio_file = temp.name
            logger.debug(f"已保存临时音频文件: {temp_audio_file}")
    except Exception as e:
        logger.warning(f"无法保存临时音频文件: {str(e)}")
    
    try:
        # 确保连接存在
        if connection_id not in manager.active_connections:
            logger.error(f"找不到连接ID: {connection_id}")
            return
            
        # 获取用户配置
        user_config = manager.get_user_config(connection_id)
        language = user_config.get("language", "zh-CN")
        logger.debug(f"使用语言设置: {language}")
        
        # 打印音频数据前几个字节用于调试
        prefix_hex = audio_data[:20].hex() if len(audio_data) >= 20 else audio_data.hex()
        logger.debug(f"音频数据前缀: {prefix_hex}")
        
        # 发送转录中的状态
        await manager.send_message(connection_id, {
            "type": "processing",
            "message": "正在处理音频..."
        })
        
        # 获取STT提供商设置
        stt_provider = user_config.get("providers", {}).get("stt", DEFAULT_PROVIDERS["stt"])
        logger.info(f"使用STT提供商: {stt_provider}")
        
        transcript = ""
        
        if stt_provider == "deepgram":
            # 使用Deepgram转录
            audio_processor = manager.get_audio_processor(connection_id)
            if not audio_processor:
                logger.error(f"连接 {connection_id} 没有音频处理器")
                await manager.send_message(connection_id, {
                    "type": "error",
                    "message": "音频处理器未初始化"
                })
                return
            
            # 执行转录
            logger.info("使用Deepgram进行语音转录...")
            transcript = await audio_processor.transcribe(audio_data, language, detected_format)
            
        elif stt_provider == "minimax":
            # 使用MiniMax转录
            logger.info("使用MiniMax进行语音转录...")
            minimax = get_minimax_integration()
            
            # 决定音频格式
            audio_format = "mp3"
            if detected_format:
                if "webm" in detected_format:
                    audio_format = "webm"
                elif "mp3" in detected_format:
                    audio_format = "mp3"
                elif "wav" in detected_format:
                    audio_format = "wav"
            
            # 使用MiniMax API进行转录
            stt_result = await minimax.speech_to_text(audio_data, audio_format)
            
            if stt_result.get("success"):
                transcript = stt_result.get("text", "")
                logger.info(f"MiniMax STT转录成功: '{transcript}'")
            else:
                logger.error(f"MiniMax STT转录失败: {stt_result.get('error')}")
                # 失败时尝试使用Deepgram
                logger.info("回退到Deepgram进行转录...")
                audio_processor = manager.get_audio_processor(connection_id)
                if audio_processor:
                    transcript = await audio_processor.transcribe(audio_data, language, detected_format)
                else:
                    logger.error("音频处理器不可用，无法进行转录")
        else:
            # 未知的STT提供商，使用Deepgram
            logger.warning(f"未知的STT提供商: {stt_provider}，使用Deepgram")
            audio_processor = manager.get_audio_processor(connection_id)
            if audio_processor:
                transcript = await audio_processor.transcribe(audio_data, language, detected_format)
            else:
                logger.error("音频处理器不可用，无法进行转录")
        
        if not transcript:
            logger.warning("音频转录结果为空")
            await manager.send_message(connection_id, {
                "type": "error",
                "message": "无法识别语音输入，请再试一次"
            })
            return
        
        logger.info(f"音频转录结果: {transcript}")
        
        # 将转录文本发送到客户端作为反馈
        await manager.send_message(connection_id, {
            "type": "transcription",
            "text": transcript,
            "final": True
        })
        
        # 处理转录文本
        await process_text_input(connection_id, transcript)
    except Exception as e:
        logger.error(f"处理音频时出错: {e}", exc_info=True)
        if connection_id in manager.active_connections:
            await manager.send_message(connection_id, {
                "type": "error",
                "message": f"处理音频时出错: {str(e)}"
            })
    finally:
        # 清理临时文件
        if temp_audio_file:
            try:
                import os
                os.remove(temp_audio_file)
                logger.debug(f"已删除临时文件: {temp_audio_file}")
            except Exception as e:
                logger.debug(f"清理临时文件时出错: {str(e)}")
        logger.debug("音频处理完成")

# 处理文本输入
async def process_text_input(connection_id: str, text: str):
    """处理文本输入并生成回复"""
    logger.info(f"处理来自连接 {connection_id} 的文本输入: '{text}'")
    try:
        # 获取用户配置
        user_config = manager.get_user_config(connection_id)
        if not user_config:
            user_config = {
                "language": DEFAULT_LANGUAGE,
                "voice": DEFAULT_VOICE,
                "use_echomimic": True,
                "ref_image_path": None,
                "providers": {
                    "llm": DEFAULT_PROVIDERS["llm"],
                    "stt": DEFAULT_PROVIDERS["stt"],
                    "tts": DEFAULT_PROVIDERS["tts"]
                }
            }
        
        # 发送思考中的状态
        await manager.send_message(connection_id, {
            "type": "thinking",
            "message": "思考中..."
        })
        
        # 根据配置选择LLM提供商
        llm_provider = user_config.get("providers", {}).get("llm", DEFAULT_PROVIDERS["llm"])
        logger.info(f"使用LLM提供商: {llm_provider}")
        
        response = "我不明白您在说什么。"
        
        if llm_provider == "google":
            # 使用Google Gemini
            llm_chain = manager.get_llm_chain(connection_id)
            logger.info("LLM链已准备就绪，准备调用Gemini大模型")
            
            # 调用大模型获取回复
            logger.info("开始调用Gemini大模型...")
            # 修复参数名称，LangChain期望的参数是'input'而不是'human_input'
            # 同时使用新的ainvoke API替代已弃用的acall
            llm_response = await llm_chain.ainvoke({"input": text})
            response = llm_response.get("response", "我不明白您在说什么。")
            logger.info(f"Gemini模型返回回复: '{response}'")
            
        elif llm_provider == "minimax":
            # 使用MiniMax
            logger.info("准备调用MiniMax大模型...")
            minimax = get_minimax_integration()
            
            # 构建历史消息
            chat_history = manager.get_chat_history(connection_id) if hasattr(manager, "get_chat_history") else []
            messages = chat_history + [{"role": "user", "content": text}]
            
            # 发送请求到MiniMax
            minimax_response = await minimax.chat_completion(messages)
            
            if minimax_response.get("success"):
                response = minimax_response.get("reply", "我不明白您在说什么。")
                logger.info(f"MiniMax模型返回回复: '{response}'")
                
                # 更新历史
                if hasattr(manager, "update_chat_history"):
                    manager.update_chat_history(connection_id, {
                        "role": "user", 
                        "content": text
                    }, {
                        "role": "assistant", 
                        "content": response
                    })
            else:
                logger.error(f"MiniMax调用失败: {minimax_response.get('error')}")
                response = "非常抱歉，我暂时无法回答您的问题，请稍后再试。"
        else:
            logger.warning(f"未知的LLM提供商: {llm_provider}，使用默认回复")
        
        # 发送回复文本
        await manager.send_message(connection_id, {
            "type": "bot_reply",
            "message": response
        })
        
        # 获取TTS提供商设置
        tts_provider = user_config.get("providers", {}).get("tts", DEFAULT_PROVIDERS["tts"])
        logger.info(f"使用TTS提供商: {tts_provider}")
        
        audio_data = None
        
        if tts_provider == "google":
            # 使用Google TTS
            audio_processor = manager.get_audio_processor(connection_id)
            
            # 生成TTS音频
            logger.info("开始生成Google TTS语音...")
            audio_data = await audio_processor.synthesize(response)
            logger.info(f"Google TTS语音生成完成，大小: {len(audio_data)} 字节")
            
        elif tts_provider == "minimax":
            # 使用MiniMax TTS
            logger.info("开始生成MiniMax TTS语音...")
            minimax = get_minimax_integration()
            
            # 获取语音设置
            voice = user_config.get("voice", DEFAULT_VOICE)
            # 映射到MiniMax支持的语音
            if voice not in ["female-yunjin", "male-qingqing"]:
                voice = "female-yunjin"  # 默认使用女声
                
            # 调用MiniMax TTS API
            tts_result = await minimax.text_to_speech(response, voice=voice)
            
            if tts_result.get("success"):
                audio_data = tts_result.get("audio_data")
                logger.info(f"MiniMax TTS语音生成完成，大小: {len(audio_data)} 字节")
            else:
                logger.error(f"MiniMax TTS生成失败: {tts_result.get('error')}")
                # 失败时切换到默认TTS
                audio_processor = manager.get_audio_processor(connection_id)
                audio_data = await audio_processor.synthesize(response)
                logger.info(f"回退到Google TTS，生成完成，大小: {len(audio_data)} 字节")
        else:
            # 未知的TTS提供商，使用默认的Google TTS
            logger.warning(f"未知的TTS提供商: {tts_provider}，使用Google TTS")
            audio_processor = manager.get_audio_processor(connection_id)
            audio_data = await audio_processor.synthesize(response)
            logger.info(f"Google TTS语音生成完成，大小: {len(audio_data)} 字节")
        
        # 如果使用EchoMimic，则生成视频
        if user_config["use_echomimic"] and user_config["ref_image_path"]:
            logger.info(f"开始EchoMimic视频生成，使用参考图像: {user_config['ref_image_path']}")
            # 通知前端视频生成开始
            await manager.send_message(connection_id, {
                "type": "generating_video",
                "message": "正在生成视频..."
            })
            
            # 获取EchoMimic生成器
            generator = get_echomimic_generator()
            
            # 创建临时音频文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio.write(audio_data)
                temp_audio_path = temp_audio.name
            
            try:
                logger.info(f"调用EchoMimic生成器，临时音频文件: {temp_audio_path}")
                # 生成视频
                result = await generator.generate_video(
                    reference_image_path=user_config["ref_image_path"],
                    audio_path=temp_audio_path
                )
                
                # 转换视频路径为前端可访问的URL路径
                if result and result.get("success") and result.get("video_path"):
                    video_path = result["video_path"]
                    web_path = video_path.replace("./frontend/build", "")
                    logger.info(f"EchoMimic视频生成成功: {video_path}, Web路径: {web_path}")
                    
                    # 发送视频就绪通知
                    await manager.send_message(connection_id, {
                        "type": "video_ready",
                        "video_url": web_path,
                        "success": True
                    })
                else:
                    logger.warning("EchoMimic视频生成返回不完整结果，回退到纯音频")
                    # 视频生成失败，发送纯音频
                    await manager.send_bytes(connection_id, audio_data)
            except Exception as e:
                logger.error(f"EchoMimic视频生成失败: {e}")
                # 出错时发送纯音频
                await manager.send_bytes(connection_id, audio_data)
            finally:
                # 清理临时文件
                if os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)
        else:
            logger.info("未启用EchoMimic或未设置参考图像，发送纯音频")
            # 没有使用EchoMimic或没有设置参考图像，直接发送音频
            await manager.send_bytes(connection_id, audio_data)
    
    except Exception as e:
        logger.error(f"处理文本输入时出错: {e}")
        await manager.send_message(connection_id, {
            "type": "error",
            "message": f"处理文本失败: {str(e)}"
        })

# 图像上传端点
@app.post("/api/upload_reference_image")
async def upload_reference_image(file: UploadFile = File(...)):
    """处理参考图像上传"""
    try:
        # 创建上传目录
        upload_dir = Path("./frontend/build/uploads/reference_images")
        upload_dir.mkdir(exist_ok=True, parents=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ref_{timestamp}_{file.filename}"
        filepath = upload_dir / filename
        
        # 保存文件
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 返回相对路径
        relative_path = f"/uploads/reference_images/{filename}"
        
        return {"success": True, "imagePath": relative_path}
        
    except Exception as e:
        logger.error(f"上传参考图像失败: {e}")
        return {"success": False, "error": str(e)}

# 配置更新端点
@app.post("/api/update_config")
async def update_config(request: Request):
    """更新用户配置"""
    try:
        data = await request.json()
        connection_id = data.get("connection_id", "default")
        
        # 如果连接ID不存在，创建默认配置
        if connection_id not in manager.user_configs:
            manager.user_configs[connection_id] = {
                "language": DEFAULT_LANGUAGE,
                "voice": DEFAULT_VOICE,
                "theme": "light",
                "providers": {
                    "llm": DEFAULT_PROVIDERS["llm"],
                    "stt": DEFAULT_PROVIDERS["stt"],
                    "tts": DEFAULT_PROVIDERS["tts"]
                },
                "use_echomimic": True,
                "ref_image_path": None
            }
        
        # 更新配置
        config = manager.user_configs[connection_id]
        
        if "language" in data:
            config["language"] = data["language"]
            
        if "voice" in data:
            config["voice"] = data["voice"]
            
        if "theme" in data:
            config["theme"] = data["theme"]
            
        if "useEchoMimic" in data:
            config["use_echomimic"] = data["useEchoMimic"]
            
        if "refImagePath" in data:
            config["ref_image_path"] = data["refImagePath"]
            # 将网络路径转换为文件系统路径
            if config["ref_image_path"] and config["ref_image_path"].startswith("/"):
                config["ref_image_path"] = f"./frontend/build{config['ref_image_path']}"
                
        # 更新API提供商设置
        if "providers" in data:
            providers_data = data["providers"]
            
            # 初始化providers如果不存在
            if "providers" not in config:
                config["providers"] = {
                    "llm": DEFAULT_PROVIDERS["llm"],
                    "stt": DEFAULT_PROVIDERS["stt"],
                    "tts": DEFAULT_PROVIDERS["tts"]
                }
            
            # 更新LLM提供商
            if "llm" in providers_data and providers_data["llm"] in API_PROVIDERS["llm"]:
                config["providers"]["llm"] = providers_data["llm"]
                logger.info(f"更新LLM提供商为: {providers_data['llm']}")
            
            # 更新STT提供商
            if "stt" in providers_data and providers_data["stt"] in API_PROVIDERS["stt"]:
                config["providers"]["stt"] = providers_data["stt"]
                logger.info(f"更新STT提供商为: {providers_data['stt']}")
                
            # 更新TTS提供商
            if "tts" in providers_data and providers_data["tts"] in API_PROVIDERS["tts"]:
                config["providers"]["tts"] = providers_data["tts"]
                logger.info(f"更新TTS提供商为: {providers_data['tts']}")
        
        # 如果已经有音频处理器，更新设置
        if connection_id in manager.audio_processors:
            audio_processor = manager.audio_processors[connection_id]
            audio_processor.set_language(config["language"])
            audio_processor.set_voice(config["voice"])
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        return {"success": False, "error": str(e)}

# 处理EchoMimic生成请求
@app.post("/api/generate_video")
async def generate_video(request: Request, background_tasks: BackgroundTasks):
    """生成EchoMimic视频的API端点"""
    try:
        # 获取请求数据
        data = await request.json()
        
        # 验证请求数据
        if not data.get("audio_data") or not data.get("reference_image"):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "缺少必要参数"}
            )
            
        # 获取生成器实例
        generator = get_echomimic_generator()
        
        # 创建临时文件来存储音频和图像
        temp_dir = tempfile.mkdtemp()
        
        # 处理音频数据
        audio_data_b64 = data["audio_data"].split(",")[1] if "," in data["audio_data"] else data["audio_data"]
        audio_bytes = base64.b64decode(audio_data_b64)
        audio_path = os.path.join(temp_dir, "temp_audio.wav")
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
            
        # 处理参考图像
        ref_image_b64 = data["reference_image"].split(",")[1] if "," in data["reference_image"] else data["reference_image"]
        ref_image_bytes = base64.b64decode(ref_image_b64)
        ref_image_path = os.path.join(temp_dir, "temp_ref.png")
        with open(ref_image_path, "wb") as f:
            f.write(ref_image_bytes)
            
        # 获取其他参数
        width = data.get("width", 512)
        height = data.get("height", 512)
        max_length = data.get("max_length", 120)  # 默认最多5秒
        
        # 异步生成视频
        result = await generator.generate_video(
            reference_image_path=ref_image_path,
            audio_path=audio_path,
            width=width, 
            height=height,
            max_length=max_length
        )
        
        # 添加清理任务
        background_tasks.add_task(lambda: os.system(f"rm -rf {temp_dir}"))
        
        # 获取连接ID并向前端发送视频就绪通知
        connection_id = data.get("connection_id", "default")
        if connection_id in manager.active_connections:
            # 转换视频路径为前端可访问的URL路径
            video_url = result.get("video_path", "")
            if video_url and os.path.exists(video_url):
                # 转换为相对路径
                web_path = video_url.replace("./frontend/build", "")
                await manager.send_message(connection_id, {
                    "type": "video_ready",
                    "video_url": web_path,
                    "success": True
                })
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"视频生成请求处理失败: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# 处理文本到视频请求
@app.post("/api/text_to_video")
async def text_to_video(request: Request, background_tasks: BackgroundTasks):
    """从文本生成视频的API端点，结合TTS和EchoMimic"""
    try:
        # 获取请求数据
        data = await request.json()
        
        # 验证文本参数
        if not data.get("text"):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "缺少文本参数"}
            )
            
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        
        # 获取连接ID
        connection_id = data.get("connection_id", "default")
        
        # 获取用户配置
        user_config = manager.get_user_config(connection_id)
        
        # 获取参考图像路径，优先使用用户配置中的路径
        ref_image_path = None
        
        # 先检查请求中是否提供了参考图像
        if data.get("reference_image"):
            # 处理请求中的参考图像
            ref_image_b64 = data["reference_image"].split(",")[1] if "," in data["reference_image"] else data["reference_image"]
            ref_image_bytes = base64.b64decode(ref_image_b64)
            ref_image_path = os.path.join(temp_dir, "temp_ref.png")
            with open(ref_image_path, "wb") as f:
                f.write(ref_image_bytes)
        # 如果请求中没有图像，则使用用户配置中的参考图像
        elif user_config.get("ref_image_path"):
            ref_image_path = user_config["ref_image_path"]
        else:
            # 如果没有参考图像，返回错误
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "未找到参考图像，请在设置中指定"}
            )
            
        # 获取或创建音频处理器
        if connection_id not in manager.audio_processors:
            manager.audio_processors[connection_id] = AudioProcessor(DEFAULT_LANGUAGE)
            
        audio_processor = manager.audio_processors[connection_id]
        
        # 将文本转换为语音
        text = data["text"]
        lang = user_config.get("language", DEFAULT_LANGUAGE)
        voice = user_config.get("voice", DEFAULT_VOICE)
        
        # 设置语音和语言
        audio_processor.set_language(lang)
        audio_processor.set_voice(voice)
        
        # 生成语音
        audio_data = await audio_processor.synthesize(text)
        
        if not audio_data:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "语音生成失败"}
            )
            
        # 保存语音文件
        audio_path = os.path.join(temp_dir, "temp_tts.wav")
        with open(audio_path, "wb") as f:
            f.write(audio_data)
            
        # 获取其他参数
        width = data.get("width", 512)
        height = data.get("height", 512)
        max_length = data.get("max_length", 240)  # 默认最多10秒
        
        # 获取生成器实例并生成视频
        generator = get_echomimic_generator()
        result = await generator.generate_video(
            reference_image_path=ref_image_path,
            audio_path=audio_path,
            width=width, 
            height=height,
            max_length=max_length
        )
        
        # 添加生成的文本到结果
        result["text"] = text
        
        # 添加清理任务
        background_tasks.add_task(lambda: os.system(f"rm -rf {temp_dir}"))
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"文本到视频生成请求处理失败: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# 获取预设参考图像列表
@app.get("/api/preset_images")
async def get_preset_images(gender: str = "woman"):
    """
    获取预设参考图像列表
    
    参数:
        gender: 性别，可选值为"man"或"woman"
    """
    try:
        # 检查性别参数
        if gender not in ["man", "woman"]:
            gender = "woman"  # 默认使用女性图像
            
        # 预设图像目录
        preset_dir = os.path.join("echomimic_v2", "EMTD_dataset", "ref_imgs_by_FLUX", gender)
        
        if not os.path.exists(preset_dir):
            return {"success": False, "error": f"预设图像目录不存在: {preset_dir}"}
        
        # 获取目录中的所有PNG图像
        images = []
        for filename in os.listdir(preset_dir):
            if filename.endswith(".png") and not filename.startswith("."):
                image_path = os.path.join(preset_dir, filename)
                # 构建URL路径(相对路径，前端会自动添加域名前缀)
                url_path = f"/static/preset_images/{gender}/{filename}"
                
                images.append({
                    "path": image_path,
                    "thumbnail": url_path,
                    "filename": filename
                })
        
        return {"success": True, "images": images}
    except Exception as e:
        logging.error(f"获取预设图像列表错误: {str(e)}")
        return {"success": False, "error": str(e)}

# 使用预设参考图像
@app.post("/api/use_preset_image")
async def use_preset_image(request: Request):
    """
    使用预设参考图像
    
    请求体:
        image_path: 预设图像的文件路径
    """
    try:
        data = await request.json()
        image_path = data.get("image_path")
        
        if not image_path or not os.path.exists(image_path):
            return {"success": False, "error": "图像路径无效或文件不存在"}
        
        # 获取当前连接的用户ID，假设已有活动连接
        # 简化处理，这里可能需要根据实际连接管理方式调整
        connection_id = list(manager.active_connections.keys())[0] if manager.active_connections else None
        
        if not connection_id:
            return {"success": False, "error": "没有活动的会话连接"}
        
        # 更新用户配置
        config = manager.user_configs.get(connection_id, {"use_echomimic": True})
        config["ref_image_path"] = image_path
        manager.user_configs[connection_id] = config
            
        return {"success": True, "file_path": image_path}
    except Exception as e:
        logging.error(f"使用预设图像错误: {str(e)}")
        return {"success": False, "error": str(e)}

# 挂载静态文件
# 添加应用首页重定向
@app.get("/")
async def redirect_to_frontend():
    return RedirectResponse(url="/frontend/index.html")

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("数字人助手应用已启动")
    # 创建必要的目录
    Path("./frontend/build/uploads/reference_images").mkdir(exist_ok=True, parents=True)
    Path("./frontend/build/generated").mkdir(exist_ok=True, parents=True)
    Path("./cache/echomimic").mkdir(exist_ok=True, parents=True)

# 应用关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("数字人助手应用已关闭")

# 现在，在所有API路由注册后，挂载静态文件
# 为预设图像创建静态文件挂载点 - 暂时注释掉，因为目录不存在
# app.mount("/static/preset_images", StaticFiles(directory="echomimic_v2/EMTD_dataset/ref_imgs_by_FLUX"), name="preset_images")

# 挂载前端构建目录 - 暂时注释掉，因为目录不存在
# app.mount("/frontend", StaticFiles(directory="frontend/build", html=True), name="frontend")

# 挂载前端测试文件 - 暂时注释掉，因为目录不存在
# app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend_root")

# 添加测试路由和静态文件挂载 - 暂时注释掉，因为函数不存在
# add_test_routes(app)

# 删除独立的WebSocket应用定义
# 所有WebSocket请求现在由主应用app处理

# 删除独立 WebSocket 应用的端点代码
# 现在只使用主应用的 /api/ws 端点

# 删除多余的WebSocket应用定义
# websocket_app 已被删除，只使用主应用app处理所有请求

# 主入口
if __name__ == "__main__":
    try:
        # 只启动一个主应用服务器
        uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
    except Exception as e:
        logger.critical(f"应用启动失败: {e}")