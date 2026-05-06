#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro 视频剪辑 Agent
自动执行 FFmpeg 命令，无需懂技术

用法:
    python video_agent.py

然后按提示输入命令，例如:
    - "把 video1.mp4 和 video2.mp4 合并"
    - "截取 video.mp4 从 00:01:30 到 00:02:00"
    - "给 video.mp4 添加背景音乐 bgm.mp3"
    - "把 video.mp4 压缩到 10MB 以内"
"""

import os
import sys
import re
import subprocess
import glob
from pathlib import Path
from datetime import datetime

class VideoAgent:
    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
    def _find_ffmpeg(self):
        """查找 FFmpeg 可执行文件"""
        # 常见安装路径
        possible_paths = [
            "ffmpeg",
            "ffmpeg.exe",
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            os.path.expanduser(r"~\ffmpeg\bin\ffmpeg.exe"),
            os.path.expanduser(r"~\scoop\shims\ffmpeg.exe"),
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, "-version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"✅ 找到 FFmpeg: {path}")
                    return path
            except:
                continue
        
        print("❌ 未找到 FFmpeg")
        print("请从 https://www.gyan.dev/ffmpeg/builds/ 下载并解压到 C:\ffmpeg")
        print("或将 ffmpeg.exe 所在目录添加到系统 PATH")
        sys.exit(1)
    
    def _run_ffmpeg(self, args, description="执行 FFmpeg 命令"):
        """执行 FFmpeg 命令并显示进度"""
        cmd = [self.ffmpeg_path] + args
        print(f"\n🎬 {description}")
        print(f"命令: {' '.join(cmd)}\n")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print(f"✅ 完成!")
                return True
            else:
                print(f"❌ 错误: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print(f"❌ 超时")
            return False
        except Exception as e:
            print(f"❌ 异常: {e}")
            return False
    
    def _generate_output_name(self, prefix="output"):
        """生成输出文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"{prefix}_{timestamp}.mp4"
    
    def _parse_time(self, time_str):
        """解析时间字符串 (支持 00:01:30 或 90s 或 1m30s)"""
        time_str = time_str.strip()
        
        # HH:MM:SS 格式
        if re.match(r"\d+:\d{2}:\d{2}", time_str):
            return time_str
        
        # MM:SS 格式
        if re.match(r"\d{1,2}:\d{2}", time_str):
            parts = time_str.split(":")
            if len(parts) == 2:
                m, s = int(parts[0]), int(parts[1])
                return f"00:{m:02d}:{s:02d}"
        
        # 90s 或 1m30s 格式
        total_seconds = 0
        matches = re.findall(r"(\d+)([hms])", time_str.lower())
        for num, unit in matches:
            if unit == 'h':
                total_seconds += int(num) * 3600
            elif unit == 'm':
                total_seconds += int(num) * 60
            elif unit == 's':
                total_seconds += int(num)
        
        if total_seconds > 0:
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            s = total_seconds % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        
        return time_str
    
    def merge_videos(self, video_files, output=None):
        """合并多个视频"""
        if not video_files:
            print("❌ 请提供视频文件")
            return False
        
        # 展开通配符
        expanded_files = []
        for f in video_files:
            if '*' in f:
                expanded_files.extend(sorted(glob.glob(f)))
            else:
                expanded_files.append(f)
        
        if len(expanded_files) < 2:
            print(f"❌ 至少需要 2 个视频文件，找到 {len(expanded_files)} 个")
            return False
        
        print(f"📁 将合并 {len(expanded_files)} 个视频:")
        for f in expanded_files:
            print(f"   - {f}")
        
        # 创建 concat 列表文件
        list_file = self.output_dir / "concat_list.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for video in expanded_files:
                # 处理中文路径
                abs_path = os.path.abspath(video).replace("\\", "/")
                f.write(f"file '{abs_path}'\n")
        
        output = output or self._generate_output_name("merged")
        
        args = [
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            "-y", str(output)
        ]
        
        success = self._run_ffmpeg(args, "合并视频")
        list_file.unlink(missing_ok=True)
        
        if success:
            print(f"\n📤 输出文件: {output}")
        return success
    
    def trim_video(self, input_file, start_time, end_time=None, duration=None, output=None):
        """截取视频片段"""
        if not os.path.exists(input_file):
            print(f"❌ 文件不存在: {input_file}")
            return False
        
        start = self._parse_time(start_time)
        
        args = ["-ss", start, "-i", input_file]
        
        if end_time:
            end = self._parse_time(end_time)
            # 计算持续时间
            args.extend(["-to", end])
        elif duration:
            dur = self._parse_time(duration)
            args.extend(["-t", dur])
        
        args.extend(["-c", "copy", "-y"])
        
        output = output or self._generate_output_name("trimmed")
        args.append(str(output))
        
        success = self._run_ffmpeg(args, f"截取视频 ({start} 开始)")
        
        if success:
            print(f"\n📤 输出文件: {output}")
        return success
    
    def add_bgm(self, video_file, audio_file, loop=True, volume=0.3, output=None):
        """给视频添加背景音乐"""
        if not os.path.exists(video_file):
            print(f"❌ 视频文件不存在: {video_file}")
            return False
        if not os.path.exists(audio_file):
            print(f"❌ 音频文件不存在: {audio_file}")
            return False
        
        output = output or self._generate_output_name("with_bgm")
        
        if loop:
            # 循环背景音乐以匹配视频长度
            filter_complex = f"[1:a]aloop=loop=-1:size=0,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume={volume}[a];[0:a][a]amix=inputs=2:duration=first"
            args = [
                "-i", video_file,
                "-i", audio_file,
                "-filter_complex", filter_complex,
                "-c:v", "copy",
                "-y", str(output)
            ]
        else:
            # 不循环，只叠加一次
            args = [
                "-i", video_file,
                "-i", audio_file,
                "-filter_complex", f"[0:a][1:a]amix=inputs=2:duration=first,volume=2[a]",
                "-map", "0:v",
                "-map", "[a]",
                "-c:v", "copy",
                "-y", str(output)
            ]
        
        success = self._run_ffmpeg(args, "添加背景音乐")
        
        if success:
            print(f"\n📤 输出文件: {output}")
        return success
    
    def compress_video(self, input_file, target_size_mb=None, crf=23, output=None):
        """压缩视频"""
        if not os.path.exists(input_file):
            print(f"❌ 文件不存在: {input_file}")
            return False
        
        output = output or self._generate_output_name("compressed")
        
        if target_size_mb:
            # 根据目标大小计算码率
            # 获取视频时长
            probe_cmd = [self.ffmpeg_path, "-i", input_file]
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            
            duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})", result.stderr)
            if duration_match:
                h, m, s = map(int, duration_match.groups())
                duration_sec = h * 3600 + m * 60 + s
                
                # 目标码率 (bits per second)，留 128k 给音频
                target_bits = (target_size_mb * 8 * 1024 * 1024) / duration_sec - 128000
                target_kbits = max(int(target_bits / 1000), 500)
                
                print(f"🎯 目标大小: {target_size_mb}MB")
                print(f"⏱️  视频时长: {duration_sec}秒")
                print(f"📊 目标码率: {target_kbits}k")
                
                args = [
                    "-i", input_file,
                    "-c:v", "libx264",
                    "-b:v", f"{target_kbits}k",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-y", str(output)
                ]
            else:
                print("⚠️ 无法获取视频时长，使用 CRF 模式压缩")
                args = [
                    "-i", input_file,
                    "-c:v", "libx264",
                    "-crf", str(crf),
                    "-preset", "medium",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-y", str(output)
                ]
        else:
            # 使用 CRF 模式
            args = [
                "-i", input_file,
                "-c:v", "libx264",
                "-crf", str(crf),
                "-preset", "medium",
                "-c:a", "aac",
                "-b:a", "128k",
                "-y", str(output)
            ]
        
        success = self._run_ffmpeg(args, "压缩视频")
        
        if success:
            # 显示压缩结果
            original_size = os.path.getsize(input_file) / (1024 * 1024)
            compressed_size = os.path.getsize(output) / (1024 * 1024)
            ratio = (1 - compressed_size / original_size) * 100
            print(f"\n📊 压缩结果:")
            print(f"   原大小: {original_size:.2f} MB")
            print(f"   压缩后: {compressed_size:.2f} MB")
            print(f"   压缩率: {ratio:.1f}%")
            print(f"\n📤 输出文件: {output}")
        return success
    
    def extract_audio(self, video_file, output=None, format="mp3"):
        """从视频提取音频"""
        if not os.path.exists(video_file):
            print(f"❌ 文件不存在: {video_file}")
            return False
        
        output = output or self._generate_output_name("audio").with_suffix(f".{format}")
        
        args = [
            "-i", video_file,
            "-vn",  # 不要视频
            "-c:a", "libmp3lame" if format == "mp3" else "aac",
            "-q:a", "2" if format == "mp3" else "128k",
            "-y", str(output)
        ]
        
        success = self._run_ffmpeg(args, "提取音频")
        
        if success:
            print(f"\n📤 输出文件: {output}")
        return success
    
    def add_subtitle(self, video_file, subtitle_file, output=None):
        """给视频添加字幕"""
        if not os.path.exists(video_file):
            print(f"❌ 视频文件不存在: {video_file}")
            return False
        if not os.path.exists(subtitle_file):
            print(f"❌ 字幕文件不存在: {subtitle_file}")
            return False
        
        output = output or self._generate_output_name("subtitled")
        
        # 处理中文字幕编码
        args = [
            "-i", video_file,
            "-vf", f"subtitles={subtitle_file}:force_style='FontName=Microsoft YaHei'",
            "-c:a", "copy",
            "-y", str(output)
        ]
        
        success = self._run_ffmpeg(args, "添加字幕")
        
        if success:
            print(f"\n📤 输出文件: {output}")
        return success
    
    def resize_video(self, input_file, width=None, height=None, output=None):
        """调整视频分辨率"""
        if not os.path.exists(input_file):
            print(f"❌ 文件不存在: {input_file}")
            return False
        
        output = output or self._generate_output_name("resized")
        
        if width and height:
            scale = f"{width}:{height}"
        elif width:
            scale = f"{width}:-2"  # 保持比例
        elif height:
            scale = f"-2:{height}"  # 保持比例
        else:
            print("❌ 请指定宽度或高度")
            return False
        
        args = [
            "-i", input_file,
            "-vf", f"scale={scale}",
            "-c:a", "copy",
            "-y", str(output)
        ]
        
        success = self._run_ffmpeg(args, f"调整分辨率到 {scale}")
        
        if success:
            print(f"\n📤 输出文件: {output}")
        return success
    
    def change_speed(self, input_file, speed=1.0, output=None):
        """改变视频播放速度"""
        if not os.path.exists(input_file):
            print(f"❌ 文件不存在: {input_file}")
            return False
        
        if speed <= 0:
            print("❌ 速度必须大于 0")
            return False
        
        output = output or self._generate_output_name(f"speed_{speed}x")
        
        # setpts 用于视频，atempo 用于音频
        video_filter = f"setpts={1/speed}*PTS"
        
        # atempo 只支持 0.5-2.0，需要链式处理
        audio_tempo = speed
        audio_filters = []
        while audio_tempo > 2.0:
            audio_filters.append("atempo=2.0")
            audio_tempo /= 2.0
        while audio_tempo < 0.5:
            audio_filters.append("atempo=0.5")
            audio_tempo /= 0.5
        audio_filters.append(f"atempo={audio_tempo}")
        audio_filter = ",".join(audio_filters)
        
        args = [
            "-i", input_file,
            "-filter_complex", f"[0:v]{video_filter}[v];[0:a]{audio_filter}[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-y", str(output)
        ]
        
        success = self._run_ffmpeg(args, f"调整速度为 {speed}x")
        
        if success:
            print(f"\n📤 输出文件: {output}")
        return success


