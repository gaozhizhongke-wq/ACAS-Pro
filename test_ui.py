#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI 测试脚本 - 诊断按钮点击问题"""

import os
import sys

# Load .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import Qt

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UI 测试")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        self.label = QLabel("点击按钮测试")
        layout.addWidget(self.label)
        
        # 测试普通按钮
        btn1 = QPushButton("普通按钮")
        btn1.clicked.connect(lambda: self.label.setText("普通按钮被点击"))
        layout.addWidget(btn1)
        
        # 测试 lambda 带参数
        btn2 = QPushButton("Lambda 测试")
        btn2.clicked.connect(lambda checked, x="test": self.on_click(x))
        layout.addWidget(btn2)
        
        # 测试 SidebarButton 样式
        from acas_pro.ui.main_window import SidebarButton
        btn3 = SidebarButton("导航按钮")
        btn3.clicked.connect(lambda: self.label.setText("导航按钮被点击"))
        layout.addWidget(btn3)
        
        layout.addStretch()
    
    def on_click(self, x):
        self.label.setText(f"Lambda 测试: {x}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 测试是否能导入主窗口
    try:
        from acas_pro.ui.main_window import MainWindow, SidebarButton
        print("[OK] MainWindow 导入成功")
    except Exception as e:
        print(f"[FAIL] MainWindow 导入失败: {e}")
    
    # 运行简单测试窗口
    window = TestWindow()
    window.show()
    
    print("UI 测试窗口已启动，点击按钮测试")
    sys.exit(app.exec())
