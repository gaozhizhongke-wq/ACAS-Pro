"""
手势生成器 - AI驱动的肢体语言生成
"""

import random
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime

import numpy as np

from ..core.logging import get_logger

logger = get_logger(__name__)


class GestureType(Enum):
    """手势类型"""
    # 强调类
    POINTING = "pointing"           # 指向
    COUNTING = "counting"           # 数数
    EMPHASIS = "emphasis"           # 强调
    
    # 描述类
    SIZE_INDICATOR = "size"         # 大小指示
    SHAPE_DESCRIPTOR = "shape"      # 形状描述
    DIRECTION = "direction"         # 方向指示
    
    # 情感类
    WELCOME = "welcome"             # 欢迎
    ENCOURAGEMENT = "encourage"     # 鼓励
    CONFIDENCE = "confidence"       # 自信
    THINKING = "thinking"           # 思考
    
    # 交互类
    GREETING = "greeting"           # 问候
    FAREWELL = "farewell"           # 告别
    THANKS = "thanks"               # 感谢
    
    # 通用
    IDLE = "idle"                   # 待机
    TRANSITION = "transition"       # 过渡


class BodyPart(Enum):
    """身体部位"""
    HEAD = "head"
    NECK = "neck"
    SHOULDER_LEFT = "shoulder_l"
    SHOULDER_RIGHT = "shoulder_r"
    ARM_LEFT = "arm_l"
    ARM_RIGHT = "arm_r"
    ELBOW_LEFT = "elbow_l"
    ELBOW_RIGHT = "elbow_r"
    WRIST_LEFT = "wrist_l"
    WRIST_RIGHT = "wrist_r"
    HAND_LEFT = "hand_l"
    HAND_RIGHT = "hand_r"
    TORSO = "torso"
    HIP = "hip"


@dataclass
class JointRotation:
    """关节旋转"""
    pitch: float = 0.0    # X轴旋转 (俯仰)
    yaw: float = 0.0      # Y轴旋转 (偏航)
    roll: float = 0.0     # Z轴旋转 (翻滚)
    
    def to_dict(self) -> Dict[str, float]:
        return {'pitch': self.pitch, 'yaw': self.yaw, 'roll': self.roll}


@dataclass
class PoseFrame:
    """姿态帧"""
    timestamp: float
    duration: float
    
    # 各关节旋转
    joint_rotations: Dict[BodyPart, JointRotation] = field(default_factory=dict)
    
    # 手部姿态（手指弯曲度 0-1）
    hand_pose_left: Dict[str, float] = field(default_factory=dict)
    hand_pose_right: Dict[str, float] = field(default_factory=dict)
    
    # 表情强度
    facial_expression: str = "neutral"
    expression_intensity: float = 0.5
    
    def get_joint(self, part: BodyPart) -> JointRotation:
        """获取关节旋转"""
        return self.joint_rotations.get(part, JointRotation())


@dataclass
class Gesture:
    """手势动作"""
    id: str
    name: str
    type: GestureType
    
    # 关键帧
    keyframes: List[PoseFrame] = field(default_factory=list)
    
    # 元数据
    duration: float = 0.0
    intensity: float = 1.0
    priority: int = 0
    
    # 适用场景
    applicable_contexts: List[str] = field(default_factory=list)
    
    def get_duration(self) -> float:
        """获取总时长"""
        if self.keyframes:
            return max(kf.timestamp + kf.duration for kf in self.keyframes)
        return self.duration


