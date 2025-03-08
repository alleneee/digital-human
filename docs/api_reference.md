# 数字人框架API参考文档

本文档详细介绍数字人框架提供的所有API端点、请求格式和响应结构。

## API概述

数字人框架通过FastAPI实现REST API，提供以下主要功能：

- 文本交互
- 语音交互
- 语音识别
- 语音合成
- 系统管理

所有API端点默认位于`http://[host]:[port]/`下。

## 公共数据结构

### AudioMessage

表示音频消息的数据结构。

```python
{
    "audio_data": "base64编码的音频数据",
    "format_type": "音频格式类型(WAV/MP3/OGG/FLAC等)",
    "sample_rate": 16000,  # 采样率
    "language": "zh-CN",   # 语言代码
    "duration": 1.5        # 音频长度(秒)
}
```

### TextMessage

表示文本消息的数据结构。

```python
{
    "text": "文本内容",
    "language": "zh-CN"    # 语言代码
}
```

## API端点

### 健康检查

#### GET /health

检查服务健康状态。

**响应**:
```json
{
    "status": "ok",
    "version": "1.0.0",
    "engines": {
        "asr": "funasrASR",
        "llm": "openaiLLM",
        "tts": "edgeTTS"
    }
}
```

### 文本交互

#### POST /api/chat/text

通过文本与数字人交互。

**请求体**:
```json
{
    "text": "你好，请问今天天气怎么样？",
    "language": "zh-CN",
    "return_audio": true,
    "conversation_id": "会话ID（可选）"
}
```

**响应**:
```json
{
    "response": {
        "text": "您好！根据我的信息，我无法获取实时天气数据。您可以通过查看天气预报应用或网站来获取今天的天气信息。",
        "language": "zh-CN"
    },
    "audio": {
        "audio_data": "base64编码的音频数据",
        "format_type": "WAV",
        "sample_rate": 16000,
        "language": "zh-CN",
        "duration": 3.5
    },
    "conversation_id": "生成的会话ID",
    "processing_time": 1.2,  # 处理时间(秒)
    "metadata": {
        "model": "gpt-3.5-turbo",
        "voice": "zh-CN-XiaoxiaoNeural"
    }
}
```

### 语音交互

#### POST /api/chat/audio

通过语音与数字人交互。

**请求体**:
```json
{
    "audio": {
        "audio_data": "base64编码的音频数据",
        "format_type": "WAV",
        "sample_rate": 16000,
        "language": "zh-CN"
    },
    "return_text": true,
    "return_audio": true,
    "conversation_id": "会话ID（可选）"
}
```

**响应**:
```json
{
    "transcription": {
        "text": "你好，请问今天天气怎么样？",
        "language": "zh-CN"
    },
    "response": {
        "text": "您好！根据我的信息，我无法获取实时天气数据。您可以通过查看天气预报应用或网站来获取今天的天气信息。",
        "language": "zh-CN"
    },
    "audio": {
        "audio_data": "base64编码的音频数据",
        "format_type": "WAV",
        "sample_rate": 16000,
        "language": "zh-CN",
        "duration": 3.5
    },
    "conversation_id": "生成的会话ID",
    "processing_time": 2.5,  # 处理时间(秒)
    "metadata": {
        "asr_model": "funasrASR",
        "llm_model": "gpt-3.5-turbo",
        "tts_voice": "zh-CN-XiaoxiaoNeural"
    }
}
```

#### POST /api/chat/audio/stream

提供流式语音交互，使用WebSocket实现实时响应。

**WebSocket连接**:
`ws://[host]:[port]/api/chat/audio/stream`

**WebSocket消息格式**:

客户端发送:
```json
{
    "type": "audio_chunk",
    "audio_data": "base64编码的音频数据块",
    "format_type": "WAV",
    "is_end": false,  # 是否为最后一个块
    "conversation_id": "会话ID（可选）"
}
```

服务端响应:
```json
{
    "type": "transcription_partial",  # 实时转写结果
    "text": "你好，请问",
    "is_final": false
}
```

