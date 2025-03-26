# 增强型网络搜索工具测试指南

本文档介绍如何测试数字人项目中的增强型网络搜索工具。增强型网络搜索工具结合了Google搜索和Firecrawl网页抓取功能，能够提供更全面、更深入的搜索结果。

## 环境准备

在开始测试前，请确保已设置以下环境变量：

```bash
# OpenAI API密钥（用于Agent）
export OPENAI_API_KEY="your_openai_api_key"

# Google搜索API密钥和搜索引擎ID
export GOOGLE_API_KEY="your_google_api_key"
export GOOGLE_SEARCH_ENGINE_ID="your_search_engine_id"

# Firecrawl API密钥
export FIRECRAWL_API_KEY="your_firecrawl_api_key"
```

您可以将这些变量添加到`.env`文件中，然后使用以下命令加载：

```bash
source .env
```

## 测试方法

我们提供了多种测试脚本，可以从不同角度测试增强型网络搜索功能：

### 1. 直接测试搜索工具函数

这种方法直接调用搜索工具函数，不通过Agent：

```bash
python test/test_search_tool_direct.py --query "数字人技术的最新进展"
```

参数说明：

- `--query`: 搜索查询（必需）
- `--google-results`: Google搜索结果数量（默认8）
- `--detailed-results`: 详细内容结果数量（默认3）
- `--language`: 搜索语言（默认zh-CN）
- `--output`: 输出文件路径（可选）

### 2. 使用OpenAI Agent库测试

这种方法使用OpenAI Agent库直接创建Agent并测试：

```bash
python test/test_enhanced_search.py
```

这个脚本会使用预定义的查询列表进行测试，并将结果保存到`test_outputs/enhanced_search`目录。

### 3. 使用项目配置系统测试

这种方法使用项目的配置系统创建Agent并测试：

```bash
python test/test_enhanced_search_with_config.py
```

这个脚本会加载`configs/agent.yaml`配置文件，创建Agent并使用预定义的查询列表进行测试，结果保存到`test_outputs/enhanced_search_config`目录。

### 4. 交互式测试

这种方法提供了一个交互式界面，您可以输入任意查询进行测试：

```bash
python test/interactive_agent.py
```

在交互式界面中，您可以：

- 输入任意查询并获取回复
- 输入`save`保存对话历史
- 输入`clear`清屏
- 输入`help`显示帮助信息
- 输入`exit`或`quit`退出程序

## 配置说明

增强型网络搜索工具的配置位于`configs/agent.yaml`文件中：

```yaml
custom_tools:
  # ... 其他工具 ...
  
  - name: "增强型网络搜索"
    enabled: true
    class: "engine.agent.tools.enhanced_web_search"
    params: {}
```

您可以根据需要调整配置参数。

## 工作原理

增强型网络搜索工具的工作流程如下：

1. 使用Google搜索API获取相关网页链接和预览内容
2. 过滤搜索结果，排除社交媒体等不太相关的网站
3. 选择最相关的几个链接
4. 使用Firecrawl API抓取这些链接的详细内容
5. 整合Google搜索概述和Firecrawl详细内容，生成完整的搜索报告

这种两阶段的搜索方法可以提供更全面、更深入的信息，特别适合需要详细了解某个主题的场景。

## 输出示例

增强型网络搜索工具的输出包含两部分：

1. **搜索结果概述**：来自Google搜索的简要结果，包括标题、链接和摘要
2. **详细内容**：来自Firecrawl的详细网页内容

输出格式示例：

```
### 搜索查询: '数字人技术的最新进展'

## 搜索结果概述

1. **数字人技术最新进展：虚拟形象与AI融合的未来**
   链接: https://example.com/article1
   摘要: 数字人技术正在快速发展，结合了计算机图形学、人工智能和语音合成等多种技术...

2. **2024年数字人行业研究报告**
   链接: https://example.com/article2
   摘要: 本报告分析了数字人技术的最新趋势和应用场景...

## 详细内容

### 1. 数字人技术最新进展：虚拟形象与AI融合的未来
来源: https://example.com/article1

数字人技术是指通过计算机图形学、人工智能、语音合成等技术，创建具有人类外观和行为特征的虚拟形象。近年来，随着深度学习和生成式AI的发展，数字人技术取得了显著进步...

---

### 2. 2024年数字人行业研究报告
来源: https://example.com/article2

本报告全面分析了数字人技术的最新发展趋势。根据数据显示，2024年数字人市场规模已达到XX亿元，同比增长XX%...

---
```

## 故障排除

如果遇到问题，请检查：

1. 环境变量是否正确设置
2. API密钥是否有效
3. 网络连接是否正常
4. 日志输出中是否有错误信息

如有其他问题，请参考项目文档或联系开发团队。
