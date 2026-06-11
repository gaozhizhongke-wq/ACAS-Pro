# ACAS-Pro TODO 实施计划

生成时间: 2026-06-11 09:15 GMT+8

---

## P0 高优先级（核心功能阻塞）

### 1. 视频渲染逻辑 (video_maker.py:445)

**当前状态**: TODO 注释，返回 None

**实施方案**:

```python
# 安装依赖
pip install moviepy ffmpeg-python

# 实现代码示例
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips

def render_video(self, project: VideoProject) -> str:
    """使用 moviepy 渲染视频"""
    clips = []
    for clip_data in project.clips:
        if clip_data['type'] == 'video':
            clip = VideoFileClip(clip_data['path'])
            clips.append(clip)
        elif clip_data['type'] == 'image':
            clip = ImageClip(clip_data['path']).set_duration(clip_data['duration'])
            clips.append(clip)
    
    # 拼接所有片段
    final_video = concatenate_videoclips(clips)
    
    # 添加背景音乐
    if project.background_music:
        audio = AudioFileClip(project.background_music)
        final_video = final_video.set_audio(audio)
    
    # 导出
    final_video.write_videofile(
        project.output_path,
        fps=project.fps,
        codec='libx264',
        audio_codec='aac'
    )
    
    return project.output_path
```

**依赖**: ffmpeg (需安装到系统 PATH)

---

### 2. TTS 引擎调用 (voice_synthesis.py:140)

**当前状态**: TODO 注释，使用 mock 合成

**实施方案 A - Azure TTS**:

```python
# 安装依赖
pip install azure-cognitiveservices-speech

import azure.cognitiveservices.speech as speechsdk

def synthesize_azure(self, text: str, voice_id: str, output_path: str) -> float:
    """使用 Azure TTS 合成语音"""
    speech_config = speechsdk.SpeechConfig(
        subscription=os.environ['AZURE_SPEECH_KEY'],
        region=os.environ['AZURE_REGION']
    )
    speech_config.speech_synthesis_voice_name = voice_id
    
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config, audio_config)
    
    result = synthesizer.speak_text_async(text).get()
    
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        # 获取时长
        return self._get_audio_duration(output_path)
    else:
        raise RuntimeError(f"TTS failed: {result.reason}")
```

**实施方案 B - 百度语音**:

```python
# 安装依赖
pip install baidu-aip

from aip import AipSpeech

def synthesize_baidu(self, text: str, voice_id: str, output_path: str) -> float:
    """使用百度语音合成"""
    client = AipSpeech(
        app_id=os.environ['BAIDU_APP_ID'],
        api_key=os.environ['BAIDU_API_KEY'],
        secret_key=os.environ['BAIDU_SECRET_KEY']
    )
    
    result = client.synthesis(text, 'zh', 1, {
        'vol': 5,
        'pit': 5,
        'spd': 5,
        'per': voice_id
    })
    
    with open(output_path, 'wb') as f:
        f.write(result)
    
    return self._get_audio_duration(output_path)
```

**需要申请**: Azure Speech / 百度智能云 API 密钥

---

### 3. 平台 API 发布 (publish_manager.py:410)

**当前状态**: TODO 注释，模拟返回成功

**实施方案 - 抖音开放平台**:

```python
# 安装依赖
pip install requests-oauthlib

import requests

class DouyinPublisher:
    API_BASE = "https://developer.toutiao.com"
    
    def publish(self, access_token: str, video_path: str, title: str) -> dict:
        """发布到抖音"""
        # 1. 上传视频
        upload_url = f"{self.API_BASE}/api/apps/v1/video/upload/"
        with open(video_path, 'rb') as f:
            response = requests.post(upload_url, headers={
                'Authorization': f'Bearer {access_token}'
            }, files={'video': f})
        
        video_id = response.json()['data']['video_id']
        
        # 2. 创建作品
        create_url = f"{self.API_BASE}/api/apps/v1/video/create/"
        response = requests.post(create_url, headers={
            'Authorization': f'Bearer {access_token}'
        }, json={
            'video_id': video_id,
            'title': title,
            'publish_type': 1  # 立即发布
        })
        
        return response.json()
```

