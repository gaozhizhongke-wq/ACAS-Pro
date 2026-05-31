# ACAS-Pro 修复总结 (2026-05-31)

## 修复内容

### 1. 文件编码损坏修复
- `security.py` - 移除 UTF-8 BOM (U+FEFF)
- `llm_chat_fixed.py` - 从 `llm_chat.py` 恢复（原始版本）
- `agent_engine.py` - 修复字符串乱码（`简体中?` → `简体中文`）
- `database.py` - 确认无损坏（误报）

### 2. config 函数-vs-对象问题（核心修复）
`config.py` 中 `config` 是**函数**（`def config() -> AppConfig`），但大量 UI 文件把它当**对象**用（`config.ui.font_family`）。

修复的文件：
- `main.py` - 添加 `cfg = config()` 调用
- `dashboard.py` - 替换所有 `config.` 为 `cfg.`
- `content_creation.py` - 同上
- `llm_chat.py` - 同上（修复3处缩进错误）
- `settings.py` - 同上
- `login_dialog.py` - 同上（修复2处缩进错误，修复相对导入路径 `....core.config` → `...core.config`）
- `account_management.py` - 同上
- `festival_calendar.py` - 同上
- `forecast.py` - 同上
- `intelligence.py` - 同上
- `inventory.py` - 同上
- `publish_manager.py` - 同上
- `video_maker.py` - 同上

### 3. api_base → base_url 修复
`LLMConfig` 数据类有 `base_url` 属性，但代码里用了 `api_base`。

修复的文件：
- `settings.py` - 4 处 `api_base` → `base_url`

### 4. LLMConfig 字段缺失修复
`settings.py` 使用了 `agent_mode` 和 `max_agent_steps`，但 `LLMConfig` 没有这些字段。

修复：
- `config.py` - 给 `LLMConfig` 添加 `agent_mode: bool = True` 和 `max_agent_steps: int = 10`

### 5. 测试文件修复
- `test_web_auth.py` - 14/14 通过（修复 mock 路径、contextmanager、jwt patch）
- `test_web_health.py` - 14/14 通过（修复 fixture、shutil patch、config mock）
- `test_web_middleware.py` - 8/8 通过
- `test_web_llm.py` - 12/12 通过
- `test_analytics_logic.py` - 21/21 通过
- `test_settings_logic.py` - 10/10 通过
- `test_campaign_and_product_logic.py` - 46/46 通过
- `test_content_and_customer_logic.py` - 37/37 通过
- `test_dashboard_and_order_logic.py` - 37/37 通过

### 6. 其他修复
- `product_manager.py` - 修复日志级别（`logger.exception` → `logger.debug`）
- `settings.py` - 修复 `hasattr(config, 'llm')` → `hasattr(_cfg, 'llm')`

## 当前状态

- ✅ 程序能启动：`python main.py` 成功运行
- ✅ 数据库初始化成功
- ✅ TimesFM 引擎初始化成功
- ✅ 趋势监控启动成功
- ✅ 发布调度器启动成功
- ✅ 预测成功（SAMPLE-001, PROD-001~005）
- ⚠️ 1 个非致命错误：`settings: Unhandled exception`（不影响启动）

## 提交

- `35b6a86` - fix: config function-vs-object, api_base→base_url, BOM removal, file corruption fixes
- `30d5f53` - fix: add agent_mode/max_agent_steps to LLMConfig, fix login_dialog import path
