# 🎬 ACAS Pro 视频剪辑 Agent

**不懂 FFmpeg？没关系！** 用自然语言告诉 Agent 你想做什么，它自动帮你搞定。

---

## 📦 安装 FFmpeg（只需一次）

### 方法一：自动安装（推荐）
双击运行 `install_ffmpeg.bat`，等待下载完成即可。

### 方法二：手动安装
1. 访问 https://www.gyan.dev/ffmpeg/builds/
2. 下载 `ffmpeg-release-full.7z`
3. 解压到 `C:\ffmpeg`
4. 将 `C:\ffmpeg\bin` 添加到系统 PATH

---

## 🚀 启动视频剪辑 Agent

```bash
python video_agent.py
```

---

## 📝 支持的命令

### 1️⃣ 合并视频
```
合并 video1.mp4 video2.mp4 video3.mp4
把 intro.mp4 和 main.mp4 合并
合并 *.mp4
```

### 2️⃣ 截取片段
```
截取 video.mp4 从 00:01:30 到 00:02:00
截取 video.mp4 从 1m30s 持续 30s
截取 video.mp4 开头 10 秒
```

### 3️⃣ 添加背景音乐
```
给 video.mp4 添加 bgm.mp3
给 video.mp4 添加背景音乐 music.mp3 音量 0.5
```

### 4️⃣ 压缩视频
```
压缩 video.mp4 到 10MB
压缩 video.mp4
```

### 5️⃣ 提取音频
```
提取 video.mp4 的音频
把 video.mp4 转成 mp3
```

### 6️⃣ 添加字幕
```
给 video.mp4 添加字幕 subtitle.srt
```

### 7️⃣ 调整分辨率
```
把 video.mp4 改成 1920x1080
把 video.mp4 宽度改成 720
```

### 8️⃣ 调整播放速度
```
把 video.mp4 加速到 2 倍
把 video.mp4 慢放到 0.5 倍
```

---

## 💡 使用示例

### 场景 1：制作短视频
```
📝 输入命令 > 截取 raw.mp4 从 00:02:15 持续 15s
📝 输入命令 > 给 trimmed.mp4 添加背景音乐 bgm.mp3 音量 0.3
📝 输入命令 > 压缩 with_bgm.mp4 到 5MB
```

### 场景 2：合并多个素材
```
📝 输入命令 > 合并 intro.mp4 content.mp4 outro.mp4
```

### 场景 3：提取音频做播客
```
📝 输入命令 > 提取 interview.mp4 的音频
```

---

## 📂 输出文件

所有处理后的视频保存在 `output/` 目录，文件名包含时间戳，例如：
- `merged_20250502_143022.mp4`
- `trimmed_20250502_143156.mp4`

---

## ⚠️ 注意事项

1. **视频文件路径**：可以直接拖文件到命令行，自动获取完整路径
2. **时间格式**：支持 `00:01:30`、`1m30s`、`90s` 等多种格式
3. **中文路径**：支持中文文件名和路径
4. **输出目录**：所有结果保存在 `output/` 文件夹

---

## 🔧 故障排除

### "未找到 FFmpeg"
运行 `install_ffmpeg.bat` 安装，或手动安装后重新打开终端。

### "文件不存在"
确保视频文件路径正确，可以用引号包裹含空格的路径。

### 其他问题
查看 `output/` 目录下的错误日志，或检查 FFmpeg 是否正常工作：
```bash
ffmpeg -version
```
