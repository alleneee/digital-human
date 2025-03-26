"""
数字人Agent模块

这个模块使用OpenAI Agents API实现更强大的代理功能
"""

from .agent_factory import AgentFactory
from .openai_agent import OpenAIAgent

__all__ = ["AgentFactory", "OpenAIAgent"] 