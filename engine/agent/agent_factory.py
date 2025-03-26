"""
Agent工厂类，用于创建不同类型的Agent实例
"""

import logging
from typing import Dict, Any, Optional
from yacs.config import CfgNode as CN

from .openai_agent import OpenAIAgent

logger = logging.getLogger(__name__)

class AgentFactory:
    """
    Agent工厂类，负责创建不同类型的Agent实例
    """
    
    @staticmethod
    def create(config: CN) -> Optional[Any]:
        """
        根据配置创建Agent实例
        
        参数:
            config: Agent配置
            
        返回:
            创建的Agent实例，如果创建失败则返回None
        """
        if not config or not config.ENABLED:
            logger.warning("Agent功能未启用")
            return None
        
        agent_type = config.NAME.lower()
        
        try:
            if agent_type == "openai":
                logger.info("创建OpenAI Agent实例")
                return OpenAIAgent(config)
            else:
                logger.error(f"不支持的Agent类型: {agent_type}")
                return None
        except Exception as e:
            logger.error(f"创建Agent实例失败: {str(e)}")
            return None 