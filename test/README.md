# 数字人项目测试工具

本目录包含用于测试数字人项目各个组件的测试脚本。

## 增强型网络搜索工具测试

### 环境变量设置

在运行搜索工具测试前，需要设置以下环境变量：

- `GOOGLE_API_KEY`: Google API密钥
- `GOOGLE_SEARCH_ENGINE_ID`: Google自定义搜索引擎ID
- `FIRECRAWL_API_KEY`: Firecrawl API密钥

您可以通过以下方式设置环境变量：

1. 在终端中直接设置：

   ```bash
   export GOOGLE_API_KEY="your_api_key"
   export GOOGLE_SEARCH_ENGINE_ID="your_search_engine_id"
   export FIRECRAWL_API_KEY="your_firecrawl_api_key"
   ```

2. 使用提供的脚本（需要先编辑脚本填入您的API密钥）：

   ```bash
   ./test/run_search_test.sh
   ```

3. 创建`.env`文件（基于项目根目录的`.env.example`）并使用dotenv加载

### 运行测试

直接测试增强型网络搜索工具：

```bash
python test/test_search_tool_direct.py --query "您的搜索查询" [选项]
```

可用选项：

- `--google-results`: Google搜索结果数量（默认为8）
- `--detailed-results`: 详细内容结果数量（默认为3）
- `--language`: 搜索语言（默认为"zh-CN"）
- `--output`: 输出文件路径（可选，默认保存在test_outputs目录）

### 测试输出

测试结果将保存在`test_outputs/search_tool_direct/`目录下，文件名格式为：
`search_[查询关键词]_[时间戳].txt`

## OpenAI Agent工具调用测试

### 环境变量设置

在运行OpenAI Agent测试前，需要设置以下环境变量：

- `OPENAI_API_KEY`: OpenAI API密钥
- `GOOGLE_API_KEY`: Google API密钥（如果使用网络搜索工具）
- `GOOGLE_SEARCH_ENGINE_ID`: Google自定义搜索引擎ID（如果使用网络搜索工具）
- `FIRECRAWL_API_KEY`: Firecrawl API密钥（如果使用网络搜索工具）

您可以通过以下方式设置环境变量：

1. 在终端中直接设置环境变量
2. 使用提供的脚本（需要先编辑脚本填入您的API密钥）：

   ```bash
   ./test/run_openai_agent_test.sh
   ```

3. 创建`.env`文件（基于项目根目录的`.env.example`）

### 运行测试

测试OpenAI Agent工具调用：

```bash
python test/test_openai_agent_tools.py --query "您的查询" [选项]
```

可用选项：

- `--model`: OpenAI模型名称（默认为"gpt-4o"）
- `--output`: 输出文件路径（可选，默认保存在test_outputs目录）

### 测试输出

测试结果将保存在`test_outputs/openai_agent/`目录下，文件名格式为：
`agent_[查询关键词]_[时间戳].txt`

## 其他测试工具

待添加...
