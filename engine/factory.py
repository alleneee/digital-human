"""
通用引擎工厂基类
实现工厂模式，支持统一的引擎创建和管理
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Optional, TypeVar, Generic, List, Union
from yacs.config import CfgNode as CN
import logging
from utils.registry_v2 import Registry

# 配置日志
logger = logging.getLogger(__name__)

# 类型定义
T = TypeVar('T')

class BaseFactory(Generic[T], ABC):
    """
    抽象工厂基类，用于创建和管理不同类型的引擎
    """
    def __init__(self, registry_name: str):
        """
        初始化工厂
        
        参数:
            registry_name: 注册表名称
        """
        self._registry = Registry[T](registry_name)
        
    @property
    def registry(self) -> Registry[T]:
        """获取注册表对象"""
        return self._registry
        
    def register_engine(self, name: Optional[str] = None):
        """
        注册引擎到工厂
        
        参数:
            name: 引擎名称，默认使用类的NAME属性
            
        返回:
            装饰器函数
        """
        return self._registry.register(name)
        
    def get_engine_class(self, name: str) -> Optional[Type[T]]:
        """
        获取引擎类
        
        参数:
            name: 引擎名称
            
        返回:
            引擎类，不存在时返回None
        """
        return self._registry.get(name)
        
    @abstractmethod
    def create(self, config: Union[CN, Dict[str, Any]], **kwargs) -> Optional[T]:
        """
        创建引擎实例
        
        参数:
            config: 引擎配置
            **kwargs: 额外参数
            
        返回:
            引擎实例，失败时返回None
        """
        pass
        
    def list_available_engines(self) -> List[str]:
        """
        列出所有可用的引擎名称
        
        返回:
            引擎名称列表
        """
        return self._registry.list_available()
