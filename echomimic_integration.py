# echomimic_integration.py
import os
import logging
import numpy as np
import torch
from pathlib import Path
from PIL import Image
from diffusers import AutoencoderKL, DDIMScheduler
from datetime import datetime
import asyncio
import tempfile
import shutil
import json

# EchoMimic相关导入
from echomimic_v2.src.models.unet_2d_condition import UNet2DConditionModel
from echomimic_v2.src.models.unet_3d_emo import EMOUNet3DConditionModel
from echomimic_v2.src.models.whisper.audio2feature import load_audio_model
from echomimic_v2.src.pipelines.pipeline_echomimicv2 import EchoMimicV2Pipeline
from echomimic_v2.src.utils.util import save_videos_grid
from echomimic_v2.src.models.pose_encoder import PoseEncoder
from echomimic_v2.src.utils.dwpose_util import draw_pose_select_v2

# 配置日志
logger = logging.getLogger(__name__)

class EchoMimicGenerator:
    """EchoMimic视频生成服务"""
    
    def __init__(self, 
                 base_path="./echomimic_v2",
                 model_precision="fp16",
                 use_gpu=True):
        """
        初始化EchoMimic生成器
        
        参数:
            base_path: EchoMimic V2项目的基础路径
            model_precision: 模型精度，"fp16"或"fp32"
            use_gpu: 是否使用GPU
        """
        self.base_path = Path(base_path)
        self.initialized = False
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        
        # 模型精度
        self.weight_dtype = torch.float16 if model_precision == "fp16" else torch.float32
        
        # 预设参数
        self.default_width = 512
        self.default_height = 512
        self.default_fps = 24
        self.default_steps = 30
        self.default_cfg = 2.5
        self.default_sample_rate = 16000
        self.default_context_frames = 16
        self.default_context_overlap = 4
        
        # 模型路径
        self.pretrained_weights_path = self.base_path / "pretrained_weights"
        self.default_pose_dir = self.base_path / "assets/halfbody_demo/pose/01"
        
        # 缓存目录
        self.cache_dir = Path("./cache/echomimic")
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
        # 输出目录
        self.output_dir = Path("./frontend/public/generated")
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # 尝试初始化模型
        try:
            self._initialize_models()
            self.initialized = True
            logger.info("EchoMimic模型初始化成功")
        except Exception as e:
            logger.error(f"EchoMimic模型初始化失败: {e}")
            
    def _initialize_models(self):
        """初始化EchoMimic所需的所有模型"""
        logger.info(f"开始初始化EchoMimic模型，设备: {self.device}, 精度: {self.weight_dtype}")
        
        # 初始化VAE
        self.vae = AutoencoderKL.from_pretrained(
            self.pretrained_weights_path / "sd-vae-ft-mse"
        ).to(self.device, dtype=self.weight_dtype)
        
        # 初始化参考网络
        self.reference_unet = UNet2DConditionModel.from_pretrained(
            self.pretrained_weights_path / "sd-image-variations-diffusers",
            subfolder="unet"
        ).to(dtype=self.weight_dtype, device=self.device)
        
        self.reference_unet.load_state_dict(
            torch.load(self.pretrained_weights_path / "reference_unet.pth", weights_only=True)
        )
        
        # 初始化去噪网络
        motion_module_path = self.pretrained_weights_path / "motion_module.pth"
        if not motion_module_path.exists():
            raise FileNotFoundError(f"未找到动作模块: {motion_module_path}")
            
        # 构建UNet参数
        unet_additional_kwargs = {
            "use_inflated_groupnorm": True,
            "unet_use_cross_frame_attention": False,
            "unet_use_temporal_attention": False,
            "use_motion_module": True,
            "cross_attention_dim": 384,
            "motion_module_resolutions": [1, 2, 4, 8],
            "motion_module_mid_block": True,
            "motion_module_decoder_only": False,
            "motion_module_type": "Vanilla",
            "motion_module_kwargs": {
                "num_attention_heads": 8,
                "num_transformer_block": 1,
                "attention_block_types": ['Temporal_Self', 'Temporal_Self'],
                "temporal_position_encoding": True,
                "temporal_position_encoding_max_len": 32,
                "temporal_attention_dim_div": 1,
            }
        }
        
        self.denoising_unet = EMOUNet3DConditionModel.from_pretrained_2d(
            self.pretrained_weights_path / "sd-image-variations-diffusers",
            motion_module_path,
            subfolder="unet",
            unet_additional_kwargs=unet_additional_kwargs
        ).to(dtype=self.weight_dtype, device=self.device)
        
        self.denoising_unet.load_state_dict(
            torch.load(self.pretrained_weights_path / "denoising_unet.pth", weights_only=True),
            strict=False
        )
        
        # 初始化姿势编码器
        self.pose_net = PoseEncoder(
            320, conditioning_channels=3, block_out_channels=(16, 32, 96, 256)
        ).to(dtype=self.weight_dtype, device=self.device)
        
        self.pose_net.load_state_dict(
            torch.load(self.pretrained_weights_path / "pose_encoder.pth", weights_only=True)
        )
        
        # 初始化音频处理器
        self.audio_processor = load_audio_model(
            model_path=self.pretrained_weights_path / "audio_processor/tiny.pt",
            device=self.device
        )
        
        # 初始化调度器
        sched_kwargs = {
            "beta_start": 0.00085,
            "beta_end": 0.012,
            "beta_schedule": "linear",
            "clip_sample": False,
            "steps_offset": 1,
            "prediction_type": "v_prediction",
            "rescale_betas_zero_snr": True,
            "timestep_spacing": "trailing"
        }
        self.scheduler = DDIMScheduler(**sched_kwargs)
        
        # 创建Pipeline
        self.pipe = EchoMimicV2Pipeline(
            vae=self.vae,
            reference_unet=self.reference_unet,
            denoising_unet=self.denoising_unet,
            audio_guider=self.audio_processor,
            pose_encoder=self.pose_net,
            scheduler=self.scheduler,
        ).to(self.device, dtype=self.weight_dtype)
    
    async def generate_video(self, 
                           reference_image_path, 
                           audio_path, 
                           pose_dir=None,
                           width=None, 
                           height=None, 
                           steps=None,
                           cfg=None,
                           seed=None,
                           max_length=None):
        """
        生成视频
        
        参数:
            reference_image_path: 参考图像路径
            audio_path: 音频文件路径
            pose_dir: 姿势目录，如果为None则使用默认姿势
            width: 视频宽度
            height: 视频高度
            steps: 去噪步数
            cfg: 条件引导比例
            seed: 随机种子
            max_length: 最大帧数
            
        返回:
            dict: 包含生成视频信息的字典
        """
        if not self.initialized:
            raise RuntimeError("EchoMimic模型未初始化")
            
        # 参数处理
        width = width or self.default_width
        height = height or self.default_height
        steps = steps or self.default_steps
        cfg = cfg or self.default_cfg
        pose_dir = pose_dir or self.default_pose_dir
        
        # 清理CUDA缓存
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
        
        # 创建时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = f"echomimic_{timestamp}"
        save_path = self.output_dir / video_name
        
        try:
            # 创建临时工作目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir = Path(temp_dir)
                
                # 加载参考图像
                ref_image_pil = Image.open(reference_image_path).resize((width, height))
                
                # 配置pose序列
                from moviepy.editor import AudioFileClip
                audio_clip = AudioFileClip(audio_path)
                
                # 计算帧数
                fps = self.default_fps
                pose_count = len(os.listdir(pose_dir))
                audio_duration = audio_clip.duration
                
                if max_length:
                    length = min(max_length, int(audio_duration * fps), pose_count)
                else:
                    length = min(int(audio_duration * fps), pose_count)
                
                logger.info(f"生成视频长度: {length}帧，音频时长: {audio_duration}秒")
                
                # 准备姿势序列
                pose_list = []
                for index in range(length):
                    tgt_musk = np.zeros((width, height, 3)).astype('uint8')
                    tgt_musk_path = os.path.join(pose_dir, f"{index}.npy")
                    detected_pose = np.load(tgt_musk_path, allow_pickle=True).tolist()
                    imh_new, imw_new, rb, re, cb, ce = detected_pose['draw_pose_params']
                    im = draw_pose_select_v2(detected_pose, imh_new, imw_new, ref_w=800)
                    im = np.transpose(np.array(im), (1, 2, 0))
                    tgt_musk[rb:re, cb:ce, :] = im

                    tgt_musk_pil = Image.fromarray(np.array(tgt_musk)).convert('RGB')
                    pose_list.append(torch.Tensor(np.array(tgt_musk_pil)).to(dtype=self.weight_dtype, device=self.device).permute(2, 0, 1) / 255.0)
                
                poses_tensor = torch.stack(pose_list, dim=1).unsqueeze(0)
                
                # 设置随机种子
                if seed is None or seed < 0:
                    seed = np.random.randint(100, 1000000)
                generator = torch.manual_seed(seed)
                
                # 生成视频
                logger.info(f"开始生成视频，参考图像: {reference_image_path}, 音频: {audio_path}")
                
                # 截取音频
                audio_clip = audio_clip.set_duration(length / fps)
                
                # 生成视频
                video = self.pipe(
                    ref_image_pil,
                    audio_path,
                    poses_tensor[:,:,:length,...],
                    width,
                    height,
                    length,
                    steps,
                    cfg,
                    generator=generator,
                    audio_sample_rate=self.default_sample_rate,
                    context_frames=self.default_context_frames,
                    fps=fps,
                    context_overlap=self.default_context_overlap,
                    start_idx=0,
                ).videos
                
                # 保存视频
                final_length = min(video.shape[2], poses_tensor.shape[2], length)
                video_sig = video[:, :, :final_length, :, :]
                
                save_with_audio = str(save_path) + ".mp4"
                save_videos_grid(
                    video_sig,
                    save_with_audio,
                    n_rows=1,
                    fps=fps,
                    audio_path=audio_path,
                    audio_start_time=0.0,
                )
                
                # 视频的相对路径
                relative_path = save_with_audio.replace("frontend/public/", "/")
                
                # 返回结果
                result = {
                    "success": True,
                    "video_path": relative_path,
                    "width": width,
                    "height": height,
                    "frames": final_length,
                    "fps": fps,
                    "duration": final_length / fps,
                }
                
                return result
                
        except Exception as e:
            logger.error(f"生成视频失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
        finally:
            # 清理CUDA缓存
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

# 单例实例
_echomimic_generator = None

def get_echomimic_generator():
    """获取EchoMimic生成器单例实例"""
    global _echomimic_generator
    if _echomimic_generator is None:
        _echomimic_generator = EchoMimicGenerator()
    return _echomimic_generator
