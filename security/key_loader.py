#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量密钥加载器 - 从 .keys/ 目录读取密钥注入 os.environ

版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
"""

import os
import re
from pathlib import Path
from typing import List


def load_keys_to_env(project_dir: str = None) -> List[str]:
    """
    从 .keys/ 目录加载密钥到环境变量
    
    替换 .env 中 ${KEYS_DIR}/.keys/X.key 格式的引用为实际密钥值
    
    Args:
        project_dir: 项目根目录，默认为当前文件的上上级目录
    
    Returns:
        已加载的密钥名称列表
    """
    if project_dir is None:
        project_dir = str(Path(__file__).parent.parent)
    
    keys_dir = Path(project_dir) / '.keys'
    loaded = []
    
    if not keys_dir.exists():
        return loaded
    
    # Scan all .key files
    for key_file in keys_dir.glob('*.key'):
        key_name = key_file.stem
        try:
            with open(key_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            # Format: version:created_at:expires_at:key_value
            # expires_at may be empty, creating '::' separator
            # Find '::' to locate start of key_value
            double_colon = content.find('::')
            if double_colon >= 0:
                key_value = content[double_colon + 2:]  # after '::'
            elif content[0].isdigit():
                # Has expires_at: find ':' after it
                # Pattern: version:created_at:expires_at:key
                # expires_at ends with +HH:MM or Z, then ':' then key
                m = re.search(r'(\+\d{2}:\d{2}|Z):', content)
                if m:
                    key_value = content[m.end():]
                else:
                    key_value = content  # fallback: entire content
            else:
                key_value = content
            
            # Set environment variable
            if key_value:
                os.environ[key_name] = key_value
                loaded.append(key_name)
        except Exception as e:
            print(f"[key_loader] Warning: failed to load {key_name}: {e}")
    
    # Also resolve ${KEYS_DIR} references in .env
    env_path = Path(project_dir) / '.env'
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                # Resolve ${KEYS_DIR}/.keys/X.key references
                if '${KEYS_DIR}' in value:
                    # The key was already loaded above, just set it
                    if key in os.environ:
                        continue  # Already set from .keys dir
        
    return loaded


if __name__ == '__main__':
    loaded = load_keys_to_env()
    print(f"Loaded keys: {loaded}")
    for k in loaded:
        v = os.environ.get(k, '')
        print(f"  {k}: {v[:20]}... ({len(v)} chars)")