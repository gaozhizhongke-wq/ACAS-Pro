"""
场景适配器 - 数字人与场景的智能融合
"""

import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from pathlib import Path

from ..core.config import config
from ..core.logging import get_logger

logger = get_logger(__name__)


class SceneType(Enum):
    """场景类型"""
    PRODUCT_SHOWCASE = "product_showcase"    # 产品展示
    LIVE_STREAMING = "live_streaming"        # 直播带货
    NEWS_BROADCAST = "news_broadcast"        # 新闻播报
    EDUCATIONAL = "educational"              # 教育培训
    CORPORATE = "corporate"                  # 企业宣传
    ENTERTAINMENT = "entertainment"          # 娱乐内容
    SOCIAL_MEDIA = "social_media"            # 社交媒体
    E_COMMERCE = "e_commerce"                # 电商推广


class BackgroundType(Enum):
    """背景类型"""
    STUDIO = "studio"                        # 摄影棚
    VIRTUAL = "virtual"                      # 虚拟背景
    REAL_LOCATION = "real_location"          # 实景
    GREEN_SCREEN = "green_screen"            # 绿幕
    CUSTOM_IMAGE = "custom_image"            # 自定义图片
    GRADIENT = "gradient"                    # 渐变色
    BLURRED = "blurred"                      # 模糊背景


class LightingPreset(Enum):
    """灯光预设"""
    STANDARD = "standard"                    # 标准
    WARM = "warm"                            # 暖光
    COOL = "cool"                            # 冷光
    DRAMATIC = "dramatic"                    # 戏剧性
    SOFT = "soft"                            # 柔光
    BRIGHT = "bright"                        # 明亮
    DARK = "dark"                            # 暗调
    PRODUCT = "product"                      # 产品光
    BEAUTY = "beauty"                        # 美颜光


class CameraAngle(Enum):
    """拍摄角度"""
    FRONT = "front"                          # 正面
    THREE_QUARTER = "three_quarter"          # 3/4侧面
    SIDE = "side"                            # 侧面
    HIGH_ANGLE = "high_angle"                # 俯拍
    LOW_ANGLE = "low_angle"                  # 仰拍
    OVERHEAD = "overhead"                    # 顶拍
    CLOSE_UP = "close_up"                    # 特写
    MEDIUM = "medium"                        # 中景
    WIDE = "wide"                            # 全景


@dataclass
class LightingConfig:
    """灯光配置"""
    key_light_intensity: float = 1.0         # 主光强度
    key_light_angle: Tuple[float, float] = (45, 45)  # (水平, 垂直)
    key_light_color: str = "#FFFFFF"         # 主光颜色
    
    fill_light_intensity: float = 0.5        # 补光强度
    fill_light_angle: Tuple[float, float] = (-45, 30)
    fill_light_color: str = "#FFFFFF"
    
    back_light_intensity: float = 0.3        # 轮廓光强度
    back_light_angle: Tuple[float, float] = (180, 60)
    back_light_color: str = "#FFFFFF"
    
    ambient_intensity: float = 0.2           # 环境光强度
    ambient_color: str = "#E8E8E8"


@dataclass
class CameraConfig:
    """相机配置"""
    angle: CameraAngle = CameraAngle.FRONT
    distance: str = "medium"                 # close/medium/wide
    height: float = 0.0                      # 相对高度
    
    # 镜头参数
    focal_length: float = 50.0               # 焦距(mm)
    aperture: float = 2.8                    # 光圈
    focus_distance: float = 2.0              # 对焦距离
    
    # 运动
    movement: str = "static"                 # static/pan/tilt/zoom/dolly
    movement_speed: float = 0.0


