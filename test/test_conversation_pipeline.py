# -*- coding: utf-8 -*-
'''
测试对话管道
'''

import asyncio
import logging
import os
from pathlib import Path
from utils import AudioMessage, TextMessage, AudioFormatType
from utils.config import get_config
from pipelines.conversation import ConversationPipeline
import argparse

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_conversation_pipeline(audio_path: str = None, text_input: str = None):
    """测试完整的对话管道流程
    
    参数:
        audio_path: 音频文件路径，用于ASR测试
        text_input: 文本输入，可以跳过ASR直接测试LLM->TTS流程
    """
    try:
        # 加载配置
        logger.info("加载配置...")
        cfg = get_config()
        
        # 初始化对话管道
        logger.info("初始化对话管道...")
        pipeline = ConversationPipeline(cfg)
        await pipeline.setup()
        
        # 初始化上下文
        conversation_context = {}
        
        # 根据输入类型选择测试方式
        if audio_path and os.path.exists(audio_path):
            # 读取音频文件
            logger.info(f"读取音频文件: {audio_path}")
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            
            # 创建音频消息
            audio_message = AudioMessage(
                data=audio_data,
                format=AudioFormatType.get_format_from_path(audio_path),
                desc="测试音频输入"
            )
            
            # 处理音频输入
            logger.info("开始处理音频输入...")
            result = await pipeline.process(audio_message, conversation_context)
            
        elif text_input:
            # 直接使用文本输入（跳过ASR）
            logger.info(f"使用文本输入: {text_input}")
            
            # 创建文本消息
            text_message = TextMessage(data=text_input)
            
            # 处理文本输入（手动将文本传递给LLM处理）
            logger.info("使用文本输入直接测试LLM->TTS流程...")
            
            # 调用LLM
            logger.info("调用LLM引擎...")
            llm_response = await pipeline.llm_engine.run(text_message, context=conversation_context.get("message_history", []))
            
            if llm_response:
                # 更新上下文
                if "message_history" not in conversation_context:
                    conversation_context["message_history"] = []
                    
                conversation_context["message_history"].append({
                    "role": "user", 
                    "content": text_input
                })
                conversation_context["message_history"].append({
                    "role": "assistant", 
                    "content": llm_response.data
                })
                
                # 调用TTS
                logger.info("调用TTS引擎...")
                result = await pipeline.tts_engine.run(llm_response)
            else:
                logger.error("LLM引擎未返回有效响应")
                return None
        else:
            logger.error("请提供音频文件路径或文本输入")
            return None
        
        # 保存结果音频
        if result and hasattr(result, "data"):
            output_dir = Path("test_outputs")
            output_dir.mkdir(exist_ok=True)
            
            output_path = output_dir / "conversation_test_output.wav"
            with open(output_path, "wb") as f:
                f.write(result.data)
                
            logger.info(f"已保存对话结果到: {output_path}")
            return {
                "output_file": output_path,
                "response_text": llm_response.data if "llm_response" in locals() else "无文本响应" 
            }
        else:
            logger.error("未获得有效的对话结果")
            return None
            
    except Exception as e:
        logger.error(f"测试过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="测试数字人对话管道")
    parser.add_argument("--audio", type=str, help="音频文件路径，用于ASR->LLM->TTS流程测试")
    parser.add_argument("--text", type=str, help="文本输入，用于直接LLM->TTS流程测试")
    
    args = parser.parse_args()
    
    # 运行测试
    result = asyncio.run(test_conversation_pipeline(args.audio, args.text))
    
    if result:
        print(f"\n=== 对话测试成功 ===")
        print(f"输出文件: {result['output_file']}")
        print(f"回复文本: {result['response_text']}")
    else:
        print("\n测试失败，未获得有效结果")
