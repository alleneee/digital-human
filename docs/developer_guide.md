# 数字人框架开发指南

本文档为开发者提供在数字人框架上进行开发和扩展的详细指导。

## 环境配置

### 开发环境准备

1. **Python环境**：推荐使用Python 3.8+
2. **虚拟环境**：建议使用虚拟环境进行开发

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 环境变量设置

开发过程中，可以使用`.env`文件或直接设置环境变量：

```
# OpenAI相关
OPENAI_API_KEY=your_api_key

# MiniMax相关
MINIMAX_API_KEY=your_api_key
MINIMAX_GROUP_ID=your_group_id

# 配置文件路径
DH_CONFIG=configs/dev.yaml
```

## 开发新引擎

### ASR引擎开发流程

1. **创建引擎类**

在`engine/asr/`目录下创建新的引擎文件，如`myASR.py`：

```python
# -*- coding: utf-8 -*-
'''
自定义ASR引擎
'''

from typing import Optional, Dict, Any, List, Union
from yacs.config import CfgNode as CN
from engine.engineBase import BaseEngine
from utils.protocol import AudioMessage, TextMessage
from engine.asr.asrFactory import ASRFactory

@ASRFactory.register_engine("MyASR")  # 注册引擎，名称为"MyASR"
class MyASR(BaseEngine):
    """我的自定义ASR引擎"""
    
    def checkKeys(self) -> List[str]:
        """检查必要的配置键"""
        return ["NAME", "API_KEY"]  # 列出必需的配置项
    
    async def run(self, input: Union[AudioMessage, List[AudioMessage]], **kwargs):
        """处理音频输入，返回文本结果"""
        # 实现音频处理逻辑
        # ...
        
        # 返回TextMessage
        return TextMessage(text="识别结果文本")
    
    def release(self):
        """释放资源"""
        pass
```

2. **创建配置文件**

在`configs/engines/asr/`目录下创建配置文件，如`myasr.yaml`：

```yaml
# 自定义ASR引擎配置
NAME: "MyASR"
TYPE: "ASR"
API_KEY: ""  # 可以从环境变量加载
# 其他配置项...
```

### LLM引擎开发流程

类似ASR引擎，在`engine/llm/`目录下创建新的引擎文件，并在`configs/engines/llm/`中添加相应配置。

```python
from engine.engineBase import BaseEngine
from engine.llm.llmFactory import LLMFactory
from utils.protocol import TextMessage

@LLMFactory.register_engine("MyLLM")
class MyLLM(BaseEngine):
    """自定义LLM引擎"""
    
    # 实现必要方法...
```

### TTS引擎开发流程

在`engine/tts/`目录下创建新的引擎文件，并在`configs/engines/tts/`中添加相应配置。

```python
from engine.engineBase import BaseEngine
from engine.tts.ttsFactory import TTSFactory
from utils.protocol import TextMessage, AudioMessage

@TTSFactory.register_engine("MyTTS")
class MyTTS(BaseEngine):
    """自定义TTS引擎"""
    
    # 实现必要方法...
```

## 扩展API接口

在`api/routes.py`中添加新的API端点：

```python
@router.post("/custom_endpoint", response_model=CustomResponse)
async def custom_endpoint(request: CustomRequest, api_service: APIService = Depends(get_api_service)):
    """自定义API端点"""
    # 实现逻辑...
    return CustomResponse(...)
```

## 调试与测试

### 运行测试

使用Python的`unittest`或`pytest`运行测试：

```bash
# 运行所有测试
python -m pytest test/

# 运行特定测试
python -m pytest test/test_asr.py
```

### 调试技巧

1. **日志调试**：使用框架的日志系统

```python
import logging
logger = logging.getLogger(__name__)

# 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
logger.debug("详细调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
```

2. **交互式调试**：使用Python交互式解释器或IPython

```bash
# 启动交互式环境
python -m IPython

# 导入模块
from pipelines.conversation import ConversationPipeline
from utils.config import load_config

# 测试组件
cfg = load_config("configs/default.yaml")
pipeline = ConversationPipeline(cfg)
# ...
```

## 性能优化

### 异步处理

框架大量使用异步编程（asyncio），确保异步函数使用`async/await`语法：

```python
async def process_data(data):
    # 异步处理...
    result = await some_async_function()
    return result
```

### 缓存策略

对于频繁使用的数据，可以实现缓存：

```python
# 简单的内存缓存
_cache = {}

async def get_data_with_cache(key):
    if key in _cache:
        return _cache[key]
    
    data = await fetch_data(key)
    _cache[key] = data
    return data
```

## 部署指南

### 生产环境配置

创建专用的生产环境配置文件`configs/production.yaml`：

```yaml
# 生产环境配置
NAME: "DigitalHuman"

# API配置
API:
  HOST: "0.0.0.0"
  PORT: 8000

# 日志配置
LOGGING:
  LEVEL: "INFO"
  FILE: "/var/log/digital-human/app.log"

# 其他生产特定配置...
```

### 容器化部署

使用Docker进行容器化部署：

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py", "--config", "configs/production.yaml"]
```

## 常见问题（FAQ）

### 1. 如何切换引擎？

在配置文件中修改相应引擎的`NAME`配置项，例如：

```yaml
# 切换LLM引擎
LLM:
  ENABLED: true
  NAME: "MyLLM"  # 切换为自定义LLM引擎
```

### 2. 如何处理大文件上传？

对于大型音频文件，建议使用分块上传和流式处理：

```python
@router.post("/upload_large_audio")
async def upload_large_audio(file: UploadFile = File(...)):
    # 流式处理上传文件
    content = await file.read(1024)  # 每次读取1KB
    while content:
        # 处理数据块
        process_chunk(content)
        content = await file.read(1024)
    
    return {"status": "success"}
```

### 3. 如何优化响应时间？

- 使用本地模型代替云API
- 实现结果缓存
- 优化音频格式和质量
- 调整异步处理策略

## 贡献指南

1. Fork项目仓库
2. 创建功能分支：`git checkout -b feature/my-feature`
3. 提交更改：`git commit -am '添加新功能'`
4. 推送分支：`git push origin feature/my-feature`
5. 提交Pull Request
