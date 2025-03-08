# -*- coding: utf-8 -*-
'''
单例模式实现
'''

class Singleton(type):
    """
    单例元类，确保类只有一个实例
    
    使用方法:
    ```
    class MyClass(metaclass=Singleton):
        pass
    ```
    """
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
