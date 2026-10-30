"""Run the real PowerContext Server (SQLite backend) for ZhiXu."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from powercontext.builtin.persistence.sqlite import SQLiteConfig
from powercontext.builtin.runtime.config import ExternalSkillsConfig, InferenceConfig, RuntimeConfig
from powercontext.server.factory import create_server_app
from powercontext.server.settings import (
    AccessControlConfig,
    BearerAuthConfig,
    HttpConfig,
    McpConfig,
    MetricsConfig,
    ServerSettings,
    TracingConfig,
)

APP_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("ZHIXU_DATA_DIR", APP_ROOT / "data")).expanduser().resolve()
HOST = os.environ.get("ZHIXU_PC_HOST", "127.0.0.1")
PORT = int(os.environ.get("ZHIXU_PC_PORT", "18080"))


def build_app():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings = ServerSettings(
        workspace=DATA_DIR,
        database=SQLiteConfig(url=f"sqlite+aiosqlite:///{DATA_DIR / 'powercontext.db'}"),
        http=HttpConfig(host=HOST, port=PORT),
        auth=BearerAuthConfig(enabled=False),
        access=AccessControlConfig(mode="disabled"),
        inference=InferenceConfig(),
        runtime=RuntimeConfig(schedule_seconds=None, experience_schedule_seconds=None),
        external_skills=ExternalSkillsConfig(),
        mcp=McpConfig(enabled=False),
        metrics=MetricsConfig(enabled=False),
        tracing=TracingConfig(enabled=False),
    )
    return create_server_app(settings=settings, scheduler_path=DATA_DIR / "scheduler.db")


if __name__ == "__main__":
    print(f"[zhixu] PowerContext Server: http://{HOST}:{PORT}  data={DATA_DIR}")
    uvicorn.run(build_app(), host=HOST, port=PORT, log_level="info", access_log=True)
