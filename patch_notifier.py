import re

with open('src/acas_pro/alert/notifier.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add httpx import
old_imports = '''try:
    import requests
except ImportError:
    from unittest.mock import MagicMock
    requests = MagicMock()'''

new_imports = '''try:
    import requests
except ImportError:
    from unittest.mock import MagicMock
    requests = MagicMock()

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False'''

content = content.replace(old_imports, new_imports)

# 2. Add async webhook method
old_webhook = '''    def _send_webhook(self, msg: AlertMessage, url: Optional[str] = None) -> bool:
        hook_url = url or getattr(self, 'webhook_url', None)
        if hook_url:
            try:
                resp = requests.post(
                    hook_url,
                    json=msg.to_dict(),
                    timeout=10,
                )
                return resp.status_code == 200
            except Exception:
                return False
        return False'''

new_webhook = '''    def _send_webhook(self, msg: AlertMessage, url: Optional[str] = None) -> bool:
        hook_url = url or getattr(self, 'webhook_url', None)
        if hook_url:
            try:
                resp = requests.post(
                    hook_url,
                    json=msg.to_dict(),
                    timeout=10,
                )
                return resp.status_code == 200
            except Exception:
                return False
        return False

    async def _send_webhook_async(self, msg: AlertMessage, url: Optional[str] = None) -> bool:
        """异步发送webhook通知"""
        if not _HAS_HTTPX:
            return False
        hook_url = url or getattr(self, 'webhook_url', None)
        if hook_url:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        hook_url,
                        json=msg.to_dict(),
                    )
                    return resp.status_code == 200
            except Exception:
                return False
        return False'''

content = content.replace(old_webhook, new_webhook)

# 3. Transform send_async
old_send_async = '''    async def send_async(self, message: 'AlertMessage',
                        channels: list = None,
                        force: bool = False):
        """异步发送告警通知"""
        if channels is None:
            channels = self._select_channels(message.priority)
        return await asyncio.to_thread(self.send, message, channels, force)'''

new_send_async = '''    async def send_async(self, message: 'AlertMessage',
                        channels: list = None,
                        force: bool = False):
        """异步发送告警通知（webhook使用httpx，其他使用to_thread）"""
        if channels is None:
            channels = self._select_channels(message.priority)
        
        results: Dict[AlertChannel, bool] = {}
        for ch in channels:
            if not force and not self.enabled_channels.get(ch, False):
                results[ch] = False
                continue
            try:
                # Webhook使用真正的异步
                if ch == AlertChannel.WEBHOOK and _HAS_HTTPX:
                    ok = await self._send_webhook_async(message)
                    results[ch] = ok
                else:
                    # 其他channel使用to_thread
                    handler = self._get_handler(ch)
                    if handler:
                        ok = await asyncio.to_thread(handler, message)
                        results[ch] = bool(ok)
                    else:
                        results[ch] = False
            except Exception:
                results[ch] = False
        
        self._record_alert(message, results)
        return results'''

content = content.replace(old_send_async, new_send_async)

with open('src/acas_pro/alert/notifier.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('OK: notifier.py modified')