@dataclass
class SceneConfig:
    """场景配置"""
    id: str
    name: str
    description: str = ""
    
    # 场景类型
    scene_type: SceneType = SceneType.PRODUCT_SHOWCASE
    
    # 背景
    background_type: BackgroundType = BackgroundType.STUDIO
    background_path: Optional[str] = None
    background_color: str = "#1a1a2e"
    
    # 灯光
    lighting_preset: LightingPreset = LightingPreset.STANDARD
    lighting_config: LightingConfig = field(default_factory=LightingConfig)
    
    # 相机
    camera_config: CameraConfig = field(default_factory=CameraConfig)
    
    # 数字人位置
    avatar_position: Tuple[float, float] = (0.5, 0.5)  # (x, y) 归一化坐标
    avatar_scale: float = 0.75
    avatar_layer: int = 1                    # 图层顺序
    
    # 道具
    props: List[Dict[str, Any]] = field(default_factory=list)
    
    # 特效
    effects: List[str] = field(default_factory=list)
    
    # 元数据
    created_at: str = field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())
    owner_id: Optional[str] = None


class SceneAdapter:
    """场景适配器"""
    
    # 场景模板库
    SCENE_TEMPLATES = {
        SceneType.PRODUCT_SHOWCASE: {
            'name': '产品展示场景',
            'background_type': BackgroundType.STUDIO,
            'background_color': '#f5f5f5',
            'lighting_preset': LightingPreset.PRODUCT,
            'camera_angle': CameraAngle.FRONT,
            'avatar_position': (0.3, 0.5),
            'avatar_scale': 0.6,
        },
        SceneType.LIVE_STREAMING: {
            'name': '直播带货场景',
            'background_type': BackgroundType.VIRTUAL,
            'background_color': '#ff6b6b',
            'lighting_preset': LightingPreset.BEAUTY,
            'camera_angle': CameraAngle.FRONT,
            'avatar_position': (0.5, 0.5),
            'avatar_scale': 0.8,
        },
        SceneType.NEWS_BROADCAST: {
            'name': '新闻播报场景',
            'background_type': BackgroundType.VIRTUAL,
            'background_color': '#1a1a2e',
            'lighting_preset': LightingPreset.STANDARD,
            'camera_angle': CameraAngle.FRONT,
            'avatar_position': (0.5, 0.5),
            'avatar_scale': 0.7,
        },
        SceneType.EDUCATIONAL: {
            'name': '教育培训场景',
            'background_type': BackgroundType.STUDIO,
            'background_color': '#e8f4f8',
            'lighting_preset': LightingPreset.SOFT,
            'camera_angle': CameraAngle.THREE_QUARTER,
            'avatar_position': (0.4, 0.5),
            'avatar_scale': 0.75,
        },
        SceneType.CORPORATE: {
            'name': '企业宣传场景',
            'background_type': BackgroundType.REAL_LOCATION,
            'background_color': '#2c3e50',
            'lighting_preset': LightingPreset.DRAMATIC,
            'camera_angle': CameraAngle.THREE_QUARTER,
            'avatar_position': (0.35, 0.5),
            'avatar_scale': 0.65,
        },
        SceneType.ENTERTAINMENT: {
            'name': '娱乐内容场景',
            'background_type': BackgroundType.VIRTUAL,
            'background_color': '#9b59b6',
            'lighting_preset': LightingPreset.DRAMATIC,
            'camera_angle': CameraAngle.FRONT,
            'avatar_position': (0.5, 0.5),
            'avatar_scale': 0.85,
        },
        SceneType.SOCIAL_MEDIA: {
            'name': '社交媒体场景',
            'background_type': BackgroundType.GRADIENT,
            'background_color': '#667eea',
            'lighting_preset': LightingPreset.WARM,
            'camera_angle': CameraAngle.CLOSE_UP,
            'avatar_position': (0.5, 0.5),
            'avatar_scale': 0.9,
        },
        SceneType.E_COMMERCE: {
            'name': '电商推广场景',
            'background_type': BackgroundType.STUDIO,
            'background_color': '#ffffff',
            'lighting_preset': LightingPreset.BRIGHT,
            'camera_angle': CameraAngle.FRONT,
            'avatar_position': (0.5, 0.5),
            'avatar_scale': 0.7,
        },
    }
    
    # 灯光预设配置
    LIGHTING_PRESETS = {
        LightingPreset.STANDARD: LightingConfig(
            key_light_intensity=1.0,
            key_light_angle=(45, 45),
            fill_light_intensity=0.5,
            fill_light_angle=(-45, 30),
            back_light_intensity=0.3,
            ambient_intensity=0.2,
        ),
        LightingPreset.WARM: LightingConfig(
            key_light_intensity=1.0,
            key_light_color="#FFF8DC",
            fill_light_intensity=0.4,
            fill_light_color="#FFE4B5",
            ambient_color="#FFF5E6",
        ),
        LightingPreset.COOL: LightingConfig(
            key_light_intensity=1.0,
            key_light_color="#F0F8FF",
            fill_light_intensity=0.4,
            fill_light_color="#E6F3FF",
            ambient_color="#F5F8FF",
        ),
        LightingPreset.DRAMATIC: LightingConfig(
            key_light_intensity=1.2,
            key_light_angle=(60, 60),
            fill_light_intensity=0.2,
            back_light_intensity=0.5,
            ambient_intensity=0.1,
        ),
        LightingPreset.SOFT: LightingConfig(
            key_light_intensity=0.8,
            fill_light_intensity=0.6,
            back_light_intensity=0.2,
            ambient_intensity=0.3,
        ),
        LightingPreset.BRIGHT: LightingConfig(
            key_light_intensity=1.2,
            fill_light_intensity=0.7,
            back_light_intensity=0.4,
            ambient_intensity=0.4,
        ),
        LightingPreset.PRODUCT: LightingConfig(
            key_light_intensity=1.1,
            key_light_angle=(30, 45),
            fill_light_intensity=0.6,
            fill_light_angle=(-30, 30),
            back_light_intensity=0.4,
            ambient_intensity=0.25,
        ),
        LightingPreset.BEAUTY: LightingConfig(
            key_light_intensity=0.9,
            key_light_angle=(0, 45),
            fill_light_intensity=0.7,
            fill_light_angle=(0, 30),
            back_light_intensity=0.3,
            ambient_intensity=0.3,
        ),
    }
    
    def __init__(self):
        self._custom_scenes: Dict[str, SceneConfig] = {}
        self._load_custom_scenes()
    
    def _load_custom_scenes(self):
        """加载自定义场景"""
        scenes_dir = Path(config().data_dir) / "avatars" / "scenes"
        scenes_dir.mkdir(parents=True, exist_ok=True)
        
        for scene_file in scenes_dir.glob("*.json"):
            try:
                with open(scene_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    scene = self._dict_to_scene(data)
                    self._custom_scenes[scene.id] = scene
            except Exception as e:
                logger.warning(f"Failed to load scene {scene_file}: {e}")
    
    def create_scene_from_template(
        self,
        scene_type: SceneType,
        name: Optional[str] = None,
        customizations: Optional[Dict[str, Any]] = None
    ) -> SceneConfig:
        """从模板创建场景"""
        template = self.SCENE_TEMPLATES.get(scene_type, self.SCENE_TEMPLATES[SceneType.PRODUCT_SHOWCASE])
        
        scene_id = f"scene_{__import__('datetime').datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        scene = SceneConfig(
            id=scene_id,
            name=name or template['name'],
            scene_type=scene_type,
            background_type=template['background_type'],
            background_color=template['background_color'],
            lighting_preset=template['lighting_preset'],
            lighting_config=self.LIGHTING_PRESETS.get(
                template['lighting_preset'],
                LightingConfig()
            ),
            camera_config=CameraConfig(
                angle=template['camera_angle'],
                distance='medium',
            ),
            avatar_position=template['avatar_position'],
            avatar_scale=template['avatar_scale'],
        )
        
        # 应用自定义
        if customizations:
            if 'background_color' in customizations:
                scene.background_color = customizations['background_color']
            if 'avatar_position' in customizations:
                scene.avatar_position = tuple(customizations['avatar_position'])
            if 'avatar_scale' in customizations:
                scene.avatar_scale = customizations['avatar_scale']
            if 'lighting_preset' in customizations:
                preset = LightingPreset(customizations['lighting_preset'])
                scene.lighting_preset = preset
                scene.lighting_config = self.LIGHTING_PRESETS.get(preset, LightingConfig())
        
        # 保存
        self._save_scene(scene)
        
        return scene
    
    def _save_scene(self, scene: SceneConfig):
        """保存场景配置"""
        scenes_dir = Path(config().data_dir) / "avatars" / "scenes"
        scenes_dir.mkdir(parents=True, exist_ok=True)
        
        scene_file = scenes_dir / f"{scene.id}.json"
        
        data = {
            'id': scene.id,
            'name': scene.name,
            'description': scene.description,
            'scene_type': scene.scene_type.value,
            'background_type': scene.background_type.value,
            'background_path': scene.background_path,
            'background_color': scene.background_color,
            'lighting_preset': scene.lighting_preset.value,
            'camera_angle': scene.camera_config.angle.value,
            'camera_distance': scene.camera_config.distance,
            'avatar_position': scene.avatar_position,
            'avatar_scale': scene.avatar_scale,
            'props': scene.props,
            'effects': scene.effects,
            'created_at': scene.created_at,
            'owner_id': scene.owner_id,
        }
        
        with open(scene_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self._custom_scenes[scene.id] = scene
    
    def get_scene(self, scene_id: str) -> Optional[SceneConfig]:
        """获取场景"""
        return self._custom_scenes.get(scene_id)
    
    def get_all_scenes(self) -> List[SceneConfig]:
        """获取所有场景"""
        return list(self._custom_scenes.values())
    
    def get_scenes_by_type(self, scene_type: SceneType) -> List[SceneConfig]:
        """按类型获取场景"""
        return [
            s for s in self._custom_scenes.values()
            if s.scene_type == scene_type
        ]
    
    def update_scene(self, scene_id: str, updates: Dict[str, Any]) -> bool:
        """更新场景"""
        scene = self.get_scene(scene_id)
        if not scene:
            return False
        
        for key, value in updates.items():
            if hasattr(scene, key):
                setattr(scene, key, value)
        
        self._save_scene(scene)
        return True
    
    def delete_scene(self, scene_id: str) -> bool:
        """删除场景"""
        scenes_dir = Path(config().data_dir) / "avatars" / "scenes"
        scene_file = scenes_dir / f"{scene_id}.json"
        
        if scene_file.exists():
            scene_file.unlink()
        
        if scene_id in self._custom_scenes:
            del self._custom_scenes[scene_id]
        
        return True
    
    def get_lighting_preset(self, preset: LightingPreset) -> LightingConfig:
        """获取灯光预设"""
        return self.LIGHTING_PRESETS.get(preset, LightingConfig())
    
    def adapt_avatar_to_scene(
        self,
        avatar_id: str,
        scene_id: str,
        content_type: str = "standard"
    ) -> Dict[str, Any]:
        """将数字人适配到场景"""
        scene = self.get_scene(scene_id)
        if not scene:
            return {}
        
        # 根据内容类型调整
        adjustments = {
            'position': scene.avatar_position,
            'scale': scene.avatar_scale,
            'lighting_adjustments': self._calculate_lighting_adjustments(scene),
            'camera_adjustments': self._calculate_camera_adjustments(scene),
        }
        
        # 特定内容类型的额外调整
        if content_type == "product_highlight":
            adjustments['position'] = (0.25, 0.5)
            adjustments['scale'] = 0.55
        elif content_type == "close_interaction":
            adjustments['scale'] = 0.9
            adjustments['camera_adjustments']['focal_length'] = 85.0
        
        return adjustments
    
    def _calculate_lighting_adjustments(self, scene: SceneConfig) -> Dict[str, Any]:
        """计算灯光调整"""
        config = scene.lighting_config
        
        return {
            'key_light': {
                'intensity': config.key_light_intensity,
                'angle': config.key_light_angle,
                'color': config.key_light_color,
            },
            'fill_light': {
                'intensity': config.fill_light_intensity,
                'angle': config.fill_light_angle,
                'color': config.fill_light_color,
            },
            'back_light': {
                'intensity': config.back_light_intensity,
                'angle': config.back_light_angle,
                'color': config.back_light_color,
            },
            'ambient': {
                'intensity': config.ambient_intensity,
                'color': config.ambient_color,
            },
        }
    
    def _calculate_camera_adjustments(self, scene: SceneConfig) -> Dict[str, Any]:
        """计算相机调整"""
        config = scene.camera_config
        
        # 根据距离计算位置
        distance_map = {
            'close': 1.5,
            'medium': 2.5,
            'wide': 4.0,
        }
        
        return {
            'angle': config.angle.value,
            'distance': distance_map.get(config.distance, 2.5),
            'height': config.height,
            'focal_length': config.focal_length,
            'aperture': config.aperture,
        }
    
    def suggest_scene_for_content(
        self,
        content_description: str,
        target_platform: Optional[str] = None
    ) -> List[SceneType]:
        """为内容推荐场景"""
        suggestions = []
        
        # 关键词匹配
        keywords = {
            SceneType.PRODUCT_SHOWCASE: ['产品', '展示', '介绍', '功能', '特点'],
            SceneType.LIVE_STREAMING: ['直播', '带货', '秒杀', '优惠', '下单'],
            SceneType.NEWS_BROADCAST: ['新闻', '播报', '资讯', '报告', '公告'],
            SceneType.EDUCATIONAL: ['教程', '教学', '课程', '学习', '知识'],
            SceneType.CORPORATE: ['企业', '品牌', '文化', '理念', '愿景'],
            SceneType.ENTERTAINMENT: ['娱乐', '搞笑', '趣味', '挑战', '互动'],
            SceneType.SOCIAL_MEDIA: ['日常', '分享', '生活', 'vlog', '朋友圈'],
            SceneType.E_COMMERCE: ['电商', '购物', '商品', '店铺', '销量'],
        }
        
        scores = {}
        for scene_type, words in keywords.items():
            score = sum(1 for word in words if word in content_description)
            if score > 0:
                scores[scene_type] = score
        
        # 按平台调整
        if target_platform:
            platform_preferences = {
                'douyin': [SceneType.ENTERTAINMENT, SceneType.LIVE_STREAMING],
                'xiaohongshu': [SceneType.SOCIAL_MEDIA, SceneType.PRODUCT_SHOWCASE],
                'kuaishou': [SceneType.LIVE_STREAMING, SceneType.ENTERTAINMENT],
                'bilibili': [SceneType.EDUCATIONAL, SceneType.ENTERTAINMENT],
            }
            
            if target_platform in platform_preferences:
                for pref in platform_preferences[target_platform]:
                    scores[pref] = scores.get(pref, 0) + 2
        
        # 排序返回
        sorted_scenes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [scene_type for scene_type, _ in sorted_scenes[:3]]
    
    def _dict_to_scene(self, data: Dict[str, Any]) -> SceneConfig:
        """字典转场景配置"""
        return SceneConfig(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            scene_type=SceneType(data.get('scene_type', 'product_showcase')),
            background_type=BackgroundType(data.get('background_type', 'studio')),
            background_path=data.get('background_path'),
            background_color=data.get('background_color', '#1a1a2e'),
            lighting_preset=LightingPreset(data.get('lighting_preset', 'standard')),
            camera_config=CameraConfig(
                angle=CameraAngle(data.get('camera_angle', 'front')),
                distance=data.get('camera_distance', 'medium'),
            ),
            avatar_position=tuple(data.get('avatar_position', [0.5, 0.5])),
            avatar_scale=data.get('avatar_scale', 0.75),
            props=data.get('props', []),
            effects=data.get('effects', []),
            created_at=data.get('created_at', __import__('datetime').datetime.now().isoformat()),
            owner_id=data.get('owner_id'),
        )
    
    def export_scene_config(self, scene_id: str, output_path: str) -> bool:
        """导出场景配置"""
        scene = self.get_scene(scene_id)
        if not scene:
            return False
        
        try:
            data = {
                'id': scene.id,
                'name': scene.name,
                'description': scene.description,
                'scene_type': scene.scene_type.value,
                'background_type': scene.background_type.value,
                'background_color': scene.background_color,
                'lighting_preset': scene.lighting_preset.value,
                'avatar_position': scene.avatar_position,
                'avatar_scale': scene.avatar_scale,
                'props': scene.props,
                'effects': scene.effects,
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Failed to export scene: {e}")
            return False