```json
{
    "type": "transcription_final",  # 最终转写结果
    "text": "你好，请问今天天气怎么样？",
}
```

```json
{
    "type": "response_text",  # 文本响应
    "text": "您好！根据我的信息，我无法获取实时天气数据。"
}
```

```json
{
    "type": "response_audio_chunk",  # 音频响应块
    "audio_data": "base64编码的音频数据块",
    "format_type": "WAV",
    "is_end": false
}
```

```json
{
    "type": "done",  # 完成标志
    "conversation_id": "会话ID",
    "processing_time": 3.2
}
```

### 语音识别

#### POST /api/asr

将音频转换为文本。

**请求体**:
```json
{
    "audio": {
        "audio_data": "base64编码的音频数据",
        "format_type": "WAV",
        "sample_rate": 16000,
        "language": "zh-CN"
    },
    "engine": "funasrASR"  # 可选，指定ASR引擎
}
```

**响应**:
```json
{
    "text": "转写的文本内容",
    "language": "zh-CN",
    "confidence": 0.95,  # 置信度
    "processing_time": 0.5  # 处理时间(秒)
}
```

#### POST /api/asr/stream

提供流式语音识别，实时转写音频。

**WebSocket连接**:
`ws://[host]:[port]/api/asr/stream`

**WebSocket消息格式**:

客户端发送:
```json
{
    "type": "audio_chunk",
    "audio_data": "base64编码的音频数据块",
    "format_type": "WAV",
    "is_end": false,  # 是否为最后一个块
    "engine": "funasrASR"  # 可选，指定ASR引擎
}
```

服务端响应:
```json
{
    "type": "transcription_partial",
    "text": "部分转写结果",
    "is_final": false
}
```

```json
{
    "type": "transcription_final",
    "text": "最终转写结果",
    "processing_time": 1.2
}
```

### 语音合成

#### POST /api/tts

将文本转换为语音。

**请求体**:
```json
{
    "text": "要转换为语音的文本",
    "language": "zh-CN",
    "voice": "zh-CN-XiaoxiaoNeural",  # 声音选项
    "engine": "edgeTTS",  # 可选，指定TTS引擎
    "speed": 1.0,  # 语速
    "pitch": 0.0   # 音调
}
```

**响应**:
```json
{
    "audio": {
        "audio_data": "base64编码的音频数据",
        "format_type": "WAV",
        "sample_rate": 16000,
        "language": "zh-CN",
        "duration": 1.5
    },
    "processing_time": 0.3  # 处理时间(秒)
}
```

#### POST /api/tts/stream

提供流式语音合成，实时生成音频。

**WebSocket连接**:
`ws://[host]:[port]/api/tts/stream`

**WebSocket消息格式**:

客户端发送:
```json
{
    "text": "要转换为语音的文本",
    "language": "zh-CN",
    "voice": "zh-CN-XiaoxiaoNeural",
    "engine": "edgeTTS"
}
```

服务端响应:
```json
{
    "type": "audio_chunk",
    "audio_data": "base64编码的音频数据块",
    "format_type": "WAV",
    "is_end": false  # 是否为最后一个块
}
```

```json
{
    "type": "done",
    "processing_time": 0.8
}
```

### 系统管理

#### GET /api/system/info

获取系统运行信息。

**响应**:
```json
{
    "version": "1.0.0",
    "uptime": 3600,  # 运行时间(秒)
    "engines": {
        "asr": ["funasrASR"],
        "llm": ["openaiLLM", "minimaxLLM"],
        "tts": ["edgeTTS", "minimaxTTS"]
    },
    "statistics": {
        "requests": 156,
        "average_response_time": 1.2
    }
}
```

#### POST /api/system/reload

重新加载系统配置。

**请求体**:
```json
{
    "config_path": "configs/custom.yaml"  # 可选，指定配置文件路径
}
```

**响应**:
```json
{
    "status": "success",
    "message": "配置已重新加载",
    "updated_components": ["asr", "llm", "tts"]
}
```

## 错误处理

