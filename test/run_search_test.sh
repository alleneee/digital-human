#!/bin/bash

# 设置环境变量
# 注意：请将这些值替换为您自己的API密钥
export GOOGLE_API_KEY="your_google_api_key"
export GOOGLE_SEARCH_ENGINE_ID="your_search_engine_id"
export FIRECRAWL_API_KEY="your_firecrawl_api_key"

# 运行测试脚本
echo "运行增强型网络搜索测试..."
python test/test_search_tool_direct.py --query "数字人技术的最新进展" --google-results 5 --detailed-results 2

# 清理环境变量（可选）
# unset GOOGLE_API_KEY
# unset GOOGLE_SEARCH_ENGINE_ID
# unset FIRECRAWL_API_KEY 