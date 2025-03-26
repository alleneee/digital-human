"""
自定义Agent工具
"""

import logging
import os
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

# 移除所有装饰器
async def enhanced_web_search(
    query: str,
    num_google_results: int = 8,
    num_detailed_results: int = 3,
    language: str = "zh-CN"
) -> str:
    """
    增强型网络搜索：先用Google搜索获取链接，再用Firecrawl爬取详细内容
    
    参数:
        query: 搜索查询关键词
        num_google_results: Google搜索返回的结果数量，默认为8
        num_detailed_results: 需要获取详细内容的结果数量，默认为3
        language: 搜索结果语言，默认为中文(zh-CN)
    
    返回:
        整合后的搜索结果，包含概述和详细内容
    """
    logger.info(f"执行增强型网络搜索: 查询='{query}', Google结果数={num_google_results}, 详细内容数={num_detailed_results}")
    
    try:
        # 步骤1: 使用Google搜索获取相关链接和预览
        google_results = await _google_search_raw(query, num_google_results, language)
        
        if not google_results:
            return f"Google搜索'{query}'没有找到结果或API配置缺失，无法继续获取详细内容。请确保设置了GOOGLE_API_KEY和GOOGLE_SEARCH_ENGINE_ID环境变量。"
            
        # 步骤2: 筛选最相关的链接
        selected_urls = _select_best_urls(google_results, num_detailed_results)
        
        if not selected_urls:
            return f"无法从Google搜索结果中筛选出有效链接，无法继续获取详细内容。"
            
        # 步骤3: 使用Firecrawl获取详细内容
        detailed_contents = []
        for url in selected_urls:
            content = await _firecrawl_specific_url(url)
            if content and isinstance(content, dict):  # 检查内容是否为字典类型
                detailed_contents.append(content)
                
        # 步骤4: 整合搜索结果
        return _format_enhanced_results(query, google_results, detailed_contents)
            
    except Exception as e:
        error_msg = f"增强型网络搜索失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

async def _google_search_raw(query: str, num_results: int = 8, language: str = "zh-CN") -> List[Dict[str, Any]]:
    """获取Google搜索原始结果，返回结果列表而非格式化字符串"""
    try:
        # 获取API密钥和搜索引擎ID
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        search_engine_id = os.environ.get("GOOGLE_SEARCH_ENGINE_ID", "")
        
        if not api_key or not search_engine_id:
            logger.error("Google搜索失败: 缺少API密钥或搜索引擎ID")
            return []
        
        # 构建API请求URL
        url = "https://www.googleapis.com/customsearch/v1"
        
        # 设置请求参数
        params = {
            "key": api_key,
            "cx": search_engine_id,
            "q": query,
            "num": min(num_results, 10),  # Google API限制最多10个结果
            "hl": language,
            "safe": "active"  # 安全搜索
        }
        
        # 发送API请求
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()  # 确保请求成功
            
            search_data = response.json()
            
        # 返回原始搜索结果项
        if "items" not in search_data:
            return []
            
        return search_data["items"]
        
    except Exception as e:
        logger.error(f"Google搜索原始数据获取失败: {str(e)}")
        return []

def _select_best_urls(google_results: List[Dict[str, Any]], max_urls: int = 3) -> List[str]:
    """从Google搜索结果中选择最相关的URL"""
    # 过滤结果，排除社交媒体、广告等
    filtered_results = []
    excluded_domains = ['youtube.com', 'facebook.com', 'twitter.com', 'instagram.com', 'tiktok.com']
    
    for result in google_results:
        url = result.get("link", "")
        # 简单的域名检查，实际应用中可以使用更复杂的过滤规则
        if not any(excluded in url for excluded in excluded_domains):
            filtered_results.append(result)
    
    # 按相关性排序（这里我们假设Google已经按相关性排序）
    # 取前max_urls个结果
    selected = filtered_results[:max_urls]
    return [item.get("link") for item in selected if item.get("link")]

async def _firecrawl_specific_url(url: str) -> Optional[Dict[str, Any]]:
    """使用Firecrawl获取特定URL的内容"""
    try:
        # 获取API密钥
        api_key = os.environ.get("FIRECRAWL_API_KEY", "")
        
        if not api_key:
            logger.error("Firecrawl API密钥未设置")
            return None
        
        # 构建API请求URL和头信息
        api_url = "https://api.firecrawl.dev/v1/scrape"  # 更新为正确的API端点
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": url,
            "formats": ["markdown"],  # 请求markdown格式的内容
            "onlyMainContent": True   # 只获取主要内容
        }
        
        # 发送API请求
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Firecrawl API返回数据: {json.dumps(data, ensure_ascii=False)[:500]}...")
            
            # 返回结果
            if data and data.get("success") and data.get("data") and "markdown" in data.get("data", {}):
                title = url.split("/")[-1].replace("-", " ").title()
                if "title" in data:
                    title = data.get("title", title)
                
                return {
                    "url": url,
                    "title": title,
                    "content": data.get("data", {}).get("markdown", "")
                }
            else:
                logger.error(f"Firecrawl API返回数据格式不符合预期: {json.dumps(data, ensure_ascii=False)[:200]}...")
            return None
            
    except Exception as e:
        logger.error(f"获取URL内容失败 {url}: {str(e)}")
        return None