所有API端点在发生错误时会返回标准HTTP错误代码和详细的错误信息。

**错误响应示例**:
```json
{
    "error": true,
    "code": "ENGINE_ERROR",
    "message": "ASR引擎处理失败",
    "details": "音频格式不支持或音频损坏"
}
```

### 常见错误代码

| 错误代码 | 描述 |
|---------|------|
| INVALID_REQUEST | 请求格式错误或缺少必要参数 |
| ENGINE_ERROR | 引擎处理失败 |
| AUDIO_ERROR | 音频处理错误 |
| AUTH_ERROR | 认证失败 |
| RATE_LIMIT | 超出速率限制 |
| SERVER_ERROR | 服务器内部错误 |

## 使用示例

### Python客户端示例

```python
import requests
import base64
import json

# 文本聊天示例
def text_chat():
    url = "http://localhost:8000/api/chat/text"
    payload = {
        "text": "你好，介绍一下你自己",
        "language": "zh-CN",
        "return_audio": True
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    print("回复文本:", data["response"]["text"])
    
    # 保存音频
    if "audio" in data:
        audio_data = base64.b64decode(data["audio"]["audio_data"])
        with open("response.wav", "wb") as f:
            f.write(audio_data)
        print("音频已保存为 response.wav")

# 音频聊天示例
def audio_chat(audio_file_path):
    url = "http://localhost:8000/api/chat/audio"
    
    # 读取音频文件
    with open(audio_file_path, "rb") as f:
        audio_data = f.read()
    
    # Base64编码
    audio_base64 = base64.b64encode(audio_data).decode("utf-8")
    
    payload = {
        "audio": {
            "audio_data": audio_base64,
            "format_type": "WAV",  # 根据实际文件格式修改
            "sample_rate": 16000,
            "language": "zh-CN"
        },
        "return_text": True,
        "return_audio": True
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    print("识别文本:", data["transcription"]["text"])
    print("回复文本:", data["response"]["text"])
    
    # 保存音频
    if "audio" in data:
        audio_data = base64.b64decode(data["audio"]["audio_data"])
        with open("response.wav", "wb") as f:
            f.write(audio_data)
        print("音频已保存为 response.wav")

if __name__ == "__main__":
    text_chat()
    # audio_chat("input.wav")
```

### WebSocket流式交互示例

```python
import asyncio
import websockets
import json
import base64

async def stream_audio_chat(audio_file_path):
    uri = "ws://localhost:8000/api/chat/audio/stream"
    
    # 读取音频文件
    with open(audio_file_path, "rb") as f:
        audio_data = f.read()
    
    # 分块处理，每块10KB
    chunk_size = 10240
    audio_chunks = [audio_data[i:i+chunk_size] for i in range(0, len(audio_data), chunk_size)]
    
    async with websockets.connect(uri) as websocket:
        # 发送音频块
        for i, chunk in enumerate(audio_chunks):
            is_end = (i == len(audio_chunks) - 1)
            
            message = {
                "type": "audio_chunk",
                "audio_data": base64.b64encode(chunk).decode("utf-8"),
                "format_type": "WAV",
                "is_end": is_end
            }
            
            await websocket.send(json.dumps(message))
            
            # 接收实时响应
            while True:
                try:
                    # 设置超时时间，避免无限等待
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    data = json.loads(response)
                    
                    if data["type"] == "transcription_partial":
                        print(f"实时转写: {data['text']}")
                    elif data["type"] == "transcription_final":
                        print(f"最终转写: {data['text']}")
                    elif data["type"] == "response_text":
                        print(f"回复文本: {data['text']}")
                    elif data["type"] == "response_audio_chunk":
                        # 处理音频块
                        print("收到音频块...")
                        # 可以将音频块累积起来，最后合成完整音频
                    elif data["type"] == "done":
                        print(f"处理完成，耗时: {data['processing_time']}秒")
                        break
                    
                except asyncio.TimeoutError:
                    # 超时，等待下一个块
                    break

if __name__ == "__main__":
    asyncio.run(stream_audio_chat("input.wav"))
```
