# -*- coding: utf-8 -*-
'''
数字人框架主程序入口
'''

import os
import sys
import logging
import argparse
import asyncio
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from yacs.config import CfgNode as CN

# 导入自定义模块
from api.routes import router as api_router, APIService
from utils.config import load_config, merge_configs
from pipelines.conversation import ConversationPipeline
from pipelines.speech import SpeechProcessor
from integrations.echomimic import EchoMimicIntegration
from utils.protocol import AudioMessage, TextMessage, AudioFormatType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("digital_human.log")
    ]
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title="数字人框架", description="ASR+LLM+TTS综合框架")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加API路由
app.include_router(api_router)

# 访问根路径时重定向到文档
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

# 全局实例
api_service = None
pipeline = None
speech_processor = None
echomimic_integration = None
config = None

# 应用启动时执行的初始化操作
@app.on_event("startup")
async def startup_event():
    global api_service, pipeline, speech_processor, echomimic_integration, config
    
    try:
        # 解析命令行参数
        args = parse_args()
        
        # 加载配置
        logger.info(f"加载配置文件: {args.config}")
        config = load_config(args.config)
        
        # 初始化语音处理器
        logger.info("初始化语音处理器...")
        speech_processor = SpeechProcessor(config)
        
        # 初始化对话管道
        logger.info("初始化对话管道...")
        pipeline = ConversationPipeline(config)
        await pipeline.setup()
        
        # 初始化EchoMimicV2集成
        logger.info("初始化EchoMimicV2集成...")
        echomimic_config = config.get("echomimic", {})
        if not echomimic_config and "echomimic" in config.get("engines", {}):
            echomimic_config = config.engines.echomimic
        
        if echomimic_config:
            try:
                echomimic_integration = EchoMimicIntegration(echomimic_config)
                logger.info("EchoMimicV2集成初始化成功")
            except Exception as e:
                logger.error(f"EchoMimicV2集成初始化失败: {str(e)}")
                echomimic_integration = None
        else:
            logger.warning("未找到EchoMimicV2配置，集成将不可用")
            echomimic_integration = None
        
        # 初始化API服务
        logger.info("初始化API服务...")
        api_service = APIService()
        api_service.set_pipeline(pipeline)
        api_service.set_speech_processor(speech_processor)
        if echomimic_integration:
            api_service.set_echomimic_integration(echomimic_integration)
        
        logger.info("应用启动完成!")
        
    except Exception as e:
        logger.error(f"初始化出错: {str(e)}")
        import traceback
        traceback.print_exc()

# 应用关闭时执行的清理操作
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("应用正在关闭...")
    
    # 清理资源
    global pipeline
    if pipeline:
        await pipeline.cleanup()
    
    logger.info("应用已关闭!")

# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description="数字人框架")
    parser.add_argument("--config", type=str, default=os.environ.get("DH_CONFIG", "configs/default.yaml"),
                      help="配置文件路径")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听主机")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    return parser.parse_args()

# 主函数
def main():
    args = parse_args()
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 启动uvicorn服务器
    uvicorn.run(
        "app:app",
        host=args.host,
        port=args.port,
        reload=True,  # 开发模式下自动重载
        log_level="info"
    )

if __name__ == "__main__":
    main()
