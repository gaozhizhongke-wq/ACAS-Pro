# ACAS Pro - 企业级自动获客系统
# 版权所有 (c) 2026 高智中科（北京）科技有限公司

"""
Grafana 仪表板自动配置模块
通过 Grafana API 自动创建/更新仪表板和告警规则
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class GrafanaClient:
    """Grafana API 客户端"""

    def __init__(self, url: str = "http://localhost:3000",
                 api_key: str = None, username: str = "admin",
                 password: str = None):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.username = username
        self.password = password
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    def _request(self, method: str, path: str, data: Dict = None) -> Dict:
        import urllib.request
        import urllib.error

        url = f"{self.url}{path}"
        body = json.dumps(data).encode("utf-8") if data else None

        req = urllib.request.Request(url, data=body, headers=self._headers, method=method)
        if not self.api_key:
            import base64
            cred = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            req.add_header("Authorization", f"Basic {cred}")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            logger.error("Grafana API 错误: %s %s", e.code, e.reason)
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error("Grafana API 异常: %s", e)
            return {"status": "error", "message": str(e)}

    def health(self) -> bool:
        result = self._request("GET", "/api/health")
        return result.get("database") == "ok"

    def create_datasource(self, name: str = "Prometheus",
                          url: str = "http://localhost:9090") -> Dict:
        datasource = {
            "name": name,
            "type": "prometheus",
            "url": url,
            "access": "proxy",
            "isDefault": True
        }
        return self._request("POST", "/api/datasources", datasource)

    def create_dashboard(self, dashboard: Dict, overwrite: bool = True) -> Dict:
        payload = {
            "dashboard": dashboard,
            "overwrite": overwrite
        }
        return self._request("POST", "/api/dashboards/db", payload)

    def get_dashboard(self, uid: str) -> Dict:
        return self._request("GET", f"/api/dashboards/uid/{uid}")

    def create_notification_channel(self, name: str, channel_type: str,
                                    settings: Dict) -> Dict:
        channel = {
            "name": name,
            "type": channel_type,
            "settings": settings,
            "isDefault": False
        }
        return self._request("POST", "/api/alert-notifications", channel)

    def send_test_alert(self, channel_id: int) -> Dict:
        return self._request("POST", f"/api/alert-notifications/{channel_id}/test")


class DashboardBuilder:
    """ACAS Pro 仪表板构建器"""

    def __init__(self):
        self.panels = []
        self._y_pos = 0

    def _add_panel(self, title: str, panel_type: str, targets: List[Dict],
                   grid_h: int = 8, grid_w: int = 12, **kwargs) -> "DashboardBuilder":
        panel = {
            "id": len(self.panels) + 1,
            "title": title,
            "type": panel_type,
            "gridPos": {"h": grid_h, "w": grid_w, "x": 0 if len(self.panels) % 2 == 0 else grid_w,
                        "y": self._y_pos},
            "targets": targets,
            "datasource": "Prometheus",
            "fieldConfig": kwargs.get("fieldConfig", {
                "defaults": {"unit": kwargs.get("unit", "short")},
                "overrides": []
            }),
            "options": kwargs.get("options", {}),
        }
        self.panels.append(panel)
        if len(self.panels) % 2 == 0:
            self._y_pos += grid_h
        return self

    def add_api_request_rate(self) -> "DashboardBuilder":
        return self._add_panel(
            "API 请求速率 (req/s)",
            "timeseries",
            [{"expr": "rate(http_requests_total[5m])", "legendFormat": "{{method}} {{path}}"}],
            unit="reqps"
        )

    def add_api_latency(self) -> "DashboardBuilder":
        return self._add_panel(
            "API 延迟 (P50/P95/P99)",
            "timeseries",
            [
                {"expr": "histogram_quantile(0.5, rate(http_request_duration_seconds_bucket[5m]))", "legendFormat": "P50"},
                {"expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))", "legendFormat": "P95"},
                {"expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))", "legendFormat": "P99"},
            ],
            unit="s"
        )

    def add_error_rate(self) -> "DashboardBuilder":
        return self._add_panel(
            "错误率 (5xx)",
            "timeseries",
            [{"expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])", "legendFormat": "error rate"}],
            unit="percentunit"
        )

    def add_active_users(self) -> "DashboardBuilder":
        return self._add_panel(
            "活跃用户数",
            "stat",
            [{"expr": "acas_active_users", "legendFormat": "当前在线"}],
            grid_h=4, grid_w=6
        )

    def add_content_generation(self) -> "DashboardBuilder":
        return self._add_panel(
            "内容生成量 (24h)",
            "stat",
            [{"expr": "increase(acas_content_generated_total[24h])", "legendFormat": "生成数"}],
            grid_h=4, grid_w=6
        )

    def add_database_connections(self) -> "DashboardBuilder":
        return self._add_panel(
            "数据库连接池",
            "gauge",
            [
                {"expr": "acas_db_connections_active", "legendFormat": "活跃"},
                {"expr": "acas_db_connections_idle", "legendFormat": "空闲"},
            ],
            grid_h=4, grid_w=6
        )

    def add_redis_ops(self) -> "DashboardBuilder":
        return self._add_panel(
            "Redis 操作速率",
            "timeseries",
            [
                {"expr": "rate(redis_commands_processed_total[5m])", "legendFormat": "ops/s"},
                {"expr": "redis_connected_clients", "legendFormat": "clients"},
            ],
            unit="ops"
        )

    def add_system_resources(self) -> "DashboardBuilder":
        return self._add_panel(
            "系统资源使用",
            "timeseries",
            [
                {"expr": "process_cpu_seconds_total", "legendFormat": "CPU"},
                {"expr": "process_resident_memory_bytes / 1024 / 1024", "legendFormat": "Memory (MB)"},
            ],
            unit="short"
        )

    def add_alert_status(self) -> "DashboardBuilder":
        return self._add_panel(
            "告警状态",
            "table",
            [{"expr": "ALERTS", "legendFormat": "{{alertname}}", "instant": True}],
            grid_h=8, grid_w=12
        )

    def build(self, title: str = "ACAS Pro 监控仪表板",
              tags: List[str] = None) -> Dict:
        return {
            "id": None,
            "uid": "acas-pro-dashboard",
            "title": title,
            "tags": tags or ["acas-pro", "monitoring"],
            "timezone": "browser",
            "schemaVersion": 38,
            "version": 0,
            "refresh": "30s",
            "time": {"from": "now-1h", "to": "now"},
            "panels": self.panels,
            "templating": {
                "list": [
                    {
                        "name": "datasource",
                        "type": "datasource",
                        "query": "prometheus",
                        "current": {"text": "Prometheus", "value": "Prometheus"}
                    }
                ]
            },
            "annotations": {
                "list": [
                    {
                        "name": "Deployments",
                        "datasource": "Prometheus",
                        "enable": True,
                        "expr": "acas_deployment_total"
                    }
                ]
            }
        }


def setup_grafana(config: Dict[str, Any] = None) -> Dict[str, Any]:
    """一键配置 Grafana"""
    config = config or {}
    results = {}

    client = GrafanaClient(
        url=config.get("grafana_url", "http://localhost:3000"),
        api_key=config.get("grafana_api_key", ""),
        username=config.get("grafana_user", "admin"),
        password=config.get("grafana_pass", "admin")
    )

    # 1. 检查健康
    if not client.health():
        results["health"] = "Grafana 不可达"
        return results
    results["health"] = "ok"

    # 2. 创建数据源
    ds_result = client.create_datasource()
    results["datasource"] = "ok" if ds_result.get("id") else ds_result.get("message", "failed")

    # 3. 创建仪表板
    builder = DashboardBuilder()
    (builder.add_api_request_rate()
            .add_api_latency()
            .add_error_rate()
            .add_active_users()
            .add_content_generation()
            .add_database_connections()
            .add_redis_ops()
            .add_system_resources()
            .add_alert_status())

    dashboard = builder.build()
    db_result = client.create_dashboard(dashboard)
    results["dashboard"] = "ok" if db_result.get("status") == "success" else db_result.get("message", "failed")

    # 4. 配置通知渠道
    if config.get("dingtalk_url"):
        ch = client.create_notification_channel(
            name="ACAS 钉钉告警",
            channel_type="dingding",
            settings={"url": config["dingtalk_url"]}
        )
        results["dingtalk_channel"] = "ok" if ch.get("id") else "failed"

    if config.get("wechat_url"):
        ch = client.create_notification_channel(
            name="ACAS 企微告警",
            channel_type="wechat",
            settings={"url": config["wechat_url"]}
        )
        results["wechat_channel"] = "ok" if ch.get("id") else "failed"

    return results


def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description="ACAS Pro Grafana 配置")
    parser.add_argument("--grafana-url", default="http://localhost:3000")
    parser.add_argument("--grafana-user", default="admin")
    parser.add_argument("--grafana-pass", default="admin")
    parser.add_argument("--export", action="store_true", help="导出仪表板JSON到文件")
    args = parser.parse_args()

    if args.export:
        builder = DashboardBuilder()
        (builder.add_api_request_rate()
                .add_api_latency()
                .add_error_rate()
                .add_active_users()
                .add_content_generation()
                .add_database_connections()
                .add_redis_ops()
                .add_system_resources()
                .add_alert_status())
        dashboard = builder.build()
        output_path = os.path.join(os.path.dirname(__file__), "acas_pro_dashboard.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dashboard, f, ensure_ascii=False, indent=2)
        print(f"仪表板已导出: {output_path}")
    else:
        results = setup_grafana({
            "grafana_url": args.grafana_url,
            "grafana_user": args.grafana_user,
            "grafana_pass": args.grafana_pass
        })
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
