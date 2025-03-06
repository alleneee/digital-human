"""
增强的注册表系统
实现更灵活的模块注册和工厂模式
"""

import inspect
from typing import Dict, Any, Type, Callable, Optional, TypeVar, Generic, List
import logging

# 日志配置
logger = logging.getLogger(__name__)

# 类型定义
T = TypeVar('T')
ConfigType = TypeVar('ConfigType')

class Registry(Generic[T]):
    """
    增强的注册表类，支持类型检查和依赖注入
    """
    def __init__(self, name: str):
        """
        初始化注册表
        
        参数:
            name: 注册表名称，用于标识不同类型的组件
        """
        self._name = name
        self._module_dict: Dict[str, Type[T]] = {}
        logger.debug(f"创建注册表: {name}")
    
    def __len__(self) -> int:
        return len(self._module_dict)
    
    def __contains__(self, key: str) -> bool:
        return key in self._module_dict
    
    def __repr__(self) -> str:
        return f"Registry(name={self._name}, items={list(self._module_dict.keys())})"
        
    def keys(self) -> List[str]:
        """获取所有已注册模块名称"""
        return list(self._module_dict.keys())
        
    def values(self) -> List[Type[T]]:
        """获取所有已注册模块类"""
        return list(self._module_dict.values())
        
    def items(self):
        """获取所有已注册的(名称, 模块)对"""
        return self._module_dict.items()
    
    def register(self, name: Optional[str] = None) -> Callable:
        """
        注册模块到注册表
        
        用法:
            1. 作为装饰器，不指定名称:
               @registry.register()
               class MyModule: ...
            
            2. 作为装饰器，指定名称:
               @registry.register('my_module')
               class MyModule: ...
               
            3. 作为方法调用:
               registry.register('my_module')(MyModule)
        """
        def _register(cls: Type[T]) -> Type[T]:
            # 确定注册名称
            module_name = name
            if module_name is None:
                # 尝试从类属性获取名称
                if hasattr(cls, "NAME") and cls.NAME is not None:
                    module_name = cls.NAME
                else:
                    # 使用类名作为默认名称
                    module_name = cls.__name__
            
            # 检查名称是否已存在
            if module_name in self._module_dict:
                logger.warning(f"覆盖已存在的模块: {module_name}")
                
            # 注册模块
            logger.debug(f"注册模块 {module_name} 到 {self._name}")
            self._module_dict[module_name] = cls
            return cls
            
        return _register
    
    def get(self, name: str) -> Optional[Type[T]]:
        """
        获取已注册的模块
        
        参数:
            name: 模块名称
            
        返回:
            已注册的模块类，不存在时返回None
        """
        return self._module_dict.get(name)
        
    def build(self, name: str, *args, **kwargs) -> Optional[T]:
        """
        创建指定模块的实例
        
        参数:
            name: 模块名称
            *args, **kwargs: 传递给模块构造函数的参数
            
        返回:
            模块实例，失败时返回None
        """
        cls = self.get(name)
        if cls is None:
            logger.error(f"模块不存在: {name}")
            return None
            
        try:
            instance = cls(*args, **kwargs)
            return instance
        except Exception as e:
            logger.error(f"创建模块 {name} 实例失败: {e}")
            return None
            
    def list_available(self) -> List[str]:
        """
        列出所有可用的模块名称
        """
        return list(self._module_dict.keys())
