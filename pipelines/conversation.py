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
from yacs.config import CfgNode as CN

# 配置日志
logger = logging.getLogger(__name__)

class ConversationPipeline:
    """
    对话流水线: 语音输入 -> ASR -> LLM -> TTS -> 语音输出
    """
    def __init__(self, config: CN):
        """
        初始化对话流水线
        
        参数:
            config: 配置对象，包含ASR、LLM和TTS引擎的配置
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
            
        logger.info("对话流水线初始化完成")
        
    async def process(self, 
                     audio_input: AudioMessage, 
                     conversation_context: Optional[Dict[str, Any]] = None,
                     skip_asr: bool = False,
                     text_input: Optional[str] = None,
                     skip_llm: bool = False,
                     skip_tts: bool = False) -> Dict[str, Any]:
        """
        处理完整的对话流程
        
        参数:
            audio_input: 输入音频消息
            conversation_context: 对话上下文
            skip_asr: 是否跳过ASR步骤（直接使用text_input）
            text_input: 直接输入的文本（跳过ASR时使用）
            skip_llm: 是否跳过LLM步骤
            skip_tts: 是否跳过TTS步骤
            
        返回:
            处理结果字典，包含：
            - input_text: 输入文本（ASR结果）
            - response_text: 回复文本（LLM结果）
            - audio_output: 输出音频（TTS结果）
            - error: 如果有错误发生
        """
        result = {}
        
        try:
            # 1. 语音识别阶段
            if not skip_asr and self.asr_engine:
                logger.info("开始语音识别")
                text_result = await self.asr_engine.run(audio_input)
                if not text_result:
                    logger.error("ASR识别失败")
                    return {"error": "语音识别失败"}
                
                input_text = text_result.data
                logger.info(f"ASR识别结果: {input_text}")
                result["input_text"] = input_text
            else:
                # 使用直接输入的文本
                if text_input:
                    input_text = text_input
                    result["input_text"] = input_text
                    logger.info(f"使用直接输入文本: {input_text}")
                else:
                    logger.error("没有输入文本且ASR被跳过")
                    return {"error": "没有有效的输入"}
            
            # 2. 对话生成阶段
            if not skip_llm and self.llm_engine:
                logger.info("开始对话生成")
                
                # 创建文本消息对象
                text_message = TextMessage(data=input_text)
                
                # 调用LLM引擎生成回复
                response = await self.llm_engine.run(text_message, context=conversation_context)
                
                if not response:
                    logger.error("LLM生成失败")
                    return {**result, "error": "对话生成失败"}
                
                response_text = response.data
                logger.info(f"LLM回复: {response_text}")
                result["response_text"] = response_text
            else:
                # 跳过LLM，使用输入文本作为回复
                response_text = input_text
                result["response_text"] = response_text
                logger.info("跳过LLM处理")
            
            # 3. 语音合成阶段
            if not skip_tts and self.tts_engine:
                logger.info("开始语音合成")
                
                # 创建文本消息对象
                text_message = TextMessage(data=response_text)
                
                # 调用TTS引擎合成语音
                audio_output = await self.tts_engine.run(text_message)
                
                if not audio_output:
                    logger.error("TTS合成失败")
                    return {**result, "error": "语音合成失败"}
                
                logger.info(f"TTS合成成功，音频长度: {len(audio_output.data)} 字节")
                result["audio_output"] = audio_output
            else:
                logger.info("跳过TTS处理")
            
            return result
        
        except Exception as e:
            logger.error(f"对话处理出错: {str(e)}", exc_info=True)
            return {**result, "error": str(e)}
            
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