def _format_enhanced_results(query: str, google_results: List[Dict[str, Any]], detailed_contents: List[Dict[str, Any]]) -> str:
    """格式化增强型搜索结果"""
    
    # 首先添加Google搜索概述
    result = f"### 搜索查询: '{query}'\n\n"
    
    result += "## 搜索结果概述\n\n"
    for i, item in enumerate(google_results[:5], 1):  # 只显示前5个概述
        title = item.get("title", "无标题")
        link = item.get("link", "")
        snippet = item.get("snippet", "无描述").replace("\n", " ")
        
        result += f"{i}. **{title}**\n"
        result += f"   链接: {link}\n"
        result += f"   摘要: {snippet}\n\n"
    
    # 添加详细内容
    result += "## 详细内容\n\n"
    
    for i, content in enumerate(detailed_contents, 1):
        title = content.get("title", "无标题")
        url = content.get("url", "")
        text = content.get("content", "")
        
        # 截取内容摘要（最多1000字符）
        if len(text) > 1000:
            text = text[:1000] + "..."
            
        result += f"### {i}. {title}\n"
        result += f"来源: {url}\n\n"
        result += f"{text}\n\n"
        result += "---\n\n"
    
    # 如果没有详细内容
    if not detailed_contents:
        result += "_未能获取详细内容，请尝试调整搜索关键词或检查Firecrawl API配置。_\n\n"
    
    return result

async def weather_tool(location: str, unit: str = "celsius") -> str:
    """
    获取指定位置的天气信息
    
    参数:
        location: 城市名称或位置描述，如"北京"、"上海"
        unit: 温度单位，"celsius"（摄氏度）或"fahrenheit"（华氏度），默认为"celsius"
    
    返回:
        天气信息的字符串描述
    """
    logger.info(f"查询天气: 位置={location}, 单位={unit}")
    
    try:
        # 这里使用示例API，实际应用中应使用真实的天气API
        api_key = os.environ.get("WEATHER_API_KEY", "demo_key")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.example.com/weather",
                params={
                    "location": location,
                    "unit": unit,
                    "api_key": api_key
                },
                timeout=10.0
            )
            
        # 在示例中，我们模拟API响应
        # 实际应用中应解析实际API返回的数据
        weather_data = {
            "location": location,
            "temperature": 25 if unit == "celsius" else 77,
            "condition": "晴天",
            "humidity": 60,
            "wind": "东南风3级",
            "updated_at": datetime.now().isoformat()
        }
        
        result = (
            f"{location}天气: {weather_data['condition']}, "
            f"温度{weather_data['temperature']}°{'C' if unit == 'celsius' else 'F'}, "
            f"湿度{weather_data['humidity']}%, {weather_data['wind']}"
        )
        
        logger.info(f"天气查询结果: {result}")
        return result
        
    except Exception as e:
        error_msg = f"获取天气信息失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

async def knowledge_base_search(query: str, limit: int = 5) -> str:
    """
    搜索知识库获取相关信息
    
    参数:
        query: 搜索查询
        limit: 返回结果数量上限，默认为5
    
    返回:
        知识库搜索结果
    """
    logger.info(f"搜索知识库: 查询={query}, 限制={limit}")
    
    try:
        # 模拟知识库搜索结果
        # 实际应用中应连接到向量数据库或其他知识库系统
        search_results = [
            {
                "title": "示例文档1",
                "content": "这是与查询相关的示例内容1...",
                "relevance": 0.92
            },
            {
                "title": "示例文档2",
                "content": "这是与查询相关的示例内容2...",
                "relevance": 0.85
            },
            {
                "title": "示例文档3",
                "content": "这是与查询相关的示例内容3...",
                "relevance": 0.78
            }
        ]
        
        # 格式化返回结果
        results_text = "知识库搜索结果:\n\n"
        for i, result in enumerate(search_results[:limit], 1):
            results_text += f"{i}. {result['title']} (相关度: {result['relevance']})\n"
            results_text += f"   {result['content']}\n\n"
        
        logger.info(f"知识库搜索完成，找到{len(search_results[:limit])}条结果")
        return results_text
        
    except Exception as e:
        error_msg = f"知识库搜索失败: {str(e)}"
        logger.error(error_msg)
        return error_msg 