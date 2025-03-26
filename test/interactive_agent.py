#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
交互式Agent测试工具
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
import json
from datetime import datetime
import argparse

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import load_config
from engine.agent.agent_factory import AgentFactory
from utils.protocol import TextMessage

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InteractiveAgent:
    """交互式Agent测试类"""
    
    def __init__(self, config_path=None):
        """初始化交互式Agent"""
        self.config_path = config_path or "configs/agent.yaml"
        self.agent = None
        self.context = {}
        self.session_id = f"interactive_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.history = []
    
    async def initialize(self):
        """初始化Agent"""
        try:
            # 加载配置
            logger.info(f"加载配置: {self.config_path}")
            config = load_config(self.config_path)
            
            if not config or not config.AGENT.ENABLED:
                logger.error("Agent功能未启用，请检查配置")
                return False
            
            # 创建Agent实例
            logger.info("创建Agent实例...")
            self.agent = AgentFactory.create(config.AGENT)
            
            if not self.agent:
                logger.error("创建Agent实例失败")
                return False
            
            # 初始化上下文
            self.context = {
                "session_id": self.session_id,
                "interactive_mode": True
            }
            
            logger.info("Agent初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"初始化失败: {str(e)}")
            return False
    
    async def process_query(self, query):
        """处理用户查询"""
        if not self.agent:
            logger.error("Agent未初始化")
            return "错误: Agent未初始化"
        
        try:
            # 记录查询
            self.history.append({"role": "user", "content": query})
            
            # 处理查询
            logger.info(f"处理查询: {query}")
            start_time = datetime.now()
            response = await self.agent.process(query, conversation_context=self.context)
            end_time = datetime.now()
            
            # 计算处理时间
            processing_time = (end_time - start_time).total_seconds()
            logger.info(f"处理完成，耗时: {processing_time:.2f} 秒")
            
            # 更新上下文
            self.context.update({
                "last_query": query,
                "last_response": response.text
            })
            
            # 记录回复
            self.history.append({"role": "assistant", "content": response.text})
            
            return response.text
            
        except Exception as e:
            error_msg = f"处理查询失败: {str(e)}"
            logger.error(error_msg)
            return f"错误: {error_msg}"
    
    def save_history(self, filename=None):
        """保存对话历史"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"interactive_session_{timestamp}.json"
        
        # 创建保存目录
        save_dir = Path(__file__).parent.parent / "test_outputs" / "interactive"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存文件路径
        save_path = save_dir / filename
        
        # 保存历史记录
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "history": self.history
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"对话历史已保存到: {save_path}")
        return str(save_path)

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="交互式Agent测试工具")
    parser.add_argument("--config", type=str, default="configs/agent.yaml", help="配置文件路径")
    args = parser.parse_args()
    
    # 创建交互式Agent
    interactive = InteractiveAgent(args.config)
    
    # 初始化Agent
    if not await interactive.initialize():
        logger.error("初始化失败，退出程序")
        return
    
    print("\n===== 交互式Agent测试工具 =====")
    print("输入 'exit' 或 'quit' 退出程序")
    print("输入 'save' 保存对话历史")
    print("输入 'clear' 清屏")
    print("输入 'help' 显示帮助信息")
    print("================================\n")
    
    # 主循环
    while True:
        try:
            # 获取用户输入
            user_input = input("\n> ")
            
            # 处理特殊命令
            if user_input.lower() in ["exit", "quit"]:
                # 保存历史并退出
                interactive.save_history()
                print("再见！")
                break
                
            elif user_input.lower() == "save":
                # 保存历史
                save_path = interactive.save_history()
                print(f"对话历史已保存到: {save_path}")
                continue
                
            elif user_input.lower() == "clear":
                # 清屏
                os.system("cls" if os.name == "nt" else "clear")
                continue
                
            elif user_input.lower() == "help":
                # 显示帮助信息
                print("\n===== 帮助信息 =====")
                print("exit/quit - 退出程序")
                print("save - 保存对话历史")
                print("clear - 清屏")
                print("help - 显示帮助信息")
                print("====================\n")
                continue
                
            elif not user_input.strip():
                # 空输入
                continue
            
            # 处理正常查询
            response = await interactive.process_query(user_input)
            print(f"\n{response}\n")
            
        except KeyboardInterrupt:
            # 处理Ctrl+C
            print("\n程序被中断")
            interactive.save_history()
            break
            
        except Exception as e:
            print(f"\n错误: {str(e)}\n")
    
    print("程序已退出")

if __name__ == "__main__":
    asyncio.run(main()) 