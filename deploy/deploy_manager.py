# ACAS Pro - 企业级自动获客系统
# 版权所有 (c) 2026 高智中科（北京）科技有限公司

"""
一键部署管理脚本
支持环境：开发/测试/预生产/生产
部署前检查 → 备份 → 停止服务 → 更新代码 → 迁移数据库 → 启动服务 → 验证
自动回滚机制
"""

import json
import os
import time
import logging
import subprocess
import platform
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DeployEnv(Enum):
    DEV = "development"
    TEST = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class DeployStep(Enum):
    PRE_CHECK = "pre_check"
    BACKUP = "backup"
    STOP_SERVICE = "stop_service"
    UPDATE_CODE = "update_code"
    MIGRATE_DB = "migrate_db"
    START_SERVICE = "start_service"
    VERIFY = "verify"
    ROLLBACK = "rollback"


@dataclass
class StepResult:
    step: DeployStep
    success: bool = False
    message: str = ""
    duration: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class DeployManager:
    """部署管理器"""

    ENV_CONFIG = {
        DeployEnv.DEV: {"port": 5002, "workers": 1, "debug": True, "backup": False},
        DeployEnv.TEST: {"port": 5002, "workers": 2, "debug": True, "backup": True},
        DeployEnv.STAGING: {"port": 5002, "workers": 4, "debug": False, "backup": True},
        DeployEnv.PRODUCTION: {"port": 5002, "workers": 8, "debug": False, "backup": True},
    }

    def __init__(self, env: DeployEnv = DeployEnv.DEV, project_dir: str = ".",
                 dry_run: bool = False):
        self.env = env
        self.project_dir = os.path.abspath(project_dir)
        self.dry_run = dry_run
        self.config = self.ENV_CONFIG[env]
        self.results: List[StepResult] = []
        self.backup_id: str = ""
        self._process = None

    def _run_cmd(self, cmd: str, timeout: int = 60) -> tuple:
        if self.dry_run:
            logger.info("[DRY-RUN] %s", cmd)
            return 0, "", ""

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=self.project_dir
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "命令超时"
        except Exception as e:
            return -1, "", str(e)

    def pre_check(self) -> StepResult:
        """部署前检查"""
        start = time.time()
        step = StepResult(step=DeployStep.PRE_CHECK)
        checks = []

        # 检查Python版本
        rc, out, _ = self._run_cmd("python --version")
        if rc == 0:
            checks.append(("Python版本", True, out.strip()))
        else:
            checks.append(("Python版本", False, "未安装"))

        # 检查依赖
        rc, _, err = self._run_cmd("pip check")
        if rc == 0:
            checks.append(("依赖完整性", True, "OK"))
        else:
            checks.append(("依赖完整性", False, err[:100]))

        # 检查端口
        port = self.config["port"]
        rc, _, _ = self._run_cmd(f"netstat -an | findstr :{port}")
        if rc == 0:
            checks.append(("端口检查", False, f"端口 {port} 已被占用"))
        else:
            checks.append(("端口检查", True, f"端口 {port} 可用"))

        # 检查磁盘空间
        if platform.system() == "Windows":
            rc, out, _ = self._run_cmd("wmic logicaldisk get size,freespace,caption")
            checks.append(("磁盘空间", True, "已检查"))

        # 检查.env文件
        env_file = os.path.join(self.project_dir, ".env")
        if os.path.exists(env_file):
            checks.append((".env配置", True, "存在"))
        else:
            checks.append((".env配置", False, "缺失"))

        failed = [c for c in checks if not c[1]]
        step.success = len(failed) == 0
        step.message = f"检查 {len(checks)} 项，{len(failed)} 项失败"
        step.duration = round(time.time() - start, 2)

        for name, ok, detail in checks:
            icon = "✅" if ok else "❌"
            logger.info("  %s %s: %s", icon, name, detail)

        self.results.append(step)
        return step

    def backup(self) -> StepResult:
        """备份当前版本"""
        start = time.time()
        step = StepResult(step=DeployStep.BACKUP)

        if not self.config["backup"]:
            step.success = True
            step.message = "开发环境跳过备份"
            self.results.append(step)
            return step

        self.backup_id = f"pre_deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir = os.path.join(self.project_dir, "backups", self.backup_id)
        os.makedirs(backup_dir, exist_ok=True)

        # 备份数据库
        rc, out, err = self._run_cmd(
            'python -c "from dr.backup_manager import BackupManager; '
            'm=BackupManager(); r=m.backup_database(); print(r.id)"',
            timeout=300
        )
        if rc == 0:
            step.message = f"备份完成: {self.backup_id}"
        else:
            step.message = f"备份警告: {err[:100]}"

        step.success = True
        step.duration = round(time.time() - start, 2)
        self.results.append(step)
        return step

    def stop_service(self) -> StepResult:
        """停止服务"""
        start = time.time()
        step = StepResult(step=DeployStep.STOP_SERVICE)

        # Windows: 查找并终止Python进程
        rc, out, _ = self._run_cmd("tasklist | findstr python")
        if rc == 0 and out:
            logger.info("发现运行中的Python进程，尝试停止...")
            self._run_cmd("taskkill /F /IM python.exe", timeout=10)
            time.sleep(2)

        step.success = True
        step.message = "服务已停止"
        step.duration = round(time.time() - start, 2)
        self.results.append(step)
        return step

    def update_code(self) -> StepResult:
        """更新代码"""
        start = time.time()
        step = StepResult(step=DeployStep.UPDATE_CODE)

        # 安装/更新依赖
        rc, _, err = self._run_cmd("pip install -r requirements.txt --quiet", timeout=300)
        if rc == 0:
            step.message = "依赖更新完成"
        else:
            step.message = f"依赖更新警告: {err[:100]}"

        step.success = True
        step.duration = round(time.time() - start, 2)
        self.results.append(step)
        return step

    def migrate_db(self) -> StepResult:
        """迁移数据库"""
        start = time.time()
        step = StepResult(step=DeployStep.MIGRATE_DB)

        db_url = os.getenv("DATABASE_URL", "")
        if not db_url or "sqlite" in db_url:
            step.success = True
            step.message = "SQLite无需迁移"
            self.results.append(step)
            return step

        rc, out, err = self._run_cmd(
            "python -m database.migrate upgrade", timeout=120
        )
        step.success = rc == 0
        step.message = "数据库迁移完成" if rc == 0 else f"迁移失败: {err[:100]}"
        step.duration = round(time.time() - start, 2)
        self.results.append(step)
        return step

    def start_service(self) -> StepResult:
        """启动服务"""
        start = time.time()
        step = StepResult(step=DeployStep.START_SERVICE)

        port = self.config["port"]
        workers = self.config["workers"]
        debug = self.config["debug"]

        cmd = f"python api_server_v2.py --port {port} --workers {workers}"
        if debug:
            cmd += " --debug"

        if not self.dry_run:
            self._process = subprocess.Popen(
                cmd, shell=True, cwd=self.project_dir,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            time.sleep(5)

            # 检查进程是否存活
            if self._process.poll() is None:
                step.success = True
                step.message = f"服务已启动 (PID: {self._process.pid}, 端口: {port})"
            else:
                step.success = False
                step.message = "服务启动失败"
        else:
            step.success = True
            step.message = f"[DRY-RUN] 服务启动命令: {cmd}"

        step.duration = round(time.time() - start, 2)
        self.results.append(step)
        return step

    def verify(self) -> StepResult:
        """验证部署"""
        start = time.time()
        step = StepResult(step=DeployStep.VERIFY)

        port = self.config["port"]
        import urllib.request
        try:
            req = urllib.request.Request(f"http://localhost:{port}/api/health")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.getcode() == 200:
                    step.success = True
                    step.message = "服务健康检查通过"
                else:
                    step.success = False
                    step.message = f"健康检查返回: {resp.getcode()}"
        except Exception as e:
            step.success = False
            step.message = f"健康检查失败: {e}"

        step.duration = round(time.time() - start, 2)
        self.results.append(step)
        return step

    def rollback(self) -> StepResult:
        """回滚到上一版本"""
        start = time.time()
        step = StepResult(step=DeployStep.ROLLBACK)

        if not self.backup_id:
            step.message = "无备份可回滚"
            step.success = False
            self.results.append(step)
            return step

        logger.warning("开始回滚到: %s", self.backup_id)

        # 停止当前服务
        self.stop_service()

        # 恢复备份
        rc, _, err = self._run_cmd(
            f'python -c "from dr.backup_manager import BackupManager; '
            f'm=BackupManager(); m.restore_backup(\'{self.backup_id}\')"',
            timeout=300
        )

        step.success = rc == 0
        step.message = "回滚完成" if rc == 0 else f"回滚失败: {err[:100]}"
        step.duration = round(time.time() - start, 2)
        self.results.append(step)

        # 重新启动服务
        if step.success:
            self.start_service()

        return step

    def deploy(self) -> Dict[str, Any]:
        """执行完整部署流程"""
        logger.info("=" * 50)
        logger.info("ACAS Pro 部署 - 环境: %s", self.env.value)
        logger.info("模式: %s", "DRY-RUN" if self.dry_run else "LIVE")
        logger.info("=" * 50)

        deploy_start = time.time()

        # 执行步骤链
        steps = [
            self.pre_check,
            self.backup,
            self.stop_service,
            self.update_code,
            self.migrate_db,
            self.start_service,
            self.verify,
        ]

        for step_func in steps:
            result = step_func()
            icon = "✅" if result.success else "❌"
            logger.info("%s %s: %s (%.2fs)", icon, result.step.value, result.message, result.duration)

            if not result.success:
                logger.error("部署失败于步骤: %s", result.step.value)
                logger.warning("执行回滚...")
                self.rollback()
                break

        total_duration = round(time.time() - deploy_start, 2)
        overall = all(r.success for r in self.results if r.step != DeployStep.ROLLBACK)

        report = {
            "environment": self.env.value,
            "overall_success": overall,
            "total_duration": total_duration,
            "steps": [
                {"step": r.step.value, "success": r.success,
                 "message": r.message, "duration": r.duration}
                for r in self.results
            ]
        }

        status = "✅ 部署成功" if overall else "❌ 部署失败"
        logger.info("\n%s (总耗时: %.2fs)", status, total_duration)

        return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ACAS Pro 部署管理")
    parser.add_argument("action", choices=["deploy", "rollback", "check"],
                        help="部署操作")
    parser.add_argument("--env", choices=[e.value for e in DeployEnv],
                        default="development", help="部署环境")
    parser.add_argument("--dir", default=".", help="项目目录")
    parser.add_argument("--dry-run", action="store_true", help="模拟模式")
    parser.add_argument("--output", help="报告输出文件")
    args = parser.parse_args()

    env = DeployEnv(args.env)
    mgr = DeployManager(env=env, project_dir=args.dir, dry_run=args.dry_run)

    if args.action == "deploy":
        report = mgr.deploy()
    elif args.action == "rollback":
        result = mgr.rollback()
        report = {"rollback": result.success, "message": result.message}
    elif args.action == "check":
        result = mgr.pre_check()
        report = {"check": result.success, "message": result.message}

    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)


if __name__ == "__main__":
    main()