def print_help():
    """打印帮助信息"""
    print("""
🎬 ACAS Pro 视频剪辑 Agent
═══════════════════════════════════════

支持的自然语言命令:

1️⃣  合并视频
    "合并 video1.mp4 video2.mp4"
    "把 intro.mp4 和 main.mp4 合并"
    "合并 *.mp4"

2️⃣  截取片段
    "截取 video.mp4 从 00:01:30 到 00:02:00"
    "截取 video.mp4 从 1m30s 持续 30s"
    "截取 video.mp4 开头 10 秒"

3️⃣  添加背景音乐
    "给 video.mp4 添加 bgm.mp3"
    "给 video.mp4 添加背景音乐 music.mp3 音量 0.5"

4️⃣  压缩视频
    "压缩 video.mp4 到 10MB"
    "压缩 video.mp4"

5️⃣  提取音频
    "提取 video.mp4 的音频"
    "把 video.mp4 转成 mp3"

6️⃣  添加字幕
    "给 video.mp4 添加字幕 subtitle.srt"

7️⃣  调整分辨率
    "把 video.mp4 改成 1920x1080"
    "把 video.mp4 宽度改成 720"

8️⃣  调整速度
    "把 video.mp4 加速到 2 倍"
    "把 video.mp4 慢放到 0.5 倍"

其他命令:
    help  - 显示帮助
    quit  - 退出
    exit  - 退出

═══════════════════════════════════════
""")


