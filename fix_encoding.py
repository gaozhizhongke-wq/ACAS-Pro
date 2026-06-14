#!/usr/bin/env python3
"""Fix encoding issues in ecommerce source files."""
import os, sys

for fname in ['taobao_shop_api.py', 'kuaishou_shop_api.py',
             'xiaohongshu_shop_api.py', 'douyin_shop_api.py']:
    path = os.path.join('src', 'acas_pro', 'ecommerce', fname)
    if not os.path.exists(path):
        print(f"SKIP: {path} not found")
        continue
    
    data = open(path, 'rb').read()
    lines = data.split(b'\n')
    
    # Check if first line has BOM or other issues
    print(f"\n=== {fname} ===")
    print(f"line 1: {repr(lines[0])}")
    print(f"line 2: {repr(lines[1])}")
    print(f"line 3: {repr(lines[2][:80])}")
    print(f"line 4: {repr(lines[3][:80])}")
    print(f"line 5: {repr(lines[4][:80])}")
    
    # Try decoding each line individually
    for i, line in enumerate(lines[:10]):
        try:
            decoded = line.decode('utf-8')
        except UnicodeDecodeError:
            print(f"  line {i+1}: DECODE ERROR - {repr(line[:50])}")
        else:
            pass  # ok
    
    # Check if the file has valid UTF-8 for its content
    try:
        text = data.decode('utf-8')
        print(f"  File is valid UTF-8")
    except UnicodeDecodeError as e:
        print(f"  UTF-8 ERROR at pos {e.start}: {repr(data[max(0,e.start-5):e.start+5])}")
        # Find bad bytes
        bad_pos = e.start
        bad_bytes = data[bad_pos:bad_pos+5]
        print(f"  Bad bytes: {bad_bytes.hex()} at position {bad_pos}")
        
        # Try to fix by replacing bad bytes
        fixed_data = data[:bad_pos] + b'?' + data[bad_pos+1:]
        try:
            text = fixed_data.decode('utf-8')
            print(f"  Fixed version decodes OK (replaced 1 byte)")
        except UnicodeDecodeError as e2:
            print(f"  Still broken at {e2.start}: {repr(fixed_data[max(0,e2.start-5):e2.start+5])}")