# 数字人框架

数字人框架是一个模块化、可扩展的系统，集成了语音识别（ASR）、大语言模型（LLM）和语音合成（TTS）功能，为创建交互式数字人应用提供完整解决方案。该框架采用清晰的目录结构和标准化接口，确保各组件间无缝协作与灵活扩展。

## 功能特点

- **模块化设计**：ASR、LLM、TTS引擎可独立替换和扩展
- **异步处理**：基于Python asyncio实现的高性能异步处理流程
- **REST API**：提供完整的REST API接口，支持文本和音频交互
- **配置灵活**：基于YAML的配置系统，支持环境变量和配置合并
- **多引擎支持**：
  - ASR：支持FunASR本地模型
  - LLM：支持OpenAI GPT系列模型
  - TTS：支持Edge TTS和MiniMax TTS

## 系统架构

### 组件架构

```
+------------------+      +------------------+      +------------------+
|                  |      |                  |      |                  |
|  ASR Engine      +----->+  LLM Engine      +----->+  TTS Engine      |
|                  |      |                  |      |                  |
+------------------+      +------------------+      +------------------+
         ^                                                   |
         |                                                   |
         |               +------------------+                |
         |               |                  |                |
         +---------------+  Conversation    +<---------------+
                         |  Pipeline        |
                         |                  |
                         +------------------+
                                  ^
                                  |
                                  |
                         +------------------+
                         |                  |
                         |  FastAPI         |
                         |  Application     |
                         |                  |
                         +------------------+
```

### 目录结构

```
digital-human/
├── app.py                  # 主入口点
├── api/                    # API接口
│   └── routes.py           # API路由定义
├── configs/                # 配置文件
│   ├── default.yaml        # 默认配置
│   └── engines/            # 引擎特定配置
│       ├── asr/            # ASR引擎配置
│       ├── llm/            # LLM引擎配置
│       └── tts/            # TTS引擎配置
├── engine/                 # 引擎实现
│   ├── asr/                # ASR引擎
│   ├── llm/                # LLM引擎
│   └── tts/                # TTS引擎
├── integrations/           # 第三方集成
│   ├── deepgram.py         # Deepgram集成
│   └── minimax.py          # Minimax集成
├── pipelines/              # 处理管道
│   ├── conversation.py     # 对话管道
│   └── speech.py           # 语音处理
├── utils/                  # 工具函数
│   └── audio_processor.py  # 音频处理工具
└── test/                   # 测试脚本
```

## 快速开始

### 环境要求

- Python 3.8+
- 依赖包：详见`requirements.txt`

### 安装

1. 克隆项目：

```bash
git clone https://github.com/yourusername/digital-human.git
cd digital-human
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 配置环境变量（可选）：

```bash
# OpenAI API密钥（使用OpenAI LLM时需要）
export OPENAI_API_KEY=your_openai_api_key

# MiniMax API密钥（使用MiniMax TTS时需要）
export MINIMAX_API_KEY=your_minimax_api_key
export MINIMAX_GROUP_ID=your_minimax_group_id
```

### 配置

- 默认配置文件位于`configs/default.yaml`
- 引擎特定配置文件位于`configs/engines/{asr,llm,tts}/`目录下
- 可通过环境变量`DH_CONFIG`指定自定义配置文件路径

### 运行API服务

```bash
python app.py
```

默认情况下，API服务会在`http://0.0.0.0:8000`上启动。您也可以使用以下参数自定义运行方式：

```bash
python app.py --config configs/custom.yaml --host 127.0.0.1 --port 8888
```

## API接口

### 健康检查

```
GET /health
```

### 文本聊天

```
POST /api/chat/text
Content-Type: application/json

{
    "text": "你好，请问你是谁?"
}
```

### 音频聊天

```
POST /api/chat/audio
Content-Type: application/json

{
    "audio": "base64编码的音频数据",
    "format": "mp3"  # 音频格式：wav, mp3等
}
```

### 语音识别（ASR）

```
POST /api/asr
Content-Type: application/json

{
    "audio": "base64编码的音频数据",
    "format": "mp3"  # 音频格式
}
```

### 语音合成（TTS）

```
POST /api/tts
Content-Type: application/json

{
    "text": "要合成的文本内容"
}
```

## 测试

项目提供了多个测试脚本，用于测试不同组件的功能：

- `test_asr.py`：测试ASR引擎
- `test_llm.py`：测试LLM引擎
- `test_tts.py`：测试TTS引擎
- `test_conversation_pipeline.py`：测试完整对话流程
- `test_api.py`：测试API接口

### 运行测试

```bash
# 测试ASR引擎
python test_asr.py

# 测试LLM引擎
python test_llm.py

# 测试TTS引擎
python test_tts.py

# 测试对话流程（使用文本输入）
python test_conversation_pipeline.py --text "你好，请问你是谁?"

# 测试对话流程（使用音频输入）
python test_conversation_pipeline.py --audio "test_outputs/advanced_audio_简短语音.mp3"

# 测试API接口
python test_api.py --test all
```

## 扩展引擎

### 添加新的ASR引擎

1. 在`engine/asr/`目录下创建新的引擎实现类（如`myASR.py`）
2. 继承`BaseEngine`类并实现必要的方法
3. 使用`@ASREngines.register()`装饰器注册引擎
4. 在`configs/engines/asr/`目录下创建对应的配置文件

示例：

```python
from ..builder import ASREngines
from ..engineBase import BaseEngine

@ASREngines.register()
class MyASR(BaseEngine):
    def checkKeys(self):
        return ["NAME", "API_KEY"]
        
    def setup(self):
        # 初始化代码
        pass
        
    async def run(self, input, **kwargs):
        # 实现语音识别逻辑
        pass
```

### 添加新的LLM/TTS引擎

与添加ASR引擎类似，只需在相应目录下创建引擎实现类，并使用对应的装饰器注册。

## 许可证

[MIT许可证](LICENSE)

## 贡献

欢迎提交问题报告和拉取请求。对于重大更改，请先开启一个问题讨论您要更改的内容。