def parse_command(agent, command):
    """解析自然语言命令"""
    command = command.strip().lower()
    
    if not command:
        return True
    
    if command in ["quit", "exit", "q"]:
        print("👋 再见!")
        return False
    
    if command in ["help", "h", "?"]:
        print_help()
        return True
    
    # 合并视频
    merge_patterns = [
        r"合并\s+(.+)",
        r"把\s+(.+)\s+和\s+(.+)\s+合并",
        r"合并\s+(.+)\s+和\s+(.+)",
    ]
    for pattern in merge_patterns:
        match = re.search(pattern, command)
        if match:
            # 提取所有文件
            files_str = command.replace("合并", "").replace("把", "").replace("和", " ").replace("合并", "")
            files = [f.strip() for f in re.split(r"\s+", files_str) if f.strip() and f.strip() not in ["和", "与", "以及"]]
            # 过滤出可能的文件
            video_files = [f for f in files if any(ext in f.lower() for ext in [".mp4", ".avi", ".mov", ".mkv", "*.mp4", "*.avi", "*.mov"])]
            if video_files:
                agent.merge_videos(video_files)
                return True
    
    # 截取视频
    trim_patterns = [
        r"截取\s+(\S+)\s+从\s+(\S+)\s+到\s+(\S+)",
        r"截取\s+(\S+)\s+从\s+(\S+)\s+持续\s+(\S+)",
        r"截取\s+(\S+)\s+开头\s+(\S+)",
    ]
    for i, pattern in enumerate(trim_patterns):
        match = re.search(pattern, command)
        if match:
            video_file = match.group(1)
            if i == 0:  # 从 X 到 Y
                start, end = match.group(2), match.group(3)
                agent.trim_video(video_file, start, end_time=end)
            elif i == 1:  # 从 X 持续 Y
                start, duration = match.group(2), match.group(3)
                agent.trim_video(video_file, start, duration=duration)
            elif i == 2:  # 开头 X
                duration = match.group(2)
                agent.trim_video(video_file, "0:00", duration=duration)
            return True
    
    # 添加背景音乐
    bgm_patterns = [
        r"给\s+(\S+)\s+添加\s+(\S+)",
        r"给\s+(\S+)\s+添加背景音乐\s+(\S+)",
        r"(.+)\s+添加背景音乐\s+(.+)",
    ]
    for pattern in bgm_patterns:
        match = re.search(pattern, command)
        if match:
            video_file = match.group(1)
            audio_file = match.group(2)
            # 检查是否是音频文件
            if any(ext in audio_file.lower() for ext in [".mp3", ".wav", ".aac", ".m4a"]):
                # 提取音量
                volume_match = re.search(r"音量\s+(\d+\.?\d*)", command)
                volume = float(volume_match.group(1)) if volume_match else 0.3
                agent.add_bgm(video_file, audio_file, volume=volume)
                return True
    
    # 压缩视频
    compress_patterns = [
        r"压缩\s+(\S+)\s+到\s+(\d+)\s*MB",
        r"压缩\s+(\S+)",
    ]
    for i, pattern in enumerate(compress_patterns):
        match = re.search(pattern, command)
        if match:
            video_file = match.group(1)
            target_size = int(match.group(2)) if i == 0 else None
            agent.compress_video(video_file, target_size_mb=target_size)
            return True
    
    # 提取音频
    extract_patterns = [
        r"提取\s+(\S+)\s+的音频",
        r"把\s+(\S+)\s+转成\s+(mp3|wav|aac)",
    ]
    for pattern in extract_patterns:
        match = re.search(pattern, command)
        if match:
            video_file = match.group(1)
            fmt = match.group(2) if match.lastindex >= 2 else "mp3"
            agent.extract_audio(video_file, format=fmt)
            return True
    
    # 添加字幕
    subtitle_patterns = [
        r"给\s+(\S+)\s+添加字幕\s+(\S+)",
    ]
    for pattern in subtitle_patterns:
        match = re.search(pattern, command)
        if match:
            video_file = match.group(1)
            subtitle_file = match.group(2)
            agent.add_subtitle(video_file, subtitle_file)
            return True
    
    # 调整分辨率
    resize_patterns = [
        r"把\s+(\S+)\s+改成\s+(\d+)x(\d+)",
        r"把\s+(\S+)\s+宽度改成\s+(\d+)",
        r"把\s+(\S+)\s+高度改成\s+(\d+)",
    ]
    for i, pattern in enumerate(resize_patterns):
        match = re.search(pattern, command)
        if match:
            video_file = match.group(1)
            if i == 0:
                width, height = int(match.group(2)), int(match.group(3))
                agent.resize_video(video_file, width=width, height=height)
            elif i == 1:
                width = int(match.group(2))
                agent.resize_video(video_file, width=width)
            elif i == 2:
                height = int(match.group(2))
                agent.resize_video(video_file, height=height)
            return True
    
    # 调整速度
    speed_patterns = [
        r"把\s+(\S+)\s+加速到\s+(\d+\.?\d*)\s*倍",
        r"把\s+(\S+)\s+慢放到\s+(\d+\.?\d*)\s*倍",
    ]
    for pattern in speed_patterns:
        match = re.search(pattern, command)
        if match:
            video_file = match.group(1)
            speed = float(match.group(2))
            agent.change_speed(video_file, speed=speed)
            return True
    
    print("❓ 无法理解的命令，输入 help 查看支持的命令")
    return True


def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║           🎬 ACAS Pro 视频剪辑 Agent v1.0                  ║
║                                                          ║
║   用自然语言操作视频，无需懂 FFmpeg 命令                  ║
╚══════════════════════════════════════════════════════════╝
""")
    
    agent = VideoAgent()
    print_help()
    
    while True:
        try:
            command = input("\n📝 输入命令 > ").strip()
            if not parse_command(agent, command):
                break
        except KeyboardInterrupt:
            print("\n👋 再见!")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")


if __name__ == "__main__":
    main()
