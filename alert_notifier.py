#!/usr/bin/env python3
"""ACAS Pro - 告警通知发送器
支持: 飞书/钉钉/企业微信 Webhook
"""
import json
import hmac
import hashlib
import base64
import time
import requests
from datetime import datetime
from typing import Optional

class AlertNotifier:
    """统一告警通知接口"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json; charset=utf-8"
        })
    
    # ============================================
    # 飞书机器人
    # ============================================
    def send_feishu(self, webhook_url: str, secret: Optional[str], 
                    title: str, content: str, is_error: bool = False) -> bool:
        """发送飞书消息"""
        timestamp = str(int(time.time()))
        
        # 签名计算
        if secret:
            string_to_sign = f"{timestamp}\n{secret}"
            hmac_code = hmac.new(
                secret.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            sign = base64.b64encode(hmac_code).decode('utf-8')
        else:
            sign = ""
        
        # 颜色
        color = "red" if is_error else "blue"
        
        payload = {
            "timestamp": timestamp,
            "sign": sign,
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": f"🚨 {title}"},
                    "template": color
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": content}
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {"tag": "plain_text", "content": f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                        ]
                    }
                ]
            }
        }
        
        try:
            resp = self.session.post(webhook_url, json=payload, timeout=10)
            return resp.json().get("code") == 0
        except Exception as e:
            print(f"飞书发送失败: {e}")
            return False
    
    # ============================================
    # 钉钉机器人
    # ============================================
    def send_dingtalk(self, webhook_url: str, secret: Optional[str],
                      title: str, content: str, is_error: bool = False) -> bool:
        """发送钉钉消息"""
        timestamp = str(round(time.time() * 1000))
        
        if secret:
            string_to_sign = f"{timestamp}\n{secret}"
            hmac_code = hmac.new(
                secret.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            sign = requests.utils.quote(base64.b64encode(hmac_code))
            webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
        
        emoji = "🔴" if is_error else "🔵"
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"{emoji} **{title}**\n\n{content}\n\n---\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }
        
        try:
            resp = self.session.post(webhook_url, json=payload, timeout=10)
            return resp.json().get("errcode") == 0
        except Exception as e:
            print(f"钉钉发送失败: {e}")
            return False
    
    # ============================================
    # 企业微信
    # ============================================
    def send_wecom(self, webhook_url: str, title: str, 
                   content: str, is_error: bool = False) -> bool:
        """发送企业微信消息"""
        emoji = "🚨" if is_error else "ℹ️"
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"{emoji} **{title}**\n>{content.replace(chr(10), chr(10)+'>')}\n\n<font color=\"info\">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</font>"
            }
        }
        
        try:
            resp = self.session.post(webhook_url, json=payload, timeout=10)
            return resp.json().get("errcode") == 0
        except Exception as e:
            print(f"企业微信发送失败: {e}")
            return False
    
    # ============================================
    # 统一接口
    # ============================================
    def send(self, platform: str, webhook_url: str, secret: Optional[str],
             title: str, content: str, is_error: bool = False) -> bool:
        """统一发送接口"""
        handlers = {
            "feishu": self.send_feishu,
            "dingtalk": self.send_dingtalk,
            "wecom": self.send_wecom
        }
        
        handler = handlers.get(platform)
        if not handler:
            raise ValueError(f"不支持的平台: {platform}")
        
        if platform == "wecom":
            return handler(webhook_url, title, content, is_error)
        return handler(webhook_url, secret, title, content, is_error)


# ============================================
# CLI 入口
# ============================================
if __name__ == "__main__":
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="ACAS Pro 告警通知")
    parser.add_argument("--platform", choices=["feishu", "dingtalk", "wecom"], required=True)
    parser.add_argument("--url", required=True, help="Webhook URL")
    parser.add_argument("--secret", help="签名密钥")
    parser.add_argument("--title", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--error", action="store_true", help="错误级别")
    
    args = parser.parse_args()
    
    notifier = AlertNotifier()
    ok = notifier.send(
        args.platform, args.url, args.secret,
        args.title, args.content, args.error
    )
    
    print("发送成功" if ok else "发送失败")
    exit(0 if ok else 1)
