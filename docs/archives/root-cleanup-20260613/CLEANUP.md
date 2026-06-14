# 废弃文件清理清单

## 已废弃（可安全删除）

| 文件 | 原因 | 替代方案 |
|------|------|----------|
| `start_llm_api.bat` | 配置读取逻辑错误 | `start_service.bat` |
| `llm_api.py` | 错误处理不完善 | `llm_api_v2.py` |
| `start_web.bat` | 功能重复 | `start_static.bat` |
| `start_with_env.ps1` | 过度复杂 | 直接运行 `.bat` |

## 保留但需重构

| 文件 | 问题 | 计划 |
|------|------|------|
| `main.py` | Qt 远程无法运行 | 标记为 deprecated，仅本地使用 |
| `web_app.py` | Flask 完整版 | 与静态版合并或废弃 |

## 执行命令（谨慎操作）

```batch
:: 备份后删除废弃文件
mkdir backup_deprecated
move start_llm_api.bat backup_deprecated\
move llm_api.py backup_deprecated\
move start_web.bat backup_deprecated\
move start_with_env.ps1 backup_deprecated\
```

## 新架构

```
ACAS-Pro/
├── start_service.bat      # 启动 LLM API 服务
├── start_static.bat       # 启动静态 Web 界面
├── llm_api_v2.py          # 新 API 服务
├── config.py              # 统一配置管理
├── .env                   # 配置文件
└── web_static/
    └── index.html         # 单页应用
```
