# -*- coding: utf-8 -*-
'''
对话流水线：语音识别 -> 语言模型 -> 语音合成
'''

import logging
import asyncio
from typing import Optional, Dict, Any, List, Union
from utils.protocol import AudioMessage, TextMessage
from engine.asr.asrFactory import ASRFactory
from engine.llm.llmFactory import LLMFactory
from engine.tts.ttsFactory import TTSFactory
from engine.agent.agent_factory import AgentFactory
from yacs.config import CfgNode as CN

# 配置日志
logger = logging.getLogger(__name__)

class ConversationPipeline:
    """
    对话流水线: 语音输入 -> ASR -> LLM/Agent -> TTS -> 语音输出
    """
    def __init__(self, config: CN):
        """
        初始化对话流水线
        
        参数:
            config: 配置对象，包含ASR、LLM、TTS和Agent引擎的配置
        """
        self.config = config
        
        # 初始化引擎
        logger.info("初始化对话流水线引擎...")
        
        # 初始化ASR引擎
        if hasattr(config, 'ASR') and config.ASR.ENABLED:
            logger.info(f"初始化ASR引擎: {config.ASR.NAME}")
            self.asr_engine = ASRFactory.create(config.ASR)
        else:
            logger.warning("ASR引擎未启用")
            self.asr_engine = None
            
        # 初始化LLM引擎
        if hasattr(config, 'LLM') and config.LLM.ENABLED:
            logger.info(f"初始化LLM引擎: {config.LLM.NAME}")
            self.llm_engine = LLMFactory.create(config.LLM)
        else:
            logger.warning("LLM引擎未启用")
            self.llm_engine = None
            
        # 初始化TTS引擎
        if hasattr(config, 'TTS') and config.TTS.ENABLED:
            logger.info(f"初始化TTS引擎: {config.TTS.NAME}")
            self.tts_engine = TTSFactory.create(config.TTS)
        else:
            logger.warning("TTS引擎未启用")
            self.tts_engine = None
            
        # 初始化Agent引擎
        if hasattr(config, 'AGENT') and config.AGENT.ENABLED:
            logger.info(f"初始化Agent引擎: {config.AGENT.NAME}")
            self.agent_engine = AgentFactory.create(config.AGENT)
        else:
            logger.warning("Agent引擎未启用")
            self.agent_engine = None
        
        # 是否使用Agent模式
        self.use_agent = hasattr(config, 'AGENT') and config.AGENT.ENABLED and self.agent_engine is not None
        
        logger.info(f"对话流水线初始化完成，{'已启用' if self.use_agent else '未启用'} Agent模式")
        
    async def process(self, 
                     audio_input: AudioMessage, 
                     conversation_context: Optional[Dict[str, Any]] = None,
                     skip_asr: bool = False,
                     text_input: Optional[str] = None,
                     skip_llm: bool = False,
                     use_agent: Optional[bool] = None,
                     skip_tts: bool = False) -> Dict[str, Any]:
        """
        处理语音输入并生成语音响应
        
        参数:
            audio_input: 语音输入
            conversation_context: 对话上下文
            skip_asr: 是否跳过ASR步骤
            text_input: 文本输入，如果提供则跳过ASR
            skip_llm: 是否跳过LLM步骤
            use_agent: 是否使用Agent，默认根据配置决定
            skip_tts: 是否跳过TTS步骤
            
        返回:
            包含处理结果的字典
        """
        result = {
            "asr_result": None,
            "llm_result": None,
            "agent_result": None,  # 新增agent结果
            "tts_result": None,
            "error": None
        }
        
        # 确定是否使用Agent
        use_agent_mode = self.use_agent if use_agent is None else use_agent
        
        try:
            # 步骤1: ASR处理
            if skip_asr or text_input:
                asr_text = text_input
                result["asr_result"] = TextMessage(text=asr_text) if asr_text else None
            else:
                if not self.asr_engine:
                    raise ValueError("ASR引擎未初始化")
                
                logger.info("执行语音识别...")
                asr_text_message = await self.asr_engine.transcribe(audio_input)
                result["asr_result"] = asr_text_message
                asr_text = asr_text_message.text if asr_text_message else None
                
                if not asr_text:
                    logger.warning("语音识别未返回文本")
                    return result
            
            # 步骤2: LLM/Agent处理
            if skip_llm:
                logger.info("跳过LLM/Agent处理")
            else:
                if use_agent_mode and self.agent_engine:
                    # 使用Agent处理
                    logger.info("使用Agent处理文本...")
                    agent_response = await self.agent_engine.process(
                        asr_text,
                        conversation_context=conversation_context
                    )
                    result["agent_result"] = agent_response
                    llm_text = agent_response.text if agent_response else None
                elif self.llm_engine:
                    # 使用传统LLM处理
                    logger.info("使用LLM处理文本...")
                    llm_response = await self.llm_engine.generate(
                        asr_text,
                        conversation_context=conversation_context
                    )
                    result["llm_result"] = llm_response
                    llm_text = llm_response.text if llm_response else None
                else:
                    raise ValueError("LLM引擎和Agent引擎均未初始化")
                
                if not llm_text:
                    logger.warning("LLM/Agent未返回文本")
                    return result
            
            # 步骤3: TTS处理
            if skip_tts:
                logger.info("跳过TTS处理")
            else:
                if not self.tts_engine:
                    raise ValueError("TTS引擎未初始化")
                
                # 获取LLM/Agent输出文本
                text_to_speak = None
                if result["agent_result"]:
                    text_to_speak = result["agent_result"].text
                elif result["llm_result"]:
                    text_to_speak = result["llm_result"].text
                
                if text_to_speak:
                    logger.info("执行语音合成...")
                    tts_audio = await self.tts_engine.synthesize(text_to_speak)
                    result["tts_result"] = tts_audio
            
            return result
            
        except Exception as e:
            error_msg = f"对话流水线处理失败: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg
            return result
            
    async def asr_only(self, audio_input: AudioMessage) -> Optional[TextMessage]:
        """
        仅执行语音识别
        
        参数:
            audio_input: 输入音频消息
            
        返回:
            TextMessage: 识别结果
        """
        if not self.asr_engine:
            logger.error("ASR引擎未初始化")
            return None
            
        try:
            return await self.asr_engine.run(audio_input)
        except Exception as e:
            logger.error(f"语音识别出错: {str(e)}")
            return None
            
    async def llm_only(self, text_input: Union[str, TextMessage], 
                       conversation_context: Optional[Dict[str, Any]] = None) -> Optional[TextMessage]:
        """
        仅执行语言模型处理
        
        参数:
            text_input: 输入文本或文本消息
            conversation_context: 对话上下文
            
        返回:
            TextMessage: 生成的回复
        """
        if not self.llm_engine:
            logger.error("LLM引擎未初始化")
            return None
            
        try:
            # 如果输入是字符串，转换为TextMessage
            if isinstance(text_input, str):
                text_input = TextMessage(data=text_input)
                
            return await self.llm_engine.run(text_input, context=conversation_context)
        except Exception as e:
            logger.error(f"语言模型处理出错: {str(e)}")
            return None
            
    async def tts_only(self, text_input: Union[str, TextMessage]) -> Optional[AudioMessage]:
        """
        仅执行语音合成
        
        参数:
            text_input: 输入文本或文本消息
            
        返回:
            AudioMessage: 合成的音频
        """
        if not self.tts_engine:
            logger.error("TTS引擎未初始化")
            return None
            
        try:
            # 如果输入是字符串，转换为TextMessage
            if isinstance(text_input, str):
                text_input = TextMessage(data=text_input)
                
            return await self.tts_engine.run(text_input)
        except Exception as e:
            logger.error(f"语音合成出错: {str(e)}")
            return None

    async def agent_only(self, text_input: Union[str, TextMessage],
                       conversation_context: Optional[Dict[str, Any]] = None) -> Optional[TextMessage]:
        """
        只使用Agent处理文本输入
        
        参数:
            text_input: 文本输入
            conversation_context: 对话上下文
            
        返回:
            Agent处理结果
        """
        if not self.agent_engine:
            logger.error("Agent引擎未初始化")
            return None
            
        try:
            logger.info("只使用Agent处理文本...")
            return await self.agent_engine.process(
                text_input,
                conversation_context=conversation_context
            )
        except Exception as e:
            logger.error(f"Agent处理失败: {str(e)}")
            return None
