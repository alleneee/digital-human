#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试EchoMimicV2集成功能
"""

import os
import sys
import asyncio
import argparse
import base64
import aiofiles
from pathlib import Path

# 添加项目根目录到导入路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import load_config
from integrations.echomimic import EchoMimicIntegration

async def test_audio_to_video(audio_file_path, config_path="configs/engines/echomimic/default.yaml"):
    """测试从音频文件生成视频"""
    print(f"加载配置文件: {config_path}")
    # 加载echomimic配置
    if os.path.exists(config_path):
        config = load_config(config_path)
    else:
        # 加载默认配置并提取echomimic部分
        default_config = load_config("configs/default.yaml")
        config = default_config.get("echomimic", {})
        if not config and "engines" in default_config and "echomimic" in default_config.engines:
            config = default_config.engines.echomimic
    
    if not config:
        print("错误: 无法加载EchoMimicV2配置")
        return False
    
    # 初始化EchoMimicV2集成
    try:
        echomimic_integration = EchoMimicIntegration(config)
        print("EchoMimicV2集成初始化成功")
    except Exception as e:
        print(f"EchoMimicV2集成初始化失败: {str(e)}")
        return False
    
    # 读取音频文件
    try:
        async with aiofiles.open(audio_file_path, 'rb') as f:
            audio_data = await f.read()
        
        print(f"加载音频文件: {audio_file_path}, 大小: {len(audio_data)} 字节")
        
        # 确定音频格式
        audio_format = os.path.splitext(audio_file_path)[1].lstrip('.')
        if not audio_format:
            audio_format = "mp3"  # 默认格式
        
        # 处理音频生成视频
        print("开始处理音频生成视频...")
        video_path = await echomimic_integration.process_tts_output(audio_data, audio_format)
        
        print(f"视频生成成功: {video_path}")
        return True
    except Exception as e:
        print(f"处理音频生成视频失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_text_to_video(text, config_path="configs/engines/echomimic/default.yaml"):
    """测试从文本生成视频"""
    print(f"加载配置文件: {config_path}")
    
    # 加载echomimic配置
    if os.path.exists(config_path):
        config = load_config(config_path)
    else:
        # 加载默认配置并提取echomimic部分
        default_config = load_config("configs/default.yaml")
        config = default_config.get("echomimic", {})
        if not config and "engines" in default_config and "echomimic" in default_config.engines:
            config = default_config.engines.echomimic
    
    if not config:
        print("错误: 无法加载EchoMimicV2配置")
        return False
    
    # 从环境变量或配置文件中获取TTS配置
    from pipelines.speech import SpeechProcessor
    print("初始化语音处理器...")
    
    # 加载完整配置
    full_config = load_config("configs/default.yaml")
    speech_processor = SpeechProcessor(full_config)
    
    # 初始化EchoMimicV2集成
    try:
        echomimic_integration = EchoMimicIntegration(config)
        print("EchoMimicV2集成初始化成功")
    except Exception as e:
        print(f"EchoMimicV2集成初始化失败: {str(e)}")
        return False
    
    # 生成TTS
    try:
        from utils.protocol import TextMessage
        print(f"处理文本转语音: {text}")
        text_message = TextMessage(text=text)
        audio_output = await speech_processor.text_to_speech(text_message)
        
        print(f"语音合成成功，格式: {audio_output.format.value}, 大小: {len(audio_output.data)} 字节")
        
        # 处理音频生成视频
        print("开始处理音频生成视频...")
        video_path = await echomimic_integration.process_tts_output(
            audio_output.data,
            audio_output.format.value
        )
        
        print(f"视频生成成功: {video_path}")
        return True
    except Exception as e:
        print(f"文本到视频生成失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def list_pose_dirs_and_ref_images():
    """列出可用的姿势数据目录和参考图像"""
    # 加载配置
    config = load_config("configs/default.yaml")
    echomimic_config = config.get("echomimic", {})
    if not echomimic_config and "engines" in config and "echomimic" in config.engines:
        echomimic_config = config.engines.echomimic
    
    if not echomimic_config:
        print("错误: 无法加载EchoMimicV2配置")
        return
    
    # 初始化EchoMimicV2集成
    try:
        echomimic_integration = EchoMimicIntegration(echomimic_config)
        print("EchoMimicV2集成初始化成功")
    except Exception as e:
        print(f"EchoMimicV2集成初始化失败: {str(e)}")
        return
    
    # 获取姿势数据目录
    try:
        echomimic_path = echomimic_integration.echomimic_path
        pose_dirs = await EchoMimicIntegration.get_available_pose_dirs(echomimic_path)
        print("\n可用的姿势数据目录:")
        for i, pose_dir in enumerate(pose_dirs, 1):
            print(f"{i}. {pose_dir}")
        
        # 获取参考图像
        ref_images = await EchoMimicIntegration.get_available_reference_images(echomimic_path)
        print("\n可用的参考图像:")
        for i, ref_image in enumerate(ref_images, 1):
            print(f"{i}. {ref_image}")
    except Exception as e:
        print(f"获取可用资源失败: {str(e)}")
        import traceback
        traceback.print_exc()

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="测试EchoMimicV2集成")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 音频到视频命令
    audio_parser = subparsers.add_parser("audio", help="音频到视频测试")
    audio_parser.add_argument("--audio_file", "-a", type=str, required=True,
                             help="音频文件路径")
    audio_parser.add_argument("--config", "-c", type=str, 
                             default="configs/engines/echomimic/default.yaml",
                             help="配置文件路径")
    
    # 文本到视频命令
    text_parser = subparsers.add_parser("text", help="文本到视频测试")
    text_parser.add_argument("--text", "-t", type=str, required=True,
                            help="要合成的文本")
    text_parser.add_argument("--config", "-c", type=str, 
                            default="configs/engines/echomimic/default.yaml",
                            help="配置文件路径")
    
    # 列出资源命令
    list_parser = subparsers.add_parser("list", help="列出可用资源")
    
    return parser.parse_args()

async def main():
    """主函数"""
    args = parse_args()
    
    if args.command == "audio":
        success = await test_audio_to_video(args.audio_file, args.config)
        if success:
            print("音频到视频测试成功")
        else:
            print("音频到视频测试失败")
    elif args.command == "text":
        success = await test_text_to_video(args.text, args.config)
        if success:
            print("文本到视频测试成功")
        else:
            print("文本到视频测试失败")
    elif args.command == "list":
        await list_pose_dirs_and_ref_images()
    else:
        print("请指定子命令: audio, text, 或 list")

if __name__ == "__main__":
    asyncio.run(main())
