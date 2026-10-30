"""Start PowerContext Server and the ZhiXu web app together."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PC_PORT = int(os.environ.get("ZHIXU_PC_PORT", "18080"))
APP_PORT = int(os.environ.get("ZHIXU_PORT", "18000"))


def wait_for(url: str, timeout: float = 90) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.4)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="启动知序（含 PowerContext Server）")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("PYTHONUTF8", "1")
    processes: list[tuple[str, subprocess.Popen]] = []

    def spawn(name: str, module: str) -> subprocess.Popen:
        process = subprocess.Popen([sys.executable, "-m", module], cwd=ROOT, env=env)
        processes.append((name, process))
        return process

    try:
        print("[1/2] 启动 PowerContext Server ...")
        spawn("PowerContext", "zhixu.pc_server")
        if not wait_for(f"http://127.0.0.1:{PC_PORT}/health/ready"):
            print("PowerContext Server 启动失败，请检查端口 18080 是否被占用。")
            return 1
        print(f"      PowerContext 就绪: http://127.0.0.1:{PC_PORT}")

        print("[2/2] 启动知序 Web 应用 ...")
        spawn("知序", "zhixu.app")
        if not wait_for(f"http://127.0.0.1:{APP_PORT}/api/status"):
            print("知序启动失败，请检查端口 18000 是否被占用。")
            return 1
        print(f"      知序就绪: http://127.0.0.1:{APP_PORT}")

        if not args.no_browser:
            webbrowser.open(f"http://127.0.0.1:{APP_PORT}")
        print("\n按 Ctrl+C 停止。数据保存在 data/powercontext.db，重启后仍在。\n")

        while True:
            for name, process in processes:
                code = process.poll()
                if code is not None:
                    print(f"{name} 已退出（code={code}）。")
                    return code
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n正在停止 ...")
        return 0
    finally:
        for name, process in processes:
            if process.poll() is None:
                process.terminate()
        for name, process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
