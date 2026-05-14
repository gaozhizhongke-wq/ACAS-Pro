"""
口型同步引擎 - 语音驱动面部动画
"""

import os
import json
import math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from pathlib import Path

import numpy as np

from ..core.config import config
from ..core.logging import get_logger

logger = get_logger(__name__)


class LipSyncModel(Enum):
    """口型同步模型"""
    WAV2LIP = "wav2lip"           # Wav2Lip - 高精度
    SADTALKER = "sadtalker"       # SadTalker - 3D头部
    VIDEO_RETALKING = "retalking" # VideoReTalking - 表情控制
    IP_LAP = "ip_lap"             # IP_LAP - 轻量级


@dataclass
class VisemeFrame:
    """视位帧 - 表示一帧的口型状态"""
    timestamp: float              # 时间戳（秒）
    duration: float               # 持续时间
    
    # 视位权重 (Viseme weights)
    # 标准视位: A, E, I, O, U, M, B, P, F, V, S, Z, etc.
    visemes: Dict[str, float] = None
    
    # 嘴部开合度 (0-1)
    jaw_open: float = 0.0
    
    # 嘴唇圆度 (0-1)
    lip_roundness: float = 0.0
    
    # 嘴唇宽度 (-1 to 1, 负值=收窄, 正值=展宽)
    lip_width: float = 0.0
    
    def __post_init__(self):
        if self.visemes is None:
            self.visemes = {}


@dataclass
class Phoneme:
    """音素"""
    symbol: str                   # 音素符号
    start_time: float
    end_time: float
    
    # 对应的视位
    viseme: str = ""
    
    # 强度
    intensity: float = 1.0