**需要申请**: 各平台开发者账号和 API 密钥
- 抖音开放平台: https://developer.open-douyin.com
- 快手开放平台: https://open.kuaishou.com
- 视频号: https://developers.weixin.qq.com/doc/channels/
- 小红书: https://open.xiaohongshu.com

---

## P1 中优先级（影响质量）

### 4. 唇形同步模型 (lip_sync.py:146, 164, 332)

**需要集成的模型**:

1. **Wav2Lip** - 音频驱动唇形同步
   ```bash
   git clone https://github.com/Rudrabot/Wav2Lip.git
   pip install torch torchvision opencv-python
   ```

2. **Montreal Forced Aligner** - 语音对齐
   ```bash
   conda install -c conda-forge montreal-forced-aligner
   ```

3. **Blender Python API** - 3D 模型驱动
   ```python
   import bpy
   # 需要安装 Blender 并配置 Python 环境
   ```

### 5. 音频混合逻辑 (voice_synthesis.py:261)

```python
# 安装依赖
pip install pydub

from pydub import AudioSegment

def mix_audio(self, voice_path: str, bgm_path: str, output_path: str, bgm_volume: float = 0.3) -> str:
    """混合语音和背景音乐"""
    voice = AudioSegment.from_file(voice_path)
    bgm = AudioSegment.from_file(bgm_path)
    
    # 调整背景音乐音量
    bgm = bgm - (20 * (1 - bgm_volume))  # 降低音量
    
    # 循环背景音乐以匹配语音时长
    if len(bgm) < len(voice):
        bgm = bgm * (len(voice) // len(bgm) + 1)
    
    # 裁剪到语音时长
    bgm = bgm[:len(voice)]
    
    # 混合
    mixed = voice.overlay(bgm)
    mixed.export(output_path, format='mp3')
    
    return output_path
```

---

## P2 低优先级（优化体验）

### 6. 数字人生成 (avatar_engine.py:411, 582)

**推荐方案**:

1. **SadTalker** - 单图生成说话头像
   ```bash
   git clone https://github.com/OpenTalker/SadTalker.git
   pip install torch torchvision facexlib gfpgan
   ```

2. **DeepFaceLab** - 深度伪造（可选）
   - 需要大量 GPU 资源

### 7. 统计视频时长 (avatar_engine.py:621)

```python
import subprocess

def get_video_duration(video_path: str) -> float:
    """使用 ffprobe 获取视频时长"""
    result = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ], capture_output=True, text=True)
    
    return float(result.stdout.strip())
```

---

## 实施优先级排序

| 序号 | TODO 项 | 文件 | 优先级 | 预估工时 |
|------|---------|------|--------|----------|
| 1 | 视频渲染逻辑 | video_maker.py | P0 | 4h |
| 2 | TTS 引擎调用 | voice_synthesis.py | P0 | 3h |
| 3 | 平台 API 发布 | publish_manager.py | P0 | 8h |
| 4 | 音频混合逻辑 | voice_synthesis.py | P1 | 2h |
| 5 | 唇形同步模型 | lip_sync.py | P1 | 16h |
| 6 | 数字人生成 | avatar_engine.py | P2 | 24h |
| 7 | 视频时长统计 | avatar_engine.py | P2 | 1h |

**总计**: 约 58 工时

---

## 环境准备清单

### 系统依赖
- [ ] ffmpeg (视频/音频处理)
- [ ] Blender (3D 渲染，可选)

### Python 包
- [ ] moviepy
- [ ] ffmpeg-python
- [ ] pydub
- [ ] azure-cognitiveservices-speech
- [ ] baidu-aip
- [ ] torch
- [ ] torchvision

### API 密钥申请
- [ ] Azure Speech Service
- [ ] 百度智能云语音
- [ ] 抖音开放平台
- [ ] 快手开放平台
- [ ] 视频号
- [ ] 小红书

---

*文档生成时间: 2026-06-11 09:15 GMT+8*