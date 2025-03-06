# -*- coding: utf-8 -*-
'''
引擎基类定义
'''

from typing import List, Optional, Union
from yacs.config import CfgNode as CN
from abc import ABCMeta, abstractmethod
from utils import BaseMessage
import logging

# 配置日志
logger = logging.getLogger(__name__)

class BaseEngine(metaclass=ABCMeta):
    """
    所有引擎的基类
    """
    def __init__(self, config: CN):
        self.cfg = config
        # 检查必要的配置项
        for key in self.checkKeys():
            if key not in self.cfg:
                raise KeyError(f"[{self.__class__.__name__}] 配置中缺少必要项: {key}")
        self.setup()
    
    def __del__(self):
        """
        析构函数，释放资源
        """
        self.release()
    
    @property
    def name(self) -> str:
        """
        获取引擎名称
        """
        return self.cfg.NAME
    
    def parameters(self) -> List[str]:
        """
        获取引擎参数列表
        """
        return self.cfg.PARAMETERS if "PARAMETERS" in self.cfg else []
    
    def setup(self):
        """
        引擎初始化，子类可重写
        """
        pass

    def release(self):
        """
        释放资源，子类可重写
        """
        pass

    def checkKeys(self) -> List[str]:
        """
        检查必要的配置项，子类应重写
        """
        return []

    @abstractmethod
    async def run(self, input: Union[BaseMessage, List[BaseMessage]], **kwargs) -> Optional[BaseMessage]:
        """
        运行引擎，子类必须实现
        
        参数:
            input: 输入消息或消息列表
            **kwargs: 额外参数
            
        返回:
            BaseMessage: 处理结果
        """
        pass
