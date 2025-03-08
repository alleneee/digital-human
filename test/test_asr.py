import asyncio
import logging
import os
from pathlib import Path
from engine.asr.funasrASR import FunASRLocal
from yacs.config import CfgNode as CN
from utils import AudioMessage, AudioFormatType

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_funasr():
    """测试FunASR本地语音识别模型"""
    try:
        # 获取音频文件路径
        audio_file = Path("test_outputs/advanced_audio_简短语音.mp3")
        if not audio_file.exists():
            logger.error(f"音频文件不存在: {audio_file}")
            return None
        
        logger.info(f"测试音频文件: {audio_file}")
        
        # 读取音频文件
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        
        # 直接使用FunASRLocal测试
        logger.info("直接初始化FunASR模型...")
        model_dir = "/Users/niko/.cache/modelscope/hub/SenseVoiceSmall"
        if not os.path.exists(model_dir):
            logger.error(f"模型目录不存在: {model_dir}")
            return None
        
        # 创建FunASR配置
        cfg = CN()
        cfg.NAME = "FunASRLocal"
        cfg.MODEL_PATH = model_dir
        cfg.LANGUAGE = "auto"
        cfg.USE_VAD = True
        cfg.VAD_MODEL = "fsmn-vad"
        cfg.USE_PUNC = True
        cfg.DEVICE = "cpu"
        cfg.BATCH_SIZE_S = 60
        cfg.USE_ITN = True
        cfg.MERGE_VAD = True
        cfg.MERGE_LENGTH_S = 15
        cfg.MAX_SINGLE_SEGMENT_TIME = 30000
        
        # 初始化FunASRLocal对象
        funasr = FunASRLocal(cfg)
        
        logger.info("开始识别音频...")
        
        # 创建AudioMessage对象
        # 假设音频格式是mp3，采样率是44100Hz，样本大小是16位(2字节)
        audio_message = AudioMessage(
            data=audio_data, 
            format=AudioFormatType.MP3,
            sampleRate=44100,  # 常见MP3采样率
            sampleWidth=2      # 16位音频
        )
        
        # 使用run方法进行识别
        result = await funasr.run(audio_message)
        logger.info(f"FunASR识别结果: {result}")
        
        return result
    
    except Exception as e:
        logger.error(f"测试FunASR时发生错误: {e}")
        raise

if __name__ == "__main__":
    # 运行测试
    result = asyncio.run(test_funasr())
    print(f"\n最终识别结果: {result}")