class LipSyncEngine:
    """口型同步引擎"""
    
    # 音素到视位的映射表
    PHONEME_TO_VISEME = {
        # 元音
        'AA': 'A', 'AE': 'A', 'AH': 'A',          # 啊
        'AO': 'O', 'AW': 'O', 'OY': 'O',          # 哦
        'EH': 'E', 'ER': 'E', 'EY': 'E',          # 诶
        'IH': 'I', 'IY': 'I',                      # 衣
        'UH': 'U', 'UW': 'U',                      # 乌
        
        # 辅音 - 唇音
        'B': 'M', 'P': 'M', 'M': 'M',             # 闭唇
        
        # 辅音 - 唇齿音
        'F': 'F', 'V': 'F',                        # 唇齿
        
        # 辅音 - 齿音
        'TH': 'T', 'DH': 'T',                      # 齿间
        
        # 辅音 - 齿龈音
        'T': 'T', 'D': 'T', 'N': 'T', 'S': 'S', 'Z': 'S',
        
        # 辅音 - 龈后音
        'SH': 'CH', 'ZH': 'CH', 'CH': 'CH', 'JH': 'CH',
        
        # 辅音 - 软腭音
        'K': 'K', 'G': 'K', 'NG': 'K',
        
        # 辅音 - 声门音
        'HH': 'K',
        
        # 辅音 - 近音
        'L': 'T', 'R': 'E', 'W': 'U', 'Y': 'I',
        
        # 静音
        'SIL': 'rest', 'SP': 'rest', 'SPN': 'rest',
    }
    
    # 视位形状定义
    VISEME_SHAPES = {
        'rest': {'jaw_open': 0.0, 'lip_roundness': 0.0, 'lip_width': 0.0},
        'A': {'jaw_open': 0.8, 'lip_roundness': 0.0, 'lip_width': 0.3},
        'E': {'jaw_open': 0.5, 'lip_roundness': 0.0, 'lip_width': 0.5},
        'I': {'jaw_open': 0.2, 'lip_roundness': 0.0, 'lip_width': -0.3},
        'O': {'jaw_open': 0.4, 'lip_roundness': 0.8, 'lip_width': 0.0},
        'U': {'jaw_open': 0.2, 'lip_roundness': 0.7, 'lip_width': -0.2},
        'M': {'jaw_open': 0.0, 'lip_roundness': 0.0, 'lip_width': 0.0},
        'F': {'jaw_open': 0.1, 'lip_roundness': 0.0, 'lip_width': 0.2},
        'T': {'jaw_open': 0.2, 'lip_roundness': 0.0, 'lip_width': 0.0},
        'S': {'jaw_open': 0.1, 'lip_roundness': 0.0, 'lip_width': 0.1},
        'CH': {'jaw_open': 0.2, 'lip_roundness': 0.3, 'lip_width': -0.1},
        'K': {'jaw_open': 0.3, 'lip_roundness': 0.0, 'lip_width': 0.0},
    }
    
    def __init__(self, model: LipSyncModel = LipSyncModel.WAV2LIP):
        self.model = model
        self.model_path = self._get_model_path()
        self._initialized = False
    
    def _get_model_path(self) -> str:
        """获取模型路径"""
        model_dir = Path(config().data_dir) / "models" / "lip_sync"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_files = {
            LipSyncModel.WAV2LIP: "wav2lip_gan.pth",
            LipSyncModel.SADTALKER: "sadtalker.pth",
            LipSyncModel.VIDEO_RETALKING: "retalking.pth",
            LipSyncModel.IP_LAP: "ip_lap.pth",
        }
        
        return str(model_dir / model_files.get(self.model, "wav2lip_gan.pth"))
    
    def initialize(self) -> bool:
        """初始化模型"""
        try:
            # TODO: 加载实际的深度学习模型
            # 这里使用模拟实现
            
            if not os.path.exists(self.model_path):
                logger.warning(f"Model not found: {self.model_path}, using fallback")
                # 使用基于规则的口型同步作为后备
            
            self._initialized = True
            logger.info(f"Lip sync engine initialized with model: {self.model.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize lip sync engine: {e}")
            return False
    
    def audio_to_phonemes(self, audio_path: str) -> List[Phoneme]:
        """音频转音素序列"""
        # TODO: 集成实际的语音识别模型（如Montreal Forced Aligner）
        # 目前使用模拟数据
        
        phonemes = []
        
        # 模拟音素序列 - "Hello World"
        mock_sequence = [
            ('SIL', 0.0, 0.1),
            ('HH', 0.1, 0.15),
            ('EH', 0.15, 0.25),
            ('L', 0.25, 0.35),
            ('OW', 0.35, 0.5),
            ('SIL', 0.5, 0.6),
            ('W', 0.6, 0.7),
            ('ER', 0.7, 0.85),
            ('L', 0.85, 0.9),
            ('D', 0.9, 1.0),
            ('SIL', 1.0, 1.1),
        ]
        
        for symbol, start, end in mock_sequence:
            viseme = self.PHONEME_TO_VISEME.get(symbol.upper(), 'rest')
            phonemes.append(Phoneme(
                symbol=symbol,
                start_time=start,
                end_time=end,
                viseme=viseme,
                intensity=1.0
            ))
        
        return phonemes
    
    def phonemes_to_visemes(self, phonemes: List[Phoneme], fps: float = 30.0) -> List[VisemeFrame]:
        """音素序列转视位动画"""
        if not phonemes:
            return []
        
        viseme_frames = []
        frame_duration = 1.0 / fps
        
        # 计算总时长
        total_duration = max(p.end_time for p in phonemes)
        num_frames = int(total_duration * fps) + 1
        
        for i in range(num_frames):
            timestamp = i * frame_duration
            
            # 找到当前时间对应的音素
            current_phoneme = None
            for p in phonemes:
                if p.start_time <= timestamp < p.end_time:
                    current_phoneme = p
                    break
            
            if current_phoneme:
                # 获取视位形状
                viseme_shape = self.VISEME_SHAPES.get(
                    current_phoneme.viseme,
                    self.VISEME_SHAPES['rest']
                )
                
                # 计算过渡（与前后音素混合）
                blend_factor = self._calculate_blend_factor(
                    timestamp, current_phoneme, phonemes
                )
                
                frame = VisemeFrame(
                    timestamp=timestamp,
                    duration=frame_duration,
                    visemes={current_phoneme.viseme: current_phoneme.intensity},
                    jaw_open=viseme_shape['jaw_open'] * blend_factor,
                    lip_roundness=viseme_shape['lip_roundness'] * blend_factor,
                    lip_width=viseme_shape['lip_width'] * blend_factor,
                )
            else:
                # 静音帧
                frame = VisemeFrame(
                    timestamp=timestamp,
                    duration=frame_duration,
                    visemes={'rest': 1.0},
                    jaw_open=0.0,
                    lip_roundness=0.0,
                    lip_width=0.0,
                )
            
            viseme_frames.append(frame)
        
        return viseme_frames
    
    def _calculate_blend_factor(
        self,
        timestamp: float,
        current: Phoneme,
        all_phonemes: List[Phoneme]
    ) -> float:
        """计算音素间的混合因子，实现平滑过渡"""
        phoneme_duration = current.end_time - current.start_time
        
        if phoneme_duration == 0:
            return 1.0
        
        # 在音素中间达到最大值，两端过渡
        progress = (timestamp - current.start_time) / phoneme_duration
        
        # 使用余弦函数创建平滑曲线
        blend = 0.5 * (1 - math.cos(progress * math.pi))
        
        return blend
    
    def generate_lip_sync_animation(
        self,
        audio_path: str,
        fps: float = 30.0,
        smooth: bool = True
    ) -> List[VisemeFrame]:
        """生成口型同步动画"""
        # 1. 音频转音素
        phonemes = self.audio_to_phonemes(audio_path)
        
        # 2. 音素转视位
        visemes = self.phonemes_to_visemes(phonemes, fps)
        
        # 3. 平滑处理
        if smooth:
            visemes = self._smooth_visemes(visemes)
        
        return visemes
    
    def _smooth_visemes(self, visemes: List[VisemeFrame], window_size: int = 3) -> List[VisemeFrame]:
        """对视位序列进行平滑处理"""
        if len(visemes) < window_size:
            return visemes
        
        smoothed = []
        half_window = window_size // 2
        
        for i in range(len(visemes)):
            # 计算窗口内的平均值
            start = max(0, i - half_window)
            end = min(len(visemes), i + half_window + 1)
            
            window = visemes[start:end]
            
            avg_jaw = sum(v.jaw_open for v in window) / len(window)
            avg_round = sum(v.lip_roundness for v in window) / len(window)
            avg_width = sum(v.lip_width for v in window) / len(window)
            
            smoothed_frame = VisemeFrame(
                timestamp=visemes[i].timestamp,
                duration=visemes[i].duration,
                visemes=visemes[i].visemes,
                jaw_open=avg_jaw,
                lip_roundness=avg_round,
                lip_width=avg_width,
            )
            smoothed.append(smoothed_frame)
        
        return smoothed
    
    def apply_to_avatar(
        self,
        avatar_model_path: str,
        visemes: List[VisemeFrame],
        output_path: str
    ) -> bool:
        """将口型动画应用到数字人模型"""
        try:
            # TODO: 集成实际的3D模型驱动
            # 1. 加载3D模型（FBX/GLTF）
            # 2. 应用blendshape权重
            # 3. 渲染视频帧
            # 4. 合成最终视频
            
            logger.info(f"Applying lip sync to avatar: {avatar_model_path}")
            logger.info(f"Output: {output_path}")
            
            # 模拟处理
            import time
            time.sleep(0.5)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply lip sync: {e}")
            return False
    
    def export_animation_data(
        self,
        visemes: List[VisemeFrame],
        output_path: str,
        format: str = "json"
    ) -> bool:
        """导出动画数据"""
        try:
            if format == "json":
                data = {
                    'fps': 30.0,
                    'frames': [
                        {
                            'timestamp': v.timestamp,
                            'jaw_open': v.jaw_open,
                            'lip_roundness': v.lip_roundness,
                            'lip_width': v.lip_width,
                            'visemes': v.visemes,
                        }
                        for v in visemes
                    ]
                }
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            elif format == "csv":
                import csv
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['timestamp', 'jaw_open', 'lip_roundness', 'lip_width'])
                    for v in visemes:
                        writer.writerow([v.timestamp, v.jaw_open, v.lip_roundness, v.lip_width])
            
            logger.info(f"Animation data exported to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export animation: {e}")
            return False
    
    def preview_viseme(self, viseme_code: str) -> Dict[str, float]:
        """预览视位形状"""
        return self.VISEME_SHAPES.get(viseme_code, self.VISEME_SHAPES['rest'])
    
    def get_supported_visemes(self) -> List[str]:
        """获取支持的视位列表"""
        return list(self.VISEME_SHAPES.keys())
    
    def estimate_processing_time(self, audio_duration: float) -> float:
        """估算处理时间"""
        # 基于音频时长的估算
        base_time = 2.0  # 基础时间
        processing_rate = 0.5  # 处理速度倍数
        
        return base_time + audio_duration * processing_rate
