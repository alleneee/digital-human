#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import asyncio
import aiohttp
import base64
import logging
import subprocess
import tempfile
import time
import traceback
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# API配置
MINIMAX_GROUP_ID = os.getenv('MINIMAX_GROUP_ID')
MINIMAX_API_KEY = os.getenv('MINIMAX_API_KEY')
DEFAULT_CHAT_MODEL = 'abab6.5s-chat'  # 高级对话模型，支持函数调用
DEFAULT_TTS_MODEL = 'speech-01-turbo-240228'  # TTS模型
DEFAULT_VOICE = 'female-tianmei'  # 默认语音
API_URL = f"https://api.minimax.chat/v1/text/chatcompletion_v2?GroupId={MINIMAX_GROUP_ID}"

# 确保输出目录存在
TEST_OUTPUT_DIR = Path('test_outputs')
TEST_OUTPUT_DIR.mkdir(exist_ok=True)

# 检查mpv是否已安装
def check_mpv_installed():
    try:
        subprocess.run(["which", "mpv"], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        logger.warning("mpv未安装，将无法播放音频。请使用brew install mpv安装")
        return False

# 初始化mpv进程相关变量
mpv_process = None
mpv_fifo_path = None

# 初始化MPV播放器
def init_mpv():
    """初始化MPV播放器，使用命名管道(FIFO)进行音频传输"""
    global mpv_process, mpv_fifo_path
    
    if not check_mpv_installed():
        logger.warning("mpv未安装，将只保存音频文件而不播放")
        return False
    
    try:
        # 创建临时FIFO文件
        fifo_dir = tempfile.mkdtemp()
        fifo_path = os.path.join(fifo_dir, f"minimax_audio_{int(time.time())}.fifo")
        mpv_fifo_path = fifo_path
        
        # 创建FIFO
        try:
            os.mkfifo(fifo_path)
        except OSError as e:
            logger.error(f"创建FIFO失败: {e}")
            return False
        
        # 启动MPV播放器，设置较大的缓冲区
        mpv_command = [
            "mpv", 
            "--no-cache", 
            "--no-terminal", 
            "--no-video", 
            "--audio-buffer=1024",  # 1秒以上的音频缓冲
            "--demuxer-max-bytes=1048576",  # 1MB最大缓冲
            fifo_path
        ]
        
        mpv_process = subprocess.Popen(
            mpv_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # 打开FIFO进行写入
        mpv_stdin = open(fifo_path, 'wb')
        mpv_process.stdin = mpv_stdin
        logger.info(f"MPV播放器初始化成功，使用FIFO: {fifo_path}")
        return True
    except Exception as e:
        logger.error(f"MPV初始化错误: {e}")
        traceback.print_exc()
        cleanup_mpv()
        return False

# 清理MPV资源
def cleanup_mpv():
    """清理MPV相关资源"""
    global mpv_process, mpv_fifo_path
    
    if mpv_process:
        try:
            if hasattr(mpv_process, 'stdin') and mpv_process.stdin:
                mpv_process.stdin.close()
            mpv_process.terminate()
            mpv_process.wait(timeout=2)
        except Exception as e:
            logger.warning(f"关闭MPV进程时出错: {e}")
        finally:
            mpv_process = None
    
    if mpv_fifo_path and os.path.exists(mpv_fifo_path):
        try:
            os.unlink(mpv_fifo_path)
            os.rmdir(os.path.dirname(mpv_fifo_path))
        except Exception as e:
            logger.warning(f"清理FIFO文件时出错: {e}")
        finally:
            mpv_fifo_path = None
    
    logger.info("MPV资源已清理")

# 创建请求payload
def create_chat_payload(prompt: str, enable_voice: bool = False, 
                       enable_search: bool = False) -> Dict[str, Any]:
    """创建对话API请求参数"""
    payload = {
        "model": DEFAULT_CHAT_MODEL,
        "messages": [
            {
                "role": "system",
                "name": "MM智能助理", 
                "content": "MM智能助理是一款由MiniMax自研的，没有调用其他产品的接口的大型语言模型。MiniMax是一家中国科技公司，一直致力于进行大模型相关的研究。"
            },
            {
                "role": "user",
                "name": "用户", 
                "content": prompt
            }
        ],
        "stream": True,
        "max_tokens": 2048  # 增加最大token数量
    }
    
    # 如果启用语音输出
    if enable_voice:
        payload["stream_options"] = {"speech_output": True}
        payload["voice_setting"] = {
            "model": DEFAULT_TTS_MODEL,
            "voice_id": DEFAULT_VOICE,
            "speed": 1.0,     # 正常语速
            "vol": 1.0,       # 正常音量
            "pitch": 0        # 正常音调
        }
        payload["audio_setting"] = {
            "sample_rate": 24000,  # 较低的采样率以减小数据量
            "bitrate": 64000,      # 较低的比特率以减小数据量
            "format": "mp3",       # 使用MP3格式
            "channel": 1,          # 单声道
            "encode": "base64"     # 使用base64编码音频数据，更易于处理
        }
    
    # 如果启用网络搜索
    if enable_search:
        payload["tools"] = [{"type": "web_search"}]
        payload["tool_choice"] = "auto"
        
    return payload

# 处理流式响应并保存/播放音频
async def handle_chat_response(response, test_name: str):
    """处理流式响应，包括文本和音频"""
    full_text_response = ""
    audio_chunks = []
    json_responses = []
    
    buffer = ""
    async for chunk in response.content:
        try:
            chunk_str = chunk.decode('utf-8')
            
            # 处理可能跨多行的数据
            buffer += chunk_str
            lines = buffer.split('\n')
            buffer = lines.pop()
            
            for line in lines:
                if not line.startswith('data: '):
                    continue
                    
                line = line[6:].strip()  # 去掉 'data: ' 前缀
                
                if not line or line == '[DONE]':
                    continue
                    
                try:
                    chunk_data = json.loads(line)
                    json_responses.append(chunk_data)
                    
                    # 处理文本内容
                    if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                        if 'delta' in chunk_data['choices'][0]:
                            delta = chunk_data['choices'][0]['delta']
                            
                            # 处理文本回复
                            if 'content' in delta and delta['content']:
                                content = delta['content']
                                full_text_response += content
                                print(content, end='', flush=True)
                                
                            # 处理音频回复
                            if 'audio_content' in delta and delta['audio_content']:
                                audio_chunks.append(delta['audio_content'])
                                
                                # 实时播放音频（如果mpv已初始化）
                                if mpv_process and delta['audio_content'] != "":
                                    try:
                                        # 根据编码方式解码
                                        if 'encode' in chunk_data.get('voice_setting', {}).get('audio_setting', {}) and \
                                           chunk_data['voice_setting']['audio_setting']['encode'] == 'base64':
                                            # base64解码
                                            try:
                                                decoded_audio = base64.b64decode(delta['audio_content'])
                                            except Exception:
                                                # 处理可能的填充问题
                                                padding_needed = len(delta['audio_content']) % 4
                                                if padding_needed:
                                                    padded = delta['audio_content'] + '=' * (4 - padding_needed)
                                                    decoded_audio = base64.b64decode(padded)
                                                else:
                                                    raise
                                        else:
                                            # 十六进制解码
                                            decoded_audio = bytes.fromhex(delta['audio_content'])
                                            
                                        mpv_process.stdin.write(decoded_audio)
                                        mpv_process.stdin.flush()
                                    except Exception as e:
                                        logger.warning(f"播放音频块时出错: {str(e)}")
                            
                            # 处理工具调用（如网络搜索）
                            if 'tool_calls' in delta:
                                logger.info(f"工具调用: {delta['tool_calls']}")
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"解析JSON失败: {line[:100]}... 错误: {str(e)}")
        except Exception as e:
            logger.warning(f"处理响应块时出错: {str(e)}")
    
    print("\n")  # 换行
    
    # 保存完整文本响应
    text_output_path = TEST_OUTPUT_DIR / f"advanced_text_{test_name.replace(' ', '_')}.txt"
    with open(text_output_path, "w", encoding='utf-8') as f:
        f.write(full_text_response)
    logger.info(f"✓ 测试 - {test_name} 文本响应已保存到: {text_output_path}")
    
    # 保存完整JSON响应
    json_output_path = TEST_OUTPUT_DIR / f"advanced_json_{test_name.replace(' ', '_')}.json"
    with open(json_output_path, "w", encoding='utf-8') as f:
        json.dump(json_responses, f, ensure_ascii=False, indent=2)
    logger.info(f"✓ 测试 - {test_name} JSON响应已保存到: {json_output_path}")
    
    # 如果有音频数据，保存为MP3文件
    if audio_chunks:
        audio_data = b""
        error_count = 0
        success_count = 0
        is_base64 = False
        
        # 检查第一个音频块，判断编码方式
        if audio_chunks and len(audio_chunks) > 0:
            # 检测是否为base64编码（通过检查是否包含非十六进制字符）
            sample = audio_chunks[0]
            if any(c for c in sample if c not in '0123456789abcdefABCDEF'):
                is_base64 = True
                logger.info("检测到音频为base64编码")
            else:
                logger.info("检测到音频为十六进制编码")
        
        # 处理音频块
        for i, chunk in enumerate(audio_chunks):
            try:
                if is_base64:
                    # 处理base64编码
                    try:
                        decoded_data = base64.b64decode(chunk)
                    except Exception:
                        # 处理可能的填充问题
                        padding_needed = len(chunk) % 4
                        if padding_needed:
                            padded = chunk + '=' * (4 - padding_needed)
                            decoded_data = base64.b64decode(padded)
                        else:
                            raise
                else:
                    # 处理十六进制编码
                    clean_chunk = ''.join(c for c in chunk if c.lower() in '0123456789abcdef')
                    if len(clean_chunk) % 2 != 0:
                        clean_chunk = clean_chunk[:-1]  # 确保长度是偶数
                    decoded_data = bytes.fromhex(clean_chunk) if clean_chunk else b""
                
                if decoded_data:
                    audio_data += decoded_data
                    success_count += 1
            except Exception as e:
                error_count += 1
                if error_count < 5:  # 只记录前几个错误
                    logger.warning(f"解码第{i+1}个音频块时出错: {str(e)}，块长度: {len(chunk)[:20]}...")
        
        logger.info(f"音频块总数: {len(audio_chunks)}, 成功解码: {success_count}, 失败: {error_count}")
        
        if audio_data:
            # 保存和播放音频
            audio_output_path = TEST_OUTPUT_DIR / f"advanced_audio_{test_name.replace(' ', '_')}.mp3"
            with open(audio_output_path, "wb") as f:
                f.write(audio_data)
            logger.info(f"✓ 测试 - {test_name} 音频已保存到: {audio_output_path}")
            
            # 使用系统默认播放器播放音频（作为mpv的备选方案）
            if not mpv_process and os.path.exists(audio_output_path):
                try:
                    logger.info(f"尝试使用系统默认播放器播放音频: {audio_output_path}")
                    subprocess.Popen(["open", str(audio_output_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as e:
                    logger.warning(f"无法使用系统播放器播放音频: {str(e)}")
        else:
            logger.warning(f"测试 - {test_name} 未能解码任何音频数据")

# 测试高级聊天功能
async def test_advanced_chat(prompt: str, test_name: str, 
                          enable_voice: bool = False, 
                          enable_search: bool = False):
    """测试MiniMax高级对话API，包括语音输出和网络搜索"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MINIMAX_API_KEY}"
    }
    
    payload = create_chat_payload(prompt, enable_voice, enable_search)
    
    logger.info(f"测试: {test_name}")
    logger.info(f"启用语音: {enable_voice}, 启用搜索: {enable_search}")
    logger.info(f"请求URL: {API_URL}")
    logger.info(f"请求参数: {json.dumps(payload, ensure_ascii=False)[:200]}...")
    
    try:
        timeout = aiohttp.ClientTimeout(total=60)  # 增加超时时间到60秒
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(API_URL, headers=headers, json=payload) as response:
                logger.info(f"测试 - {test_name} 响应状态码: {response.status}")
                logger.info(f"测试 - {test_name} 响应内容类型: {response.content_type}")
                
                if response.status == 200:
                    await handle_chat_response(response, test_name)
                else:
                    error_text = await response.text()
                    logger.error(f"测试 - {test_name} 请求失败: {error_text}")
                    
    except asyncio.TimeoutError:
        logger.error(f"测试 - {test_name} 请求超时")
    except Exception as e:
        logger.error(f"测试 - {test_name} 请求异常: {str(e)}")

# 主测试函数
async def run_advanced_tests():
    """运行多个高级测试用例"""
    logger.info("开始测试MiniMax高级API功能...")
    
    # 初始化mpv（用于播放音频）
    init_mpv()
    
    # 测试用例 - 注意：语音测试用更简短的文本减少数据量
    test_cases = [
        {
            "name": "基础对话",
            "prompt": "你好，请介绍一下你自己",
            "enable_voice": False,
            "enable_search": False
        },
        {
            "name": "简短语音",  # 使用非常简短的提示减少生成的音频数据量
            "prompt": "你好",    # 使用最简短的问候语
            "enable_voice": True,
            "enable_search": False
        },
        {
            "name": "网络搜索",
            "prompt": "2022年世界杯冠军是哪个国家？",  # 更加具体的问题
            "enable_voice": False,
            "enable_search": True
        },
        {
            "name": "简短语音加搜索",  # 同样使用简短提示
            "prompt": "今天的天气怎么样？",  # 简单的问题
            "enable_voice": True,
            "enable_search": True
        }
    ]
    
    # 执行测试
    for i, test_case in enumerate(test_cases, 1):
        name = test_case["name"]
        prompt = test_case["prompt"]
        enable_voice = test_case["enable_voice"]
        enable_search = test_case["enable_search"]
        
        logger.info(f"测试 {i}/{len(test_cases)} - {name}")
        # 对于语音测试，可能需要重新初始化播放器
        if enable_voice and not mpv_process:
            logger.info("语音测试前重新初始化MPV播放器")
            init_mpv()
        
        # 尝试最多3次
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await test_advanced_chat(
                    prompt, 
                    name, 
                    enable_voice, 
                    enable_search
                )
                # 成功则跳出重试循环
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"测试 {name} 第{attempt+1}次尝试失败: {e}，将重试...")
                    await asyncio.sleep(3)  # 重试前稍等一会
                else:
                    logger.error(f"测试 {name} 在{max_retries}次尝试后仍然失败: {e}")
        
        # 测试间隔增加到3秒
        await asyncio.sleep(3)  # 适当延迟，避免API请求过于频繁
    
    logger.info("MiniMax高级API功能测试完成")
    
    # 清理MPV资源
    cleanup_mpv()

if __name__ == "__main__":
    try:
        asyncio.run(run_advanced_tests())
    except KeyboardInterrupt:
        logger.info("用户中断测试")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        traceback.print_exc()
    finally:
        # 确保清理所有资源
        cleanup_mpv()
