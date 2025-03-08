"""
语音处理流程测试脚本
测试MiniMax API集成的语音处理相关功能，无需前端界面
"""

import os
import asyncio
import logging
import tempfile
import json
import base64
from pathlib import Path
from datetime import datetime

# 导入项目模块
from minimax_integration import get_minimax_integration
from utils.audio_utils import detect_audio_format, compute_content_hash, get_cached_audio, save_to_cache

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 测试目录
TEST_OUTPUT_DIR = Path("./test_outputs")
TEST_OUTPUT_DIR.mkdir(exist_ok=True)

async def test_tts_basic():
    """
    测试基本的文本到语音转换功能
    """
    logger.info("==== 测试基本的文本到语音转换 ====")
    
    # 获取MiniMax集成实例
    minimax = get_minimax_integration()
    
    # 测试文本
    text = "你好，这是一个测试语音。我正在检查文本到语音转换的功能是否正常工作。"
    
    # 调用TTS API
    logger.info(f"正在将文本转换为语音: {text}")
    result = await minimax.text_to_speech(text=text, use_cache=True)
    
    if result.get("success"):
        audio_data = result.get("audio_data")
        duration = result.get("duration", 0)
        cached = result.get("cached", False)
        audio_format = result.get("format", "未知格式")
        
        logger.info(f"语音合成成功: 时长={duration}秒，格式={audio_format}，缓存={cached}")
        
        # 保存音频文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = TEST_OUTPUT_DIR / f"tts_basic_{timestamp}.mp3"
        
        with open(output_path, "wb") as f:
            f.write(audio_data)
            
        logger.info(f"音频文件已保存到: {output_path}")
        return output_path
    else:
        logger.error(f"语音合成失败: {result.get('error', '未知错误')}")
        return None

async def test_tts_cache():
    """
    测试TTS缓存机制
    """
    logger.info("==== 测试TTS缓存机制 ====")
    
    # 获取MiniMax集成实例
    minimax = get_minimax_integration()
    
    # 测试文本
    text = "这是一个测试缓存的语音。我们将调用两次相同的请求，第二次应该从缓存获取。"
    
    # 第一次调用TTS API，不应该有缓存
    logger.info("第一次调用TTS API（应生成新语音）")
    result1 = await minimax.text_to_speech(text=text, use_cache=True)
    
    if not result1.get("success"):
        logger.error(f"第一次语音合成失败: {result1.get('error', '未知错误')}")
        return False
    
    cached1 = result1.get("cached", False)
    logger.info(f"第一次调用: 缓存={cached1}")
    
    # 第二次调用相同参数的TTS API，应该使用缓存
    logger.info("第二次调用TTS API（应使用缓存）")
    result2 = await minimax.text_to_speech(text=text, use_cache=True)
    
    if not result2.get("success"):
        logger.error(f"第二次语音合成失败: {result2.get('error', '未知错误')}")
        return False
    
    cached2 = result2.get("cached", False)
    logger.info(f"第二次调用: 缓存={cached2}")
    
    # 验证第二次是否使用了缓存
    if not cached1 and cached2:
        logger.info("✓ 缓存机制正常工作！")
        return True
    else:
        logger.warning(f"缓存机制可能存在问题: 第一次={cached1}, 第二次={cached2}")
        return False

async def test_tts_different_voices():
    """
    测试不同声音的TTS
    """
    logger.info("==== 测试不同声音的TTS ====")
    
    # 获取MiniMax集成实例
    minimax = get_minimax_integration()
    
    # 测试文本
    text = "这是一个测试不同声音的语音。我们将使用不同的声音参数来生成语音。"
    
    # 定义要测试的声音
    voices = [
        "female-general-24",
        "male-general-16"
    ]
    
    output_paths = []
    
    for voice_id in voices:
        logger.info(f"测试声音: {voice_id}")
        
        result = await minimax.text_to_speech(
            text=text,
            voice_id=voice_id,
            use_cache=True
        )
        
        if result.get("success"):
            audio_data = result.get("audio_data")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = TEST_OUTPUT_DIR / f"tts_voice_{voice_id}_{timestamp}.mp3"
            
            with open(output_path, "wb") as f:
                f.write(audio_data)
                
            logger.info(f"音频文件已保存到: {output_path}")
            output_paths.append(output_path)
        else:
            logger.error(f"使用声音 {voice_id} 合成失败: {result.get('error', '未知错误')}")
    
    return output_paths

async def test_audio_format_detection():
    """
    测试音频格式检测
    """
    logger.info("==== 测试音频格式检测 ====")
    
    # 获取MiniMax集成实例
    minimax = get_minimax_integration()
    
    # 生成一个测试音频
    text = "这是用于测试音频格式检测的语音。"
    result = await minimax.text_to_speech(text=text, use_cache=True)
    
    if not result.get("success"):
        logger.error(f"生成测试音频失败: {result.get('error', '未知错误')}")
        return False
    
    audio_data = result.get("audio_data")
    
    # 检测音频格式
    audio_format = await detect_audio_format(audio_data)
    logger.info(f"检测到的音频格式: {audio_format.name}")
    
    return audio_format.name

