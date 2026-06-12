# 修复：消除 PytestUnhandledThreadExceptionWarning (2处)

## 问题
`pytest -W error::pytest.PytestUnhandledThreadExceptionWarning` 失败，产生两台来源的守护线程未处理异常：

### 1. `trend_monitor.py` — `test_monitor_start_stop`
- **根因**: `_monitor_loop` 用 `time.sleep(10)` + `while self._running` 轮询，`stop_monitoring()` 调用 `join(timeout=5)`，但线程可能在 sleep 中，最多等10秒才退出
- **修复**: 引入 `self._stop_event = threading.Event()`
  - `start_monitoring()` → `self._stop_event.clear()`
  - `stop_monitoring()` → `self._stop_event.set()` 立即唤醒
  - `_monitor_loop` → `while not self._stop_event.is_set()` + `self._stop_event.wait(10)` 替代 `time.sleep(10)`
- **效果**: 测试从 5.17s → 0.14s，线程立即响应停止信号

### 2. `agent_engine.py:160` — 守护线程中的 `AttributeError`
- **根因**: `LLMClient.chat()` 返回 None 时，`total_tokens` 有 guard 但后续 `response.content` 和 `response.tool_calls` 没有
- **修复**: 
  - 将 `if response is not None:` 改为 `if response is None: break`（提前退出循环）
  - 添加 logger import (`from ..core.logging import get_logger`)

## 最终结果
```
2126 passed in 28.13s
0 warnings
```
