#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro 视频剪辑 API 服务
提供 HTTP API 供前端调用 FFmpeg

启动: python video_api.py
端口: 5001
"""

import os
import re
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# 配置
UPLOAD_FOLDER = Path("uploads")
OUTPUT_FOLDER = Path("output")
ALLOWED_VIDEO = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
ALLOWED_AUDIO = {'.mp3', '.wav', '.aac', '.m4a', '.flac', '.ogg'}

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)


def find_ffmpeg():
    """查找 FFmpeg 可执行文件"""
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
                return path
        except Exception:
            continue
    return None


FFMPEG_PATH = find_ffmpeg()


def allowed_file(filename, allowed_ext):
    return Path(filename).suffix.lower() in allowed_ext


def parse_time(time_str):
    """解析时间字符串"""
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


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "ffmpeg": FFMPEG_PATH is not None,
        "ffmpeg_path": FFMPEG_PATH
    })


@app.route('/api/video/merge', methods=['POST'])
def merge_videos():
    """合并多个视频"""
    if FFMPEG_PATH is None:
        return jsonify({"error": "FFmpeg not found"}), 500
    
    if 'files' not in request.files:
        return jsonify({"error": "No files provided"}), 400
    
    files = request.files.getlist('files')
    if len(files) < 2:
        return jsonify({"error": "At least 2 files required"}), 400
    
    # 保存上传的文件
    temp_dir = tempfile.mkdtemp()
    video_paths = []
    
    try:
        for file in files:
            if file and allowed_file(file.filename, ALLOWED_VIDEO):
                filename = secure_filename(file.filename)
                filepath = Path(temp_dir) / filename
                file.save(filepath)
                video_paths.append(filepath)
        
        if len(video_paths) < 2:
            return jsonify({"error": "At least 2 valid video files required"}), 400
        
        # 创建 concat 列表
        list_file = Path(temp_dir) / "concat_list.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for video in video_paths:
                abs_path = str(video.absolute()).replace("\\", "/")
                f.write(f"file '{abs_path}'\n")
        
        # 输出文件
        output_name = f"merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        output_path = OUTPUT_FOLDER / output_name
        
        # 执行 FFmpeg
        cmd = [
            FFMPEG_PATH,
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            "-y", str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return jsonify({
                "success": True,
                "filename": output_name,
                "download_url": f"/api/download/{output_name}"
            })
        else:
            return jsonify({"error": result.stderr}), 500
            
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.route('/api/video/trim', methods=['POST'])
def trim_video():
    """截取视频片段"""
    if FFMPEG_PATH is None:
        return jsonify({"error": "FFmpeg not found"}), 500
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    start_time = request.form.get('start', '')
    end_time = request.form.get('end', '')
    duration = request.form.get('duration', '')
    
    if not file or not allowed_file(file.filename, ALLOWED_VIDEO):
        return jsonify({"error": "Invalid video file"}), 400
    
    if not start_time:
        return jsonify({"error": "Start time required"}), 400
    
    # 保存上传文件
    temp_dir = tempfile.mkdtemp()
    
    try:
        filename = secure_filename(file.filename)
        input_path = Path(temp_dir) / filename
        file.save(input_path)
        
        start = parse_time(start_time)
        
        output_name = f"trimmed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        output_path = OUTPUT_FOLDER / output_name
        
        cmd = [FFMPEG_PATH, "-ss", start, "-i", str(input_path)]
        
        if end_time:
            cmd.extend(["-to", parse_time(end_time)])
        elif duration:
            cmd.extend(["-t", parse_time(duration)])
        
        cmd.extend(["-c", "copy", "-y", str(output_path)])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return jsonify({
                "success": True,
                "filename": output_name,
                "download_url": f"/api/download/{output_name}"
            })
        else:
            return jsonify({"error": result.stderr}), 500
            
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.route('/api/video/bgm', methods=['POST'])
def add_bgm():
    """添加背景音乐"""
    if FFMPEG_PATH is None:
        return jsonify({"error": "FFmpeg not found"}), 500
    
    if 'video' not in request.files or 'audio' not in request.files:
        return jsonify({"error": "Video and audio files required"}), 400
    
    video_file = request.files['video']
    audio_file = request.files['audio']
    volume = float(request.form.get('volume', '0.3'))
    
    if not allowed_file(video_file.filename, ALLOWED_VIDEO):
        return jsonify({"error": "Invalid video file"}), 400
    
    if not allowed_file(audio_file.filename, ALLOWED_AUDIO):
        return jsonify({"error": "Invalid audio file"}), 400
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        video_path = Path(temp_dir) / secure_filename(video_file.filename)
        audio_path = Path(temp_dir) / secure_filename(audio_file.filename)
        video_file.save(video_path)
        audio_file.save(audio_path)
        
        output_name = f"with_bgm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        output_path = OUTPUT_FOLDER / output_name
        
        # 循环音频并混合
        filter_complex = f"[1:a]aloop=loop=-1:size=0,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume={volume}[a];[0:a][a]amix=inputs=2:duration=first"
        
        cmd = [
            FFMPEG_PATH,
            "-i", str(video_path),
            "-i", str(audio_path),
            "-filter_complex", filter_complex,
            "-c:v", "copy",
            "-y", str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return jsonify({
                "success": True,
                "filename": output_name,
                "download_url": f"/api/download/{output_name}"
            })
        else:
            return jsonify({"error": result.stderr}), 500
            
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.route('/api/video/compress', methods=['POST'])
def compress_video():
    """压缩视频"""
    if FFMPEG_PATH is None:
        return jsonify({"error": "FFmpeg not found"}), 500
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    mode = request.form.get('mode', 'target')
    target_size = request.form.get('target_size', '')
    crf = request.form.get('crf', '23')
    
    if not allowed_file(file.filename, ALLOWED_VIDEO):
        return jsonify({"error": "Invalid video file"}), 400
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        filename = secure_filename(file.filename)
        input_path = Path(temp_dir) / filename
        file.save(input_path)
        
        output_name = f"compressed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        output_path = OUTPUT_FOLDER / output_name
        
        if mode == 'target' and target_size:
            # 根据目标大小计算码率
            probe_cmd = [FFMPEG_PATH, "-i", str(input_path)]
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
            
            duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})", probe_result.stderr)
            if duration_match:
                h, m, s = map(int, duration_match.groups())
                duration_sec = h * 3600 + m * 60 + s
                target_bits = (float(target_size) * 8 * 1024 * 1024) / duration_sec - 128000
                target_kbits = max(int(target_bits / 1000), 500)
                
                cmd = [
                    FFMPEG_PATH, "-i", str(input_path),
                    "-c:v", "libx264",
                    "-b:v", f"{target_kbits}k",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-y", str(output_path)
                ]
            else:
                cmd = [
                    FFMPEG_PATH, "-i", str(input_path),
                    "-c:v", "libx264",
                    "-crf", str(crf),
                    "-preset", "medium",
                    "-y", str(output_path)
                ]
        else:
            cmd = [
                FFMPEG_PATH, "-i", str(input_path),
                "-c:v", "libx264",
                "-crf", str(crf),
                "-preset", "medium",
                "-c:a", "aac",
                "-b:a", "128k",
                "-y", str(output_path)
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            original_size = input_path.stat().st_size
            compressed_size = output_path.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100
            
            return jsonify({
                "success": True,
                "filename": output_name,
                "download_url": f"/api/download/{output_name}",
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": round(ratio, 2)
            })
        else:
            return jsonify({"error": result.stderr}), 500
            
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """下载处理后的文件"""
    file_path = OUTPUT_FOLDER / filename
    if file_path.exists():
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404


@app.route('/api/files', methods=['GET'])
def list_files():
    """列出所有输出文件"""
    files = []
    for f in OUTPUT_FOLDER.iterdir():
        if f.is_file():
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
    return jsonify(files)


if __name__ == '__main__':
    print("=" * 50)
    print("ACAS Pro 视频剪辑 API 服务")
    print("=" * 50)
    
    if FFMPEG_PATH is None:
        print("⚠️ 警告: 未找到 FFmpeg，请先安装")
        print("   运行: install_ffmpeg.bat")
    else:
        print(f"✅ FFmpeg: {FFMPEG_PATH}")
    
    print(f"📁 上传目录: {UPLOAD_FOLDER.absolute()}")
    print(f"📁 输出目录: {OUTPUT_FOLDER.absolute()}")
    print("=" * 50)
    print("🚀 服务启动: http://localhost:5001")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5001, debug=False)