async def test_cache_operations():
    """
    测试缓存操作的底层功能
    """
    logger.info("==== 测试缓存操作 ====")
    
    # 测试数据
    test_text = "测试缓存操作"
    test_voice = "test-voice"
    extra_params = {"param1": "value1", "param2": "value2"}
    
    # 计算缓存键
    cache_key = compute_content_hash(test_text, test_voice, extra_params)
    logger.info(f"计算得到的缓存键: {cache_key}")
    
    # 模拟音频数据
    test_audio_data = b"This is test audio data"
    
    # 保存到缓存
    logger.info("正在保存到缓存...")
    save_result = await save_to_cache(cache_key, test_audio_data)
    
    if not save_result:
        logger.error("保存到缓存失败")
        return False
    
    # 从缓存获取
    logger.info("正在从缓存获取...")
    cached_data = await get_cached_audio(cache_key)
    
    if cached_data is None:
        logger.error("从缓存获取失败")
        return False
    
    # 验证数据一致性
    is_same = cached_data == test_audio_data
    logger.info(f"缓存数据一致性: {is_same}")
    
    return is_same

async def test_long_text_tts():
    """
    测试较长文本的TTS处理
    """
    logger.info("==== 测试长文本TTS ====")
    
    # 获取MiniMax集成实例
    minimax = get_minimax_integration()
    
    # 较长的测试文本
    long_text = """
    这是一段较长的文本，用于测试语音合成系统处理长文本的能力。
    在实际应用中，用户可能会输入较长的段落或者多个句子，
    系统需要能够正确处理这些较长的输入，并生成流畅的语音输出。
    语音合成的质量不仅取决于单个句子的处理，还取决于句子之间的连贯性和自然过渡。
    我们希望系统能够理解文本的结构，适当地处理标点符号，并在语音中反映出文本的节奏和语调变化。
    此外，系统还应该能够处理不同类型的内容，包括对话、叙述和说明性文本等。
    通过这个测试，我们可以评估系统在处理较长文本时的性能和质量。
    """
    
    # 调用TTS API
    logger.info(f"正在处理长文本（长度：{len(long_text)}字符）")
    result = await minimax.text_to_speech(text=long_text, use_cache=True)
    
    if result.get("success"):
        audio_data = result.get("audio_data")
        duration = result.get("duration", 0)
        
        logger.info(f"长文本语音合成成功: 时长={duration}秒")
        
        # 保存音频文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = TEST_OUTPUT_DIR / f"tts_long_text_{timestamp}.mp3"
        
        with open(output_path, "wb") as f:
            f.write(audio_data)
            
        logger.info(f"长文本音频文件已保存到: {output_path}")
        return output_path
    else:
        logger.error(f"长文本语音合成失败: {result.get('error', '未知错误')}")
        return None

async def run_all_tests():
    """
    运行所有测试
    """
    logger.info("开始运行语音处理流程测试...")
    
    test_results = {}
    
    # 基本TTS测试
    try:
        test_results["basic_tts"] = await test_tts_basic()
    except Exception as e:
        logger.error(f"基本TTS测试出错: {e}")
        test_results["basic_tts"] = f"错误: {e}"
    
    # 缓存机制测试
    try:
        test_results["tts_cache"] = await test_tts_cache()
    except Exception as e:
        logger.error(f"缓存机制测试出错: {e}")
        test_results["tts_cache"] = f"错误: {e}"
    
    # 不同声音测试
    try:
        test_results["different_voices"] = await test_tts_different_voices()
    except Exception as e:
        logger.error(f"不同声音测试出错: {e}")
        test_results["different_voices"] = f"错误: {e}"
    
    # 音频格式检测测试
    try:
        test_results["audio_format"] = await test_audio_format_detection()
    except Exception as e:
        logger.error(f"音频格式检测测试出错: {e}")
        test_results["audio_format"] = f"错误: {e}"
    
    # 缓存操作测试
    try:
        test_results["cache_operations"] = await test_cache_operations()
    except Exception as e:
        logger.error(f"缓存操作测试出错: {e}")
        test_results["cache_operations"] = f"错误: {e}"
    
    # 长文本TTS测试
    try:
        test_results["long_text_tts"] = await test_long_text_tts()
    except Exception as e:
        logger.error(f"长文本TTS测试出错: {e}")
        test_results["long_text_tts"] = f"错误: {e}"
    
    # 打印测试结果摘要
    logger.info("\n==== 测试结果摘要 ====")
    for test_name, result in test_results.items():
        status = "✓ 成功" if result else "✗ 失败"
        logger.info(f"{test_name}: {status}")
    
    logger.info("测试完成！")
    return test_results

if __name__ == "__main__":
    # 创建异步事件循环并运行测试
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_all_tests())
