# -*- coding: utf-8 -*-
'''
FunASR 本地模型 ASR 引擎实现
'''

import asyncio
from typing import List, Optional, Union
from yacs.config import CfgNode as CN
from ..engineBase import BaseEngine
from ..builder import ASREngines
from utils import AudioMessage, TextMessage, AudioFormatType
import logging
import os
import tempfile

# 配置日志
logger = logging.getLogger(__name__)

@ASREngines.register()
class FunASRLocal(BaseEngine):
    """
    FunASR 本地模型 ASR 引擎实现
    """
    def checkKeys(self) -> List[str]:
        """
        检查必要的配置项
        """
        return ["NAME", "MODEL_PATH"]
    
    def setup(self):
        """
        初始化 FunASR 模型
        """
        try:
            from funasr import AutoModel
            
            # 检查模型路径是否存在
            model_path = self.cfg.MODEL_PATH
            if not os.path.exists(model_path):
                raise RuntimeError(f"[FunASRLocal] 模型路径不存在: {model_path}")
            
            # 保存支持的选项
            self.options = {
                "language": self.cfg.get("LANGUAGE", "auto"),
                "use_vad": self.cfg.get("USE_VAD", True),
                "vad_model": self.cfg.get("VAD_MODEL", "fsmn-vad"),
                "use_punc": self.cfg.get("USE_PUNC", True),
                "punc_model": self.cfg.get("PUNC_MODEL", "ct-punc"),
                "device": self.cfg.get("DEVICE", "cpu"),
                "batch_size_s": self.cfg.get("BATCH_SIZE_S", 60),
                "use_itn": self.cfg.get("USE_ITN", True),
                "merge_vad": self.cfg.get("MERGE_VAD", True),
                "merge_length_s": self.cfg.get("MERGE_LENGTH_S", 15),
            }
            
            # 初始化模型
            vad_kwargs = {"max_single_segment_time": self.cfg.get("MAX_SINGLE_SEGMENT_TIME", 30000)}
            
            logger.info(f"[FunASRLocal] 开始加载模型: {model_path}")
            
            # 加载模型
            if self.options["use_vad"]:
                self.model = AutoModel(
                    model=model_path,
                    vad_model=self.options["vad_model"],
                    vad_kwargs=vad_kwargs,
                    device=self.options["device"],
                )
                logger.info(f"[FunASRLocal] 已加载模型并启用VAD: {model_path}")
            else:
                self.model = AutoModel(
                    model=model_path,
                    device=self.options["device"],
                )
                logger.info(f"[FunASRLocal] 已加载模型(无VAD): {model_path}")
                
            # 初始化缓存
            self.cache = {}
            
            logger.info(f"[FunASRLocal] 模型加载成功: {model_path}")
            
        except ImportError as e:
            logger.error(f"[FunASRLocal] 请先安装FunASR: pip install funasr")
            raise RuntimeError(f"[FunASRLocal] 请先安装FunASR: {str(e)}")
        except Exception as e:
            logger.error(f"[FunASRLocal] 初始化失败: {str(e)}")
            raise RuntimeError(f"[FunASRLocal] 初始化失败: {str(e)}")
    
    async def run(self, input: Union[AudioMessage, List[AudioMessage]], **kwargs) -> Optional[TextMessage]:
        """
        运行 FunASR 识别
        
        参数:
            input: AudioMessage 或 List[AudioMessage]
            **kwargs: 额外参数，可包括:
                language: 语言代码 (auto, zh, en, yue, ja, ko等)
                use_itn: 是否使用标点和反向文本规范化
                batch_size_s: 动态批处理的音频总时长(秒)
                merge_vad: 是否合并VAD分割的短音频片段
                
        返回:
            TextMessage: 识别结果
        """
        if isinstance(input, List):
            if len(input) == 0:
                logger.warning(f"[FunASRLocal] 输入列表为空")
                return None
            input = input[0]  # 只处理第一条音频
        
        if not isinstance(input, AudioMessage):
            logger.warning(f"[FunASRLocal] 输入不是 AudioMessage 类型")
            return None
        
        if len(input.data) == 0:
            logger.warning(f"[FunASRLocal] 音频数据为空")
            return None
        
        try:
            # 构建请求选项
            options = {}
            # 设置语言
            options["language"] = kwargs.get("language", self.options["language"])
            # 设置是否使用标点和反向文本规范化
            options["use_itn"] = kwargs.get("use_itn", self.options["use_itn"])
            # 设置批处理大小
            options["batch_size_s"] = kwargs.get("batch_size_s", self.options["batch_size_s"])
            # 设置是否合并VAD分割的短音频片段
            options["merge_vad"] = kwargs.get("merge_vad", self.options["merge_vad"])
            # 设置合并长度
            options["merge_length_s"] = kwargs.get("merge_length_s", self.options["merge_length_s"])
            
            # 准备音频数据
            audio_data = input.data
            
            # 将音频数据写入临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_suffix(input.format)) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                logger.info(f"[FunASRLocal] 开始识别: {options}")
                
                # 调用FunASR模型进行识别
                result = await self._run_recognition(temp_file_path, options)
                
                # 删除临时文件
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                
                # 处理结果
                if result and result[0] and "text" in result[0]:
                    text = result[0]["text"]
                    logger.info(f"[FunASRLocal] 识别成功: {text[:50]}...")
                    
                    # 使用工具函数处理结果
                    from funasr.utils.postprocess_utils import rich_transcription_postprocess
                    processed_text = rich_transcription_postprocess(text)
                    
                    return TextMessage(data=processed_text)
                else:
                    logger.warning(f"[FunASRLocal] 识别结果为空")
                    return None
            finally:
                # 确保临时文件被删除
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"[FunASRLocal] 识别失败: {str(e)}")
            return None
    
    async def _run_recognition(self, audio_path, options):
        """
        在事件循环中运行FunASR识别
        """
        # 创建一个异步任务在线程池中运行
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._recognize_audio,
            audio_path,
            options
        )
    
    def _recognize_audio(self, audio_path, options):
        """
        在线程池中运行的同步识别函数
        """
        try:
            # 执行识别
            result = self.model.generate(
                input=audio_path,
                cache=self.cache,
                language=options["language"],
                use_itn=options["use_itn"],
                batch_size_s=options["batch_size_s"],
                merge_vad=options["merge_vad"],
                merge_length_s=options["merge_length_s"],
            )
            return result
        except Exception as e:
            logger.error(f"[FunASRLocal] 识别执行错误: {str(e)}")
            return None
    
    def _get_suffix(self, format):
        """
        根据音频格式获取文件后缀
        """
        if format == AudioFormatType.WAV:
            return ".wav"
        elif format == AudioFormatType.MP3:
            return ".mp3"
        elif format == AudioFormatType.OGG:
            return ".ogg"
        elif format == AudioFormatType.WEBM:
            return ".webm"
        else:
            return ".wav"  # 默认为WAV格式
