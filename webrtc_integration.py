# webrtc_integration.py
import os
import logging
import json
import asyncio
from typing import Dict, Any, Callable, Optional
from functools import lru_cache

# 导入Deepgram集成
from deepgram_integration import create_deepgram_client, setup_live_transcription

# 配置日志
logger = logging.getLogger(__name__)

class WebRTCHandler:
    """WebRTC处理器，管理WebRTC连接和Deepgram实时转写"""
    
    def __init__(self):
        """初始化WebRTC处理器"""
        self.connections = {}  # 连接ID到处理对象的映射
        self.deepgram_client = None
        self.initialize_deepgram()
    
    def initialize_deepgram(self) -> None:
        """初始化Deepgram客户端"""
        try:
            self.deepgram_client = create_deepgram_client()
            if self.deepgram_client:
                logger.info("Deepgram客户端初始化成功")
            else:
                logger.error("无法初始化Deepgram客户端")
        except Exception as e:
            logger.error(f"初始化Deepgram时出错: {str(e)}")
            self.deepgram_client = None
    
    async def create_connection(
        self, 
        connection_id: str, 
        message_callback: Callable[[str, Dict[str, Any]], None],
        language: str = "zh-CN"
    ) -> bool:
        """
        为指定连接创建WebRTC和Deepgram处理
        
        参数:
            connection_id: 连接的唯一标识符
            message_callback: 接收消息的回调函数
            language: 转写语言代码
        
        返回:
            是否成功创建连接
        """
        # 检查客户端是否已初始化
        if not self.deepgram_client:
            logger.error(f"无法为连接 {connection_id} 创建会话: Deepgram客户端未初始化")
            return False
        
        # 检查连接是否已存在
        if connection_id in self.connections:
            logger.warning(f"连接 {connection_id} 已存在，将重用")
            return True
        
        try:
            # 创建转写回调函数
            def transcription_callback(result: Dict[str, Any]) -> None:
                """处理Deepgram转写结果的回调"""
                try:
                    # 解析Deepgram返回的JSON
                    if not isinstance(result, dict):
                        logger.warning(f"收到非字典格式的转写结果: {type(result)}")
                        return
                    
                    channel = result.get("channel", {})
                    alternatives = channel.get("alternatives", [])
                    
                    if not alternatives:
                        logger.debug("转写结果中没有替代文本")
                        return
                    
                    # 获取第一个替代文本
                    transcript = alternatives[0].get("transcript", "")
                    is_final = result.get("is_final", False)
                    
                    if not transcript:
                        return
                    
                    # 构建消息并发送回客户端
                    message = {
                        "type": "transcription",
                        "text": transcript,
                        "final": is_final
                    }
                    
                    # 调用回调函数发送消息
                    message_callback(connection_id, message)
                    
                    # 记录转写结果
                    log_level = logging.INFO if is_final else logging.DEBUG
                    logger.log(log_level, f"转写结果 [{connection_id}] - {'最终' if is_final else '临时'}: {transcript}")
                
                except Exception as e:
                    logger.error(f"处理转写结果时出错: {str(e)}")
            
            # 设置实时转写
            live_transcription = setup_live_transcription(
                callback_function=transcription_callback,
                language=language
            )
            
            # 保存连接信息
            self.connections[connection_id] = {
                "live_transcription": live_transcription,
                "language": language,
                "message_callback": message_callback
            }
            
            logger.info(f"为连接 {connection_id} 创建了新的WebRTC会话")
            return True
            
        except Exception as e:
            logger.error(f"为连接 {connection_id} 创建WebRTC会话时出错: {str(e)}")
            return False
    
    async def process_audio(self, connection_id: str, audio_data: bytes) -> bool:
        """
        处理接收到的WebRTC音频数据
        
        参数:
            connection_id: 连接的唯一标识符
            audio_data: 音频数据字节
        
        返回:
            是否成功处理
        """
        # 检查连接是否存在
        if connection_id not in self.connections:
            logger.error(f"连接 {connection_id} 不存在，无法处理音频")
            return False
        
        # 获取连接信息
        connection = self.connections[connection_id]
        live_transcription = connection.get("live_transcription")
        
        if not live_transcription:
            logger.error(f"连接 {connection_id} 没有活跃的转写会话")
            return False
        
        try:
            # 发送音频数据到Deepgram
            live_transcription.send(audio_data)
            return True
        except Exception as e:
            logger.error(f"发送音频数据到Deepgram时出错: {str(e)}")
            return False
    
    async def close_connection(self, connection_id: str) -> None:
        """
        关闭指定的WebRTC连接
        
        参数:
            connection_id: 连接的唯一标识符
        """
        # 检查连接是否存在
        if connection_id not in self.connections:
            logger.warning(f"连接 {connection_id} 不存在，无需关闭")
            return
        
        # 获取连接信息
        connection = self.connections[connection_id]
        live_transcription = connection.get("live_transcription")
        
        if live_transcription:
            try:
                # 关闭转写会话 - 使用异步关闭方法
                if hasattr(live_transcription, 'finish') and callable(live_transcription.finish):
                    # 如果是同步方法
                    live_transcription.finish()
                    logger.info(f"关闭了连接 {connection_id} 的转写会话")
                elif hasattr(live_transcription, 'close') and callable(live_transcription.close):
                    # 如果有close方法
                    await live_transcription.close()
                    logger.info(f"关闭了连接 {connection_id} 的转写会话")
                else:
                    # 没有明确的关闭方法，仅移除引用
                    logger.info(f"无法显式关闭转写会话，将移除引用: {connection_id}")
            except Exception as e:
                logger.error(f"关闭转写会话时出错: {str(e)}")
        
        # 移除连接
        del self.connections[connection_id]
        logger.info(f"已移除连接 {connection_id}")
    
    async def update_language(self, connection_id: str, language: str) -> bool:
        """
        更新指定连接的语言设置
        
        参数:
            connection_id: 连接的唯一标识符
            language: 新的语言代码
            
        返回:
            是否成功更新
        """
        # 检查连接是否存在
        if connection_id not in self.connections:
            logger.error(f"连接 {connection_id} 不存在，无法更新语言")
            return False
        
        # 获取连接信息
        connection = self.connections[connection_id]
        message_callback = connection.get("message_callback")
        
        if not message_callback:
            logger.error(f"连接 {connection_id} 没有有效的消息回调")
            return False
        
        # 关闭现有连接
        await self.close_connection(connection_id)
        
        # 创建新连接，使用新的语言设置
        success = await self.create_connection(
            connection_id=connection_id,
            message_callback=message_callback,
            language=language
        )
        
        if success:
            logger.info(f"已为连接 {connection_id} 更新语言设置为 {language}")
        
        return success
    
    def is_connected(self, connection_id: str) -> bool:
        """
        检查指定的连接是否活跃
        
        参数:
            connection_id: 连接的唯一标识符
            
        返回:
            连接是否活跃
        """
        return connection_id in self.connections


# 创建全局WebRTC处理器实例
webrtc_handler = WebRTCHandler()


async def get_webrtc_handler() -> WebRTCHandler:
    """
    获取WebRTC处理器实例
    
    返回:
        WebRTC处理器实例
    """
    return webrtc_handler


# 判断Deepgram转写是否可用
def is_deepgram_available() -> bool:
    """
    检查Deepgram转写功能是否可用
    
    返回:
        Deepgram是否可用
    """
    return webrtc_handler.deepgram_client is not None