class GestureGenerator:
    """手势生成器"""
    
    def __init__(self):
        self._gesture_library: Dict[str, Gesture] = {}
        self._load_gesture_library()
    
    def _load_gesture_library(self):
        """加载手势库"""
        # 预定义手势模板
        gestures = [
            # 欢迎手势
            Gesture(
                id="gesture_welcome_01",
                name="双手欢迎",
                type=GestureType.WELCOME,
                keyframes=self._create_welcome_gesture(),
                applicable_contexts=["opening", "greeting", "introduction"],
            ),
            
            # 强调手势
            Gesture(
                id="gesture_emphasis_01",
                name="单手强调",
                type=GestureType.EMPHASIS,
                keyframes=self._create_emphasis_gesture(),
                applicable_contexts=["key_point", "important_info", "conclusion"],
            ),
            
            # 指向手势
            Gesture(
                id="gesture_point_01",
                name="指向右侧",
                type=GestureType.POINTING,
                keyframes=self._create_pointing_gesture("right"),
                applicable_contexts=["reference", "indication", "direction"],
            ),
            
            # 思考手势
            Gesture(
                id="gesture_think_01",
                name="托腮思考",
                type=GestureType.THINKING,
                keyframes=self._create_thinking_gesture(),
                applicable_contexts=["question", "analysis", "consideration"],
            ),
            
            # 自信手势
            Gesture(
                id="gesture_confidence_01",
                name="双手叉腰",
                type=GestureType.CONFIDENCE,
                keyframes=self._create_confidence_gesture(),
                applicable_contexts=["statement", "guarantee", "promise"],
            ),
            
            # 数数手势
            Gesture(
                id="gesture_count_01",
                name="数手指",
                type=GestureType.COUNTING,
                keyframes=self._create_counting_gesture(3),
                applicable_contexts=["listing", "enumeration", "steps"],
            ),
            
            # 待机动画
            Gesture(
                id="gesture_idle_01",
                name="自然站立",
                type=GestureType.IDLE,
                keyframes=self._create_idle_gesture(),
                applicable_contexts=["waiting", "listening", "pause"],
            ),
            
            # 过渡动画
            Gesture(
                id="gesture_transition_01",
                name="双手展开",
                type=GestureType.TRANSITION,
                keyframes=self._create_transition_gesture(),
                applicable_contexts=["topic_change", "section_end", "summary"],
            ),
        ]
        
        for gesture in gestures:
            self._gesture_library[gesture.id] = gesture
    
    def _create_welcome_gesture(self) -> List[PoseFrame]:
        """创建欢迎手势"""
        return [
            PoseFrame(
                timestamp=0.0,
                duration=0.5,
                joint_rotations={
                    BodyPart.SHOULDER_LEFT: JointRotation(pitch=0, yaw=0, roll=-30),
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=30),
                    BodyPart.ARM_LEFT: JointRotation(pitch=0, yaw=0, roll=-20),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=0, yaw=0, roll=20),
                    BodyPart.ELBOW_LEFT: JointRotation(pitch=-90, yaw=0, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=-90, yaw=0, roll=0),
                },
                facial_expression="happy",
                expression_intensity=0.8,
            ),
            PoseFrame(
                timestamp=0.5,
                duration=1.0,
                joint_rotations={
                    BodyPart.SHOULDER_LEFT: JointRotation(pitch=0, yaw=0, roll=-45),
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=45),
                    BodyPart.ARM_LEFT: JointRotation(pitch=0, yaw=0, roll=-30),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=0, yaw=0, roll=30),
                    BodyPart.ELBOW_LEFT: JointRotation(pitch=-110, yaw=0, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=-110, yaw=0, roll=0),
                },
                facial_expression="happy",
                expression_intensity=0.9,
            ),
            PoseFrame(
                timestamp=1.5,
                duration=0.5,
                joint_rotations={
                    BodyPart.SHOULDER_LEFT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ARM_LEFT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ELBOW_LEFT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                },
                facial_expression="neutral",
                expression_intensity=0.5,
            ),
        ]
    
    def _create_emphasis_gesture(self) -> List[PoseFrame]:
        """创建强调手势"""
        return [
            PoseFrame(
                timestamp=0.0,
                duration=0.3,
                joint_rotations={
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=20),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=-30, yaw=0, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=-45, yaw=0, roll=0),
                },
                facial_expression="serious",
                expression_intensity=0.7,
            ),
            PoseFrame(
                timestamp=0.3,
                duration=0.4,
                joint_rotations={
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=30),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=-45, yaw=0, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=-30, yaw=0, roll=0),
                },
                hand_pose_right={'index': 1.0, 'thumb': 0.5},
                facial_expression="serious",
                expression_intensity=0.9,
            ),
            PoseFrame(
                timestamp=0.7,
                duration=0.3,
                joint_rotations={
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                },
                facial_expression="neutral",
                expression_intensity=0.5,
            ),
        ]
    
    def _create_pointing_gesture(self, direction: str) -> List[PoseFrame]:
        """创建指向手势"""
        yaw = 45 if direction == "right" else -45
        
        return [
            PoseFrame(
                timestamp=0.0,
                duration=0.5,
                joint_rotations={
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=yaw, roll=0),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=-20, yaw=yaw, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=-90, yaw=0, roll=0),
                    BodyPart.WRIST_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                },
                hand_pose_right={'index': 0.0, 'middle': 1.0, 'ring': 1.0, 'pinky': 1.0},
                facial_expression="neutral",
                expression_intensity=0.6,
            ),
            PoseFrame(
                timestamp=0.5,
                duration=1.0,
                joint_rotations={
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=yaw, roll=0),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=-20, yaw=yaw, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=-90, yaw=0, roll=0),
                },
                hand_pose_right={'index': 0.0, 'middle': 1.0, 'ring': 1.0, 'pinky': 1.0},
                facial_expression="neutral",
                expression_intensity=0.6,
            ),
            PoseFrame(
                timestamp=1.5,
                duration=0.5,
                joint_rotations={
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                },
                facial_expression="neutral",
                expression_intensity=0.5,
            ),
        ]
    
    def _create_thinking_gesture(self) -> List[PoseFrame]:
        """创建思考手势"""
        return [
            PoseFrame(
                timestamp=0.0,
                duration=2.0,
                joint_rotations={
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=10),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=-30, yaw=20, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=-120, yaw=0, roll=0),
                    BodyPart.HEAD: JointRotation(pitch=10, yaw=0, roll=5),
                },
                hand_pose_right={'thumb': 0.3, 'index': 0.0},
                facial_expression="thinking",
                expression_intensity=0.7,
            ),
            PoseFrame(
                timestamp=2.0,
                duration=0.5,
                joint_rotations={
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.HEAD: JointRotation(pitch=0, yaw=0, roll=0),
                },
                facial_expression="neutral",
                expression_intensity=0.5,
            ),
        ]
    
    def _create_confidence_gesture(self) -> List[PoseFrame]:
        """创建自信手势"""
        return [
            PoseFrame(
                timestamp=0.0,
                duration=1.5,
                joint_rotations={
                    BodyPart.SHOULDER_LEFT: JointRotation(pitch=0, yaw=0, roll=-20),
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=20),
                    BodyPart.ARM_LEFT: JointRotation(pitch=-10, yaw=0, roll=0),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=-10, yaw=0, roll=0),
                    BodyPart.ELBOW_LEFT: JointRotation(pitch=-30, yaw=0, roll=-20),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=-30, yaw=0, roll=20),
                    BodyPart.TORSO: JointRotation(pitch=-5, yaw=0, roll=0),
                },
                facial_expression="confident",
                expression_intensity=0.8,
            ),
            PoseFrame(
                timestamp=1.5,
                duration=0.5,
                joint_rotations={
                    BodyPart.SHOULDER_LEFT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ARM_LEFT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ELBOW_LEFT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.TORSO: JointRotation(pitch=0, yaw=0, roll=0),
                },
                facial_expression="neutral",
                expression_intensity=0.5,
            ),
        ]
    
    def _create_counting_gesture(self, count: int) -> List[PoseFrame]:
        """创建数数手势"""
        keyframes = []
        
        for i in range(count):
            t = i * 1.0
            
            # 举起手指
            keyframes.append(PoseFrame(
                timestamp=t,
                duration=0.3,
                joint_rotations={
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=20),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=-60, yaw=0, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=-10, yaw=0, roll=0),
                },
                hand_pose_right=self._get_finger_pose(i + 1),
                facial_expression="neutral",
                expression_intensity=0.6,
            ))
            
            # 保持
            keyframes.append(PoseFrame(
                timestamp=t + 0.3,
                duration=0.5,
                joint_rotations={
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=20),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=-60, yaw=0, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=-10, yaw=0, roll=0),
                },
                hand_pose_right=self._get_finger_pose(i + 1),
                facial_expression="neutral",
                expression_intensity=0.6,
            ))
        
        # 复位
        keyframes.append(PoseFrame(
            timestamp=count * 1.0,
            duration=0.5,
            joint_rotations={
                BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                BodyPart.ARM_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                BodyPart.ELBOW_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
            },
            facial_expression="neutral",
            expression_intensity=0.5,
        ))
        
        return keyframes
    
    def _get_finger_pose(self, number: int) -> Dict[str, float]:
        """获取手指姿势"""
        poses = {
            1: {'thumb': 1.0, 'index': 0.0, 'middle': 1.0, 'ring': 1.0, 'pinky': 1.0},
            2: {'thumb': 1.0, 'index': 0.0, 'middle': 0.0, 'ring': 1.0, 'pinky': 1.0},
            3: {'thumb': 1.0, 'index': 0.0, 'middle': 0.0, 'ring': 0.0, 'pinky': 1.0},
            4: {'thumb': 1.0, 'index': 0.0, 'middle': 0.0, 'ring': 0.0, 'pinky': 0.0},
            5: {'thumb': 0.0, 'index': 0.0, 'middle': 0.0, 'ring': 0.0, 'pinky': 0.0},
        }
        return poses.get(number, poses[1])
    
    def _create_idle_gesture(self) -> List[PoseFrame]:
        """创建待机动画"""
        return [
            PoseFrame(
                timestamp=0.0,
                duration=3.0,
                joint_rotations={
                    BodyPart.HEAD: JointRotation(pitch=2, yaw=1, roll=0),
                },
                facial_expression="neutral",
                expression_intensity=0.3,
            ),
            PoseFrame(
                timestamp=3.0,
                duration=3.0,
                joint_rotations={
                    BodyPart.HEAD: JointRotation(pitch=-1, yaw=-1, roll=0),
                },
                facial_expression="neutral",
                expression_intensity=0.3,
            ),
        ]
    
    def _create_transition_gesture(self) -> List[PoseFrame]:
        """创建过渡手势"""
        return [
            PoseFrame(
                timestamp=0.0,
                duration=0.5,
                joint_rotations={
                    BodyPart.SHOULDER_LEFT: JointRotation(pitch=0, yaw=0, roll=-30),
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=30),
                    BodyPart.ARM_LEFT: JointRotation(pitch=-20, yaw=0, roll=0),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=-20, yaw=0, roll=0),
                    BodyPart.ELBOW_LEFT: JointRotation(pitch=-60, yaw=0, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=-60, yaw=0, roll=0),
                },
                facial_expression="neutral",
                expression_intensity=0.5,
            ),
            PoseFrame(
                timestamp=0.5,
                duration=1.0,
                joint_rotations={
                    BodyPart.SHOULDER_LEFT: JointRotation(pitch=0, yaw=0, roll=-45),
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=45),
                    BodyPart.ARM_LEFT: JointRotation(pitch=-40, yaw=0, roll=0),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=-40, yaw=0, roll=0),
                    BodyPart.ELBOW_LEFT: JointRotation(pitch=-80, yaw=0, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=-80, yaw=0, roll=0),
                },
                facial_expression="neutral",
                expression_intensity=0.5,
            ),
            PoseFrame(
                timestamp=1.5,
                duration=0.5,
                joint_rotations={
                    BodyPart.SHOULDER_LEFT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.SHOULDER_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ARM_LEFT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ARM_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ELBOW_LEFT: JointRotation(pitch=0, yaw=0, roll=0),
                    BodyPart.ELBOW_RIGHT: JointRotation(pitch=0, yaw=0, roll=0),
                },
                facial_expression="neutral",
                expression_intensity=0.5,
            ),
        ]
    
    def generate_gestures_for_script(
        self,
        script: str,
        duration: float,
        style: str = "natural"
    ) -> List[Gesture]:
        """根据脚本生成手势序列"""
        gestures = []
        current_time = 0.0
        
        # 分析脚本内容，识别关键段落
        segments = self._analyze_script(script)
        
        for segment in segments:
            # 根据段落类型选择手势
            gesture = self._select_gesture_for_segment(segment, style)
            
            if gesture:
                gestures.append(gesture)
                current_time += gesture.get_duration()
        
        # 填充待机动画
        while current_time < duration:
            idle = self.get_gesture("gesture_idle_01")
            if idle:
                gestures.append(idle)
                current_time += idle.get_duration()
        
        return gestures
    
    def _analyze_script(self, script: str) -> List[Dict[str, Any]]:
        """分析脚本，识别关键段落"""
        segments = []
        
        # 简单的关键词匹配
        keywords = {
            'welcome': ['欢迎', '大家好', 'hello', 'hi'],
            'emphasis': ['重要', '关键', '注意', '必须', '一定'],
            'pointing': ['看', '这里', '那边', '这个', '那个'],
            'thinking': ['思考', '考虑', '可能', '也许', '?'],
            'confidence': ['保证', '确保', '绝对', '肯定', '一定'],
            'counting': ['第一', '第二', '第三', '首先', '其次', '最后'],
            'transition': ['接下来', '然后', '另外', '此外', '总结'],
        }
        
        lines = script.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测段落类型
            segment_type = 'neutral'
            for seg_type, words in keywords.items():
                if any(word in line for word in words):
                    segment_type = seg_type
                    break
            
            segments.append({
                'text': line,
                'type': segment_type,
                'duration': max(2.0, len(line) * 0.3),  # 估算时长
            })
        
        return segments
    
    def _select_gesture_for_segment(
        self,
        segment: Dict[str, Any],
        style: str
    ) -> Optional[Gesture]:
        """为段落选择合适的手势"""
        type_mapping = {
            'welcome': GestureType.WELCOME,
            'emphasis': GestureType.EMPHASIS,
            'pointing': GestureType.POINTING,
            'thinking': GestureType.THINKING,
            'confidence': GestureType.CONFIDENCE,
            'counting': GestureType.COUNTING,
            'transition': GestureType.TRANSITION,
            'neutral': GestureType.IDLE,
        }
        
        gesture_type = type_mapping.get(segment['type'], GestureType.IDLE)
        
        # 查找匹配的手势
        matching = [
            g for g in self._gesture_library.values()
            if g.type == gesture_type
        ]
        
        if matching:
            return random.choice(matching)
        
        # 默认返回待机
        return self.get_gesture("gesture_idle_01")
    
    def get_gesture(self, gesture_id: str) -> Optional[Gesture]:
        """获取手势"""
        return self._gesture_library.get(gesture_id)
    
    def get_gestures_by_type(self, gesture_type: GestureType) -> List[Gesture]:
        """按类型获取手势"""
        return [
            g for g in self._gesture_library.values()
            if g.type == gesture_type
        ]
    
    def interpolate_pose(
        self,
        pose1: PoseFrame,
        pose2: PoseFrame,
        t: float
    ) -> PoseFrame:
        """插值两个姿态"""
        # 线性插值
        def lerp(a, b, t):
            return a + (b - a) * t
        
        # 插值所有关节
        joint_rotations = {}
        all_parts = set(pose1.joint_rotations.keys()) | set(pose2.joint_rotations.keys())
        
        for part in all_parts:
            r1 = pose1.get_joint(part)
            r2 = pose2.get_joint(part)
            
            joint_rotations[part] = JointRotation(
                pitch=lerp(r1.pitch, r2.pitch, t),
                yaw=lerp(r1.yaw, r2.yaw, t),
                roll=lerp(r1.roll, r2.roll, t),
            )
        
        return PoseFrame(
            timestamp=lerp(pose1.timestamp, pose2.timestamp, t),
            duration=lerp(pose1.duration, pose2.duration, t),
            joint_rotations=joint_rotations,
            facial_expression=pose1.facial_expression if t < 0.5 else pose2.facial_expression,
            expression_intensity=lerp(pose1.expression_intensity, pose2.expression_intensity, t),
        )
    
    def export_gesture(self, gesture: Gesture, output_path: str) -> bool:
        """导出手势数据"""
        try:
            data = {
                'id': gesture.id,
                'name': gesture.name,
                'type': gesture.type.value,
                'duration': gesture.get_duration(),
                'keyframes': [
                    {
                        'timestamp': kf.timestamp,
                        'duration': kf.duration,
                        'joints': {
                            part.value: rot.to_dict()
                            for part, rot in kf.joint_rotations.items()
                        },
                        'facial_expression': kf.facial_expression,
                        'expression_intensity': kf.expression_intensity,
                    }
                    for kf in gesture.keyframes
                ]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Failed to export gesture: {e}")
            return False
