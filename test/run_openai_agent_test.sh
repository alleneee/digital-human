#!/bin/bash

# 设置环境变量
# 注意：请将这些值替换为您自己的API密钥
export OPENAI_API_KEY="your_openai_api_key"
export GOOGLE_API_KEY="your_google_api_key"
export GOOGLE_SEARCH_ENGINE_ID="your_search_engine_id"
export FIRECRAWL_API_KEY="your_firecrawl_api_key"

# 运行测试脚本
echo "运行OpenAI Agent工具调用测试..."
python test/test_openai_agent_tools.py --query "请帮我查询数字人技术的最新进展" --model "gpt-4o"

# 清理环境变量（可选）
# unset OPENAI_API_KEY
# unset GOOGLE_API_KEY
# unset GOOGLE_SEARCH_ENGINE_ID
# unset FIRECRAWL_API_KEY 