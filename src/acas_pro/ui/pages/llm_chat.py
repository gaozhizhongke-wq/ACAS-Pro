#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - LLM Chat Page
AI Chat interface with LLM integration
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QScrollArea, QLabel, QFrame, QSplitter,
    QComboBox, QSpinBox, QCheckBox, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt, Signal, Slot, QThread, QTimer
from PySide6.QtGui import QFont, QColor, QPalette, QTextCursor
import json
import time
from datetime import datetime


class MessageBubble(QFrame):
    """Chat message bubble"""
    
    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.setup_ui(text)
    
    def setup_ui(self, text: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # Role label
        role_label = QLabel("👤 用户" if self.is_user else "🤖 AI")
        role_label.setStyleSheet("font-size: 11px; color: #888;")
        layout.addWidget(role_label)
        
        # Message text
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(text)
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumHeight(300)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: none;
                background: transparent;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.text_edit)
        
        # Bubble style
        if self.is_user:
            self.setStyleSheet("""
                QFrame {
                    background: #E3F2FD;
                    border-radius: 12px;
                    margin: 4px 40px 4px 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background: #F5F5F5;
                    border-radius: 12px;
                    margin: 4px 8px 4px 40px;
                }
            """)
    
    def append_text(self, text: str):
        """Append text to message (for streaming)"""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)


class LLMChatPage(QWidget):
    """LLM Chat interface page"""
    
    message_sent = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._messages = []
        self._llm_client = None
        self._agent_engine = None
        self._conversation_id = None
        self._is_generating = False
        self.setup_ui()
        self._init_llm()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Main chat area
        splitter = QSplitter(Qt.Horizontal)
        
        # Chat panel (left)
        chat_panel = QWidget()
        chat_layout = QVBoxLayout(chat_panel)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        
        # Messages scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setAlignment(Qt.AlignTop)
        self.messages_layout.setSpacing(8)
        
        # Welcome message
        welcome = QLabel("🤖 欢迎使用 ACAS AI 助手！\n\n我可以帮助你：\n• 销售预测和库存优化\n• 市场情报和舆情分析\n• 内容创作和趋势监控\n• 广告投放和电商运营\n• 数据查询和分析\n\n请输入你的问题...")
        welcome.setStyleSheet("padding: 20px; color: #666; font-size: 13px;")
        self.messages_layout.addWidget(welcome)
        self.messages_layout.addStretch()
        
        self.scroll_area.setWidget(self.messages_widget)
        chat_layout.addWidget(self.scroll_area)
        
        # Input area
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background: white;
                border-top: 1px solid #E0E0E0;
            }
        """)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(12, 12, 12, 12)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入消息，按 Enter 发送...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 10px 14px;
                border: 1px solid #E0E0E0;
                border-radius: 20px;
                font-size: 13px;
                background: #FAFAFA;
            }
            QLineEdit:focus {
                border-color: #2196F3;
                background: white;
            }
        """)
        self.input_field.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.input_field)
        
        self.send_btn = QPushButton("发送")
        self.send_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background: #2196F3;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1976D2;
            }
            QPushButton:disabled {
                background: #BDBDBD;
            }
        """)
        self.send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(self.send_btn)
        
        chat_layout.addWidget(input_frame)
        splitter.addWidget(chat_panel)
        
        # Settings panel (right)
        settings_panel = self._create_settings_panel()
        splitter.addWidget(settings_panel)
        
        splitter.setSizes([800, 250])
        layout.addWidget(splitter)
    
    def _create_header(self) -> QWidget:
        """Create header bar"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: white;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        header.setFixedHeight(50)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)
        
        title = QLabel("🤖 AI 助手")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Status indicator
        self.status_label = QLabel("未连接")
        self.status_label.setStyleSheet("color: #999; font-size: 12px;")
        layout.addWidget(self.status_label)
        
        # New chat button
        new_chat_btn = QPushButton("新对话")
        new_chat_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                background: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #EEEEEE;
            }
        """)
        new_chat_btn.clicked.connect(self._new_conversation)
        layout.addWidget(new_chat_btn)
        
        return header
    
    def _create_settings_panel(self) -> QWidget:
        """Create settings panel"""
        panel = QWidget()
        panel.setStyleSheet("background: #FAFAFA;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Model settings
        model_group = QGroupBox("模型设置")
        model_layout = QFormLayout(model_group)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI", "Anthropic", "Kimi", "DeepSeek", "通义千问", "LM Studio", "Ollama", "自定义"])
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        model_layout.addRow("Provider:", self.provider_combo)
        
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self._update_model_list()
        model_layout.addRow("Model:", self.model_combo)
        
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setValue(0.7)
        self.temp_spin.setSingleStep(0.1)
        model_layout.addRow("Temperature:", self.temp_spin)
        
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(256, 32000)
        self.max_tokens_spin.setValue(4096)
        self.max_tokens_spin.setSingleStep(256)
        model_layout.addRow("Max Tokens:", self.max_tokens_spin)
        
        layout.addWidget(model_group)
        
        # Agent settings
        agent_group = QGroupBox("Agent 设置")
        agent_layout = QFormLayout(agent_group)
        
        self.agent_check = QCheckBox("启用 Agent 模式")
        self.agent_check.setChecked(True)
        agent_layout.addRow(self.agent_check)
        
        self.max_steps_spin = QSpinBox()
        self.max_steps_spin.setRange(1, 20)
        self.max_steps_spin.setValue(10)
        agent_layout.addRow("最大步数:", self.max_steps_spin)
        
        layout.addWidget(agent_group)
        
        # Tools info
        tools_group = QGroupBox("可用工具")
        tools_layout = QVBoxLayout(tools_group)
        
        tools_label = QLabel("• 销售预测\n• 库存优化\n• 市场情报\n• 内容创作\n• 趋势监控\n• 账号分析\n• 广告管理\n• 电商运营\n• 数据查询\n• 节日营销")
        tools_label.setStyleSheet("font-size: 11px; color: #666;")
        tools_layout.addWidget(tools_label)
        
        layout.addWidget(tools_group)
        
        layout.addStretch()
        
        # Apply button
        apply_btn = QPushButton("应用设置")
        apply_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #43A047;
            }
        """)
        apply_btn.clicked.connect(self._apply_settings)
        layout.addWidget(apply_btn)
        
        return panel
    
    def _init_llm(self):
        """Initialize LLM client"""
        try:
            from ...llm.llm_client import LLMClient, LLMConfig, LLMProvider
            from ...llm.agent_engine import AgentEngine
            from ...llm.tools import ACASTools
            from ...core.config import config
            
            self._acastools = ACASTools(config=config)
            self.status_label.setText("已就绪")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 12px;")
            
        except Exception as e:
            self.status_label.setText(f"初始化失败: {str(e)}")
            self.status_label.setStyleSheet("color: #F44336; font-size: 12px;")
    
    def _on_provider_changed(self, index: int):
        """Handle provider change"""
        self._update_model_list()
    
    def _update_model_list(self):
        """Update model list based on provider"""
        from ...llm.llm_client import LLMClient, LLMProvider
        
        provider_map = {
            0: LLMProvider.OPENAI,
            1: LLMProvider.ANTHROPIC,
            2: LLMProvider.KIMI,
            3: LLMProvider.DEEPSEEK,
            4: LLMProvider.QWEN,
            5: LLMProvider.LMSTUDIO,
            6: LLMProvider.OLLAMA,
            7: LLMProvider.CUSTOM
        }
        
        provider = provider_map.get(self.provider_combo.currentIndex(), LLMProvider.OPENAI)
        models = LLMClient.list_models(provider)
        
        self.model_combo.clear()
        self.model_combo.addItems(models)
    
    def _send_message(self):
        """Send user message"""
        text = self.input_field.text().strip()
        if not text or self._is_generating:
            return
        
        self.input_field.clear()
        
        # Add user message bubble
        self._add_message(text, is_user=True)
        
        # Generate response
        self._is_generating = True
        self.send_btn.setEnabled(False)
        self.status_label.setText("思考中...")
        self.status_label.setStyleSheet("color: #FF9800; font-size: 12px;")
        
        # Use timer to process in UI thread
        QTimer.singleShot(100, lambda: self._generate_response(text))
    
    def _add_message(self, text: str, is_user: bool = True) -> MessageBubble:
        """Add message to chat"""
        # Remove stretch if present
        item = self.messages_layout.takeAt(self.messages_layout.count() - 1)
        
        bubble = MessageBubble(text, is_user)
        self.messages_layout.addWidget(bubble)
        self._messages.append({"role": "user" if is_user else "assistant", "content": text})
        
        # Add stretch back
        self.messages_layout.addStretch()
        
        # Scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)
        
        return bubble
    
    def _generate_response(self, user_text: str):
        """Generate AI response"""
        try:
            from ...llm.llm_client import LLMClient, LLMConfig, LLMProvider
            from ...llm.agent_engine import AgentEngine, AgentTask
            from ...core.config import config
            import secrets
            
            # Check if LLM is configured
            if not config.llm or not config.llm.api_key:
                response = "⚠️ 请先在设置中配置大模型 API Key。\n\n支持的服务商：\n• OpenAI (需要 API Key)\n• Anthropic Claude (需要 API Key)\n• Kimi 月之暗面 (需要 API Key)\n• DeepSeek (需要 API Key)\n• 通义千问 (需要 API Key)\n• LM Studio (本地运行，免费)\n• Ollama (本地运行，免费)\n\n请前往「系统设置」→「LLM配置」进行设置。"
                self._add_message(response, is_user=False)
            else:
                # Create LLM client
                llm_config = LLMConfig(
                    provider=LLMProvider(config.llm.provider),
                    api_key=config.llm.api_key,
                    api_base=config.llm.api_base,
                    model=config.llm.model or config.llm.get_default_model(),
                    max_tokens=config.llm.max_tokens,
                    temperature=config.llm.temperature
                )
                
                llm_client = LLMClient(llm_config)
                
                # Use Agent mode if enabled
                if config.llm.agent_mode:
                    task = AgentTask(
                        id=f"task_{secrets.token_hex(4)}",
                        prompt=user_text,
                        max_steps=config.llm.max_agent_steps
                    )
                    
                    engine = AgentEngine(llm_client, self._acastools.registry if hasattr(self, '_acastools') else None)
                    result = engine.execute(task)
                    response = result.final_response
                else:
                    # Simple chat
                    messages = [LLMMessage(role="user", content=user_text)]
                    result = llm_client.chat(messages)
                    response = result.content
                
                self._add_message(response, is_user=False)
            
            self.status_label.setText("已就绪")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 12px;")
            
        except Exception as e:
            error_msg = f"❌ 生成失败: {str(e)}"
            self._add_message(error_msg, is_user=False)
            self.status_label.setText("错误")
            self.status_label.setStyleSheet("color: #F44336; font-size: 12px;")
        
        finally:
            self._is_generating = False
            self.send_btn.setEnabled(True)
    
    def _new_conversation(self):
        """Start new conversation"""
        # Clear messages
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._messages.clear()
        
        # Add welcome back
        welcome = QLabel("🤖 新对话已开始，请输入你的问题...")
        welcome.setStyleSheet("padding: 20px; color: #666; font-size: 13px;")
        self.messages_layout.insertWidget(0, welcome)
    
    def _apply_settings(self):
        """Apply LLM settings"""
        try:
            from ...core.config import config
            
            provider_map = ["openai", "anthropic", "kimi", "deepseek", "qwen", "lmstudio", "ollama", "custom"]
            
            config.llm.provider = provider_map[self.provider_combo.currentIndex()]
            config.llm.model = self.model_combo.currentText()
            config.llm.temperature = self.temp_spin.value()
            config.llm.max_tokens = self.max_tokens_spin.value()
            config.llm.agent_mode = self.agent_check.isChecked()
            config.llm.max_agent_steps = self.max_steps_spin.value()
            config.llm.enabled = True
            
            config.save()
            
            self.status_label.setText("设置已保存")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 12px;")
            
        except Exception as e:
            self.status_label.setText(f"保存失败: {str(e)}")
            self.status_label.setStyleSheet("color: #F44336; font-size: 12px;")
    
    def _scroll_to_bottom(self):
        """Scroll to bottom of messages"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


# Fix import
from PySide6.QtWidgets import QDoubleSpinBox
