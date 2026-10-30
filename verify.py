"""End-to-end acceptance for ZhiXu: real PowerContext storage, search, context, restart."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / ".verify-data"
PC_PORT = 18180
APP_PORT = 18100
PC = f"http://127.0.0.1:{PC_PORT}"
APP = f"http://127.0.0.1:{APP_PORT}"

passed: list[str] = []
failed: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        passed.append(name)
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    else:
        failed.append(name)
        print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))


def request(method: str, url: str, payload: dict | None = None, timeout: float = 20) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            detail = json.loads(body)
        except json.JSONDecodeError:
            detail = {"detail": body}
        return error.code, detail


def wait_for(url: str, timeout: float = 90) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.3)
    return False


def spawn(module: str, env: dict) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-m", module], cwd=ROOT, env=env)


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()


def main() -> int:
    if DATA.exists():
        shutil.rmtree(DATA)
    env = dict(os.environ)
    env.update(
        {
            "PYTHONPATH": str(ROOT) + os.pathsep + env.get("PYTHONPATH", ""),
            "PYTHONUTF8": "1",
            "ZHIXU_DATA_DIR": str(DATA),
            "ZHIXU_PC_PORT": str(PC_PORT),
            "ZHIXU_PORT": str(APP_PORT),
            "ZHIXU_PC_URL": PC,
        }
    )
    pc: subprocess.Popen | None = None
    app: subprocess.Popen | None = None
    try:
        print("== 启动真实 PowerContext Server + 知序 ==")
        pc = spawn("zhixu.pc_server", env)
        check("PowerContext Server 就绪", wait_for(f"{PC}/health/ready"), PC)
        app = spawn("zhixu.app", env)
        check("知序 Web 应用就绪", wait_for(f"{APP}/api/status"), APP)
        if failed:
            return 1

        status_code, status = request("GET", f"{APP}/api/status")
        check("状态接口返回连接成功", status_code == 200 and status.get("connected") is True)
        check(
            "后端为 PowerContext 1.2.0 且支持 FTS",
            status.get("pc_version", "").startswith("1.2") and "fts" in status.get("search_modes", []),
            f"version={status.get('pc_version')} modes={status.get('search_modes')}",
        )

        code, scope = request("POST", f"{APP}/api/scopes", {"title": "验证知识库", "summary": "verify"})
        scope_id = scope.get("scope_id")
        check("创建 Scope", code == 200 and bool(scope_id), scope_id or str(scope))

        code, seeded = request("POST", f"{APP}/api/scopes/{scope_id}/seed")
        check("导入 8 篇示例资料到 PowerContext 记忆", code == 200 and seeded.get("seeded") == 8, str(seeded))

        code, docs = request("GET", f"{APP}/api/scopes/{scope_id}/documents")
        check("条目列表可回查", code == 200 and docs.get("count") == 8, f"count={docs.get('count')}")
        known_entries = {item.get("entry_id") for item in docs.get("items", []) if item.get("entry_id")}

        code, search = request(
            "POST", f"{APP}/api/scopes/{scope_id}/search", {"query": "上下文 引用", "limit": 5}
        )
        hits = search.get("hits", [])
        check(
            "FTS 检索命中并返回 citation",
            code == 200 and bool(hits) and all(hit.get("citation", {}).get("entry_id") for hit in hits),
            f"mode={search.get('mode')} hits={len(hits)}",
        )
        hit_entries = {hit["citation"]["entry_id"] for hit in hits}
        check("检索引用可回查到已存条目", bool(hit_entries) and hit_entries <= known_entries)

        code, prepared = request(
            "POST",
            f"{APP}/api/scopes/{scope_id}/prepare",
            {"query": "怎么把资料组装成 AI 上下文", "max_bytes": 1800},
        )
        check(
            "PreparedContext 状态 ready 且不超预算",
            code == 200 and prepared.get("status") == "ready" and prepared.get("content_bytes", 10**9) <= 1800,
            f"bytes={prepared.get('content_bytes')}",
        )
        check(
            "上下文包含引用条目",
            bool(prepared.get("citations")),
            f"citations={len(prepared.get('citations', []))}",
        )

        print("== 重启 PowerContext Server，验证持久化 ==")
        stop(pc)
        pc = spawn("zhixu.pc_server", env)
        check("Server 重启就绪", wait_for(f"{PC}/health/ready"), PC)
        if not failed:
            time.sleep(0.5)
            code, search2 = request(
                "POST", f"{APP}/api/scopes/{scope_id}/search", {"query": "seekdb 向量检索", "limit": 5}
            )
            if not search2.get("hits"):
                code, search2 = request(
                    "POST", f"{APP}/api/scopes/{scope_id}/search", {"query": "向量检索", "limit": 5}
                )
            check(
                "重启后同一 Scope 仍可检索",
                code == 200 and bool(search2.get("hits")),
                f"hits={len(search2.get('hits', []))}",
            )
            code, scopes = request("GET", f"{APP}/api/scopes")
            check(
                "重启后知识库仍在",
                code == 200 and any(item.get("scope_id") == scope_id for item in scopes.get("items", [])),
            )

        db = DATA / "powercontext.db"
        check("SQLite 数据库文件已落盘", db.is_file() and db.stat().st_size > 0, f"{db.stat().st_size if db.is_file() else 0} bytes")
    finally:
        if app is not None:
            stop(app)
        if pc is not None:
            stop(pc)

    print(f"\n通过 {len(passed)} 项，失败 {len(failed)} 项。")
    if failed:
        for name in failed:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
