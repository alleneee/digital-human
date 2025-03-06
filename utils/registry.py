# -*- coding: utf-8 -*-
'''
注册表实现
'''

def _register_generic(module_dict, module_name, module):
    """
    注册模块到字典中
    """
    assert module_name not in module_dict
    module_dict[module_name] = module

class Registry(dict):
    """
    注册表类，用于管理不同的引擎实现
    """
    def __init__(self, *args, **kwargs):
        super(Registry, self).__init__(*args, **kwargs)

    def register(self, module_name=None, module=None):
        """
        注册模块
        
        可以作为函数调用:
            registry.register("module_name", module)
            
        也可以作为装饰器:
            @registry.register("module_name")
            def module_func():
                pass
        """
        # 如果module_name为None，则使用module的NAME属性
        if module_name is None and module is not None and hasattr(module, "NAME"):
            module_name = module.NAME
            
        # 作为函数调用
        if module is not None:
            _register_generic(self, module_name, module)
            return

        # 作为装饰器
        def register_fn(fn):
            # 如果module_name仍为None，则使用函数名
            _register_generic(self, module_name or fn.__name__, fn)
            return fn

        return register_fn

    def list(self):
        """
        列出所有已注册的模块名
        """
        return list(self.keys())
        
    def get(self, name):
        """
        获取已注册的模块
        """
        return super(Registry, self).get(name, None)
