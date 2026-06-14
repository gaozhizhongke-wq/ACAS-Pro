
with open('src/acas_pro/ecommerce/platform_api_base.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add _get_async_client method
old_get_session = '''    def _get_session(self):
        """获取HTTP session（延迟初始化）"""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                "Accept": "application/json",
                "Content-Type": "application/json",
            })
        return self._session'''

new_get_session = '''    def _get_session(self):
        """获取HTTP session（延迟初始化）"""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                "Accept": "application/json",
                "Content-Type": "application/json",
            })
        return self._session

    def _get_async_client(self):
        """获取异步HTTP client（延迟初始化）"""
        if self._async_client is None:
            if not _HAS_HTTPX:
                raise RuntimeError("httpx not installed")
            self._async_client = httpx.AsyncClient(
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=self.REQUEST_TIMEOUT,
            )
        return self._async_client'''

content = content.replace(old_get_session, new_get_session)

# 2. Transform _do_request_async
old_async = '''    async def _do_request_async(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> Dict:
        """执行实际HTTP请求（子方法，子类可覆盖）"""
        import functools
        def _sync():
            return self._do_request(method, endpoint, params, data)
        return await asyncio.to_thread(_sync)'''

new_async = '''    async def _do_request_async(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> Dict:
        """执行实际HTTP请求（异步版本，使用httpx）"""
        if not _HAS_HTTPX:
            raise RuntimeError("httpx not installed")
        
        url = f"{self.API_BASE}{endpoint}"
        client = self._get_async_client()
        
        try:
            if method.upper() == 'GET':
                resp = await client.get(url, params=params)
            else:
                resp = await client.post(url, params=params, json=data)
            
            # 处理HTTP状态码
            if resp.status_code == 401:
                raise AuthError(f"Token expired or invalid: {resp.text[:200]}")
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get('Retry-After', 60))
                raise RateLimitError(retry_after)
            elif resp.status_code >= 500:
                raise APIError(
                    f"SERVER_{resp.status_code}",
                    f"Server error: {resp.text[:200]}"
                )
            elif resp.status_code >= 400:
                raise APIError(
                    f"CLIENT_{resp.status_code}",
                    f"Client error: {resp.text[:200]}"
                )
            
            result = resp.json()
            
            # 子类可覆盖此方法检查业务级错误码
            self._check_business_error(result)
            
            return result
            
        except (APIError, AuthError, RateLimitError):
            raise
        except Exception as e:
            raise APIError("REQUEST_FAILED", f"Async request failed: {e}")'''

content = content.replace(old_async, new_async)

with open('src/acas_pro/ecommerce/platform_api_base.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('OK: platform_api_base.py modified')
