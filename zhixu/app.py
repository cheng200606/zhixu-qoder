"""ZhiXu web app: notes in, cited AI-ready context out — powered by PowerContext."""

from __future__ import annotations

import io
import json
import os
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pypdf import PdfReader

from powercontext.client import PowerContextClient
from powercontext.client.errors import ClientError
from powercontext.errors import PowerContextError
from powercontext.http import (
    CreateScopeRequest,
    ListMemoryEntriesRequest,
    PrepareContextRequest,
    RememberMemoryRequest,
    RetireMemoryEntryRequest,
    SearchMemoryRequest,
)

APP_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
SAMPLES_DIR = APP_ROOT / "samples"
DATA_DIR = Path(os.environ.get("ZHIXU_DATA_DIR", APP_ROOT / "data")).expanduser().resolve()
PC_URL = os.environ.get("ZHIXU_PC_URL", "http://127.0.0.1:18080")
HOST = os.environ.get("ZHIXU_HOST", "127.0.0.1")
PORT = int(os.environ.get("ZHIXU_PORT", "18000"))

BEGIN_MARK = "BEGIN_POWERCONTEXT_PREPARED_CONTEXT_V1"
END_MARK = "END_POWERCONTEXT_PREPARED_CONTEXT_V1"
KIND_LABELS = {
    "note": "笔记",
    "document": "文档",
    "meeting": "会议纪要",
    "code": "代码片段",
    "resource": "资料",
}


def document_text(title: str, content: str) -> str:
    return f"# {title.strip()}\n\n{content.strip()}"


def split_document(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        return lines[0][2:].strip(), "\n".join(lines[1:]).strip()
    first = next((line.strip() for line in lines if line.strip()), "未命名条目")
    return first[:60], text.strip()


def make_snippet(text: str, query: str, width: int = 220) -> str:
    body = " ".join(text.split())
    term = query.strip()
    index = body.find(term) if term else -1
    if index < 0 and term:
        for word in term.replace("，", " ").replace(",", " ").split():
            index = body.find(word)
            if index >= 0:
                break
    if index < 0:
        return body[:width] + ("…" if len(body) > width else "")
    start = max(0, index - width // 3)
    end = min(len(body), start + width)
    return ("…" if start else "") + body[start:end] + ("…" if end < len(body) else "")


def parse_prepared_items(content: str | None) -> list[dict]:
    if not content or BEGIN_MARK not in content or END_MARK not in content:
        return []
    payload = content.split(BEGIN_MARK, 1)[1].split(END_MARK, 1)[0].strip()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    items = data.get("items", [])
    return items if isinstance(items, list) else []


def describe_entry(entry, query: str = "") -> dict:
    title, body = split_document(entry.text)
    return {
        "entry_id": entry.citation.entry_id,
        "title": title,
        "preview": make_snippet(body, query, 180),
        "kind": entry.kind,
        "kind_label": KIND_LABELS.get(entry.kind, entry.kind),
        "version": entry.version,
        "state": entry.state,
        "citation": entry.citation.model_dump(mode="json"),
    }


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.pc = PowerContextClient(PC_URL, timeout=60)
    try:
        yield
    finally:
        await application.state.pc.aclose()


app = FastAPI(title="知序 ZhiXu", version="1.0.0", lifespan=lifespan)


class ScopeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(default="", max_length=500)


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    kind: str = Field(default="note", max_length=32)


class SearchBody(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=8, ge=1, le=30)


class PrepareBody(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    max_bytes: int = Field(default=2400, ge=400, le=32000)


def client(request: Request) -> PowerContextClient:
    return request.app.state.pc


def fail(exc: Exception) -> HTTPException:
    return HTTPException(status_code=502, detail=f"PowerContext 调用失败：{exc}")


@app.get("/api/status")
async def status(request: Request):
    pc = client(request)
    try:
        caps = await pc.get_capabilities()
        scopes = await pc.list_scopes(limit=100)
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI as connection state
        return {
            "connected": False,
            "pc_url": PC_URL,
            "error": str(exc),
        }
    return {
        "connected": True,
        "app_version": "1.0.0",
        "pc_url": PC_URL,
        "pc_version": version("powercontext"),
        "database": str(DATA_DIR / "powercontext.db"),
        "search_modes": [str(mode) for mode in caps.search_modes],
        "memory_extraction": caps.memory_extraction,
        "context_schema": "powercontext.prepared-context.v1",
        "scope_count": len(scopes.items),
    }


@app.get("/api/scopes")
async def list_scopes(request: Request):
    try:
        page = await client(request).list_scopes(limit=100)
    except Exception as exc:  # noqa: BLE001
        raise fail(exc) from exc
    return {
        "items": [
            {
                "scope_id": item.scope_id,
                "title": item.title,
                "summary": item.summary,
                "version": item.version,
            }
            for item in page.items
        ]
    }


@app.post("/api/scopes")
async def create_scope(body: ScopeCreate, request: Request):
    try:
        scope = await client(request).create_scope(
            CreateScopeRequest(
                title=body.title.strip(),
                summary=body.summary.strip() or "知序知识库",
                idempotency_key=f"zhixu-{uuid4().hex}",
            )
        )
    except Exception as exc:  # noqa: BLE001
        raise fail(exc) from exc
    return {"scope_id": scope.scope_id, "title": scope.title, "summary": scope.summary}


@app.get("/api/scopes/{scope_id}/documents")
async def list_documents(scope_id: str, request: Request):
    try:
        result = await client(request).list_memory_entries(ListMemoryEntriesRequest(scope_id=scope_id))
    except Exception as exc:  # noqa: BLE001
        raise fail(exc) from exc
    documents = [describe_entry(entry) for entry in reversed(result.entries) if entry.state == "active"]
    return {"items": documents, "count": len(documents)}


@app.post("/api/scopes/{scope_id}/documents")
async def add_document(scope_id: str, body: DocumentCreate, request: Request):
    try:
        saved = await client(request).remember_memory(
            RememberMemoryRequest(
                scope_id=scope_id,
                kind=body.kind or "note",
                text=document_text(body.title, body.content),
                reason="知序手动导入",
            )
        )
    except Exception as exc:  # noqa: BLE001
        raise fail(exc) from exc
    return {"entry_id": saved.entry.citation.entry_id if saved.entry else None, "title": body.title}


@app.post("/api/scopes/{scope_id}/upload")
async def upload_document(scope_id: str, request: Request, file: UploadFile = File(...)):
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="文件为空")
    name = Path(file.filename or "上传文档").name
    stem = Path(name).stem or "上传文档"
    entries: list[tuple[str, str, str]] = []
    if name.lower().endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(raw))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"PDF 解析失败：{exc}") from exc
        for number, page in enumerate(reader.pages, start=1):
            if number > 100:
                break
            text = (page.extract_text() or "").strip()
            if text:
                entries.append((f"{stem} · 第 {number} 页", text, "document"))
        if not entries:
            raise HTTPException(status_code=400, detail="PDF 中没有可提取的文本（可能是扫描件）")
    else:
        text = raw.decode("utf-8-sig", errors="replace").strip()
        if not text:
            raise HTTPException(status_code=400, detail="文件没有文本内容")
        entries.append((stem, text[:200_000], "document"))
    try:
        pc = client(request)
        for title, content, kind in entries:
            await pc.remember_memory(
                RememberMemoryRequest(
                    scope_id=scope_id,
                    kind=kind,
                    text=document_text(title, content),
                    reason=f"知序导入 {name}",
                )
            )
    except Exception as exc:  # noqa: BLE001
        raise fail(exc) from exc
    return {"imported": len(entries), "first_title": entries[0][0]}


@app.delete("/api/scopes/{scope_id}/documents/{entry_id}")
async def delete_document(scope_id: str, entry_id: str, request: Request):
    try:
        result = await client(request).list_memory_entries(ListMemoryEntriesRequest(scope_id=scope_id))
        target = next((entry for entry in result.entries if entry.citation.entry_id == entry_id), None)
        if target is None:
            raise HTTPException(status_code=404, detail="条目不存在")
        await client(request).retire_memory_entry(
            RetireMemoryEntryRequest(scope_id=scope_id, citation=target.citation, reason="用户删除")
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise fail(exc) from exc
    return {"deleted": entry_id}


@app.post("/api/scopes/{scope_id}/search")
async def search(scope_id: str, body: SearchBody, request: Request):
    try:
        result = await client(request).search_memory(
            SearchMemoryRequest(scope_id=scope_id, query=body.query.strip(), limit=body.limit, mode="auto")
        )
    except Exception as exc:  # noqa: BLE001
        raise fail(exc) from exc
    hits = []
    for hit in result.hits:
        title, text = split_document(hit.text)
        hits.append(
            {
                "title": title,
                "snippet": make_snippet(text, body.query),
                "score": round(hit.score, 4),
                "matched_by": list(hit.matched_by),
                "citation": hit.citation.model_dump(mode="json"),
            }
        )
    return {
        "mode": str(result.mode),
        "query": body.query,
        "hits": hits,
        "memory_revision": result.memory.revision,
    }


@app.post("/api/scopes/{scope_id}/prepare")
async def prepare(scope_id: str, body: PrepareBody, request: Request):
    try:
        prepared = await client(request).prepare_context(
            PrepareContextRequest(scope_id=scope_id, query=body.query.strip(), max_bytes=body.max_bytes)
        )
    except Exception as exc:  # noqa: BLE001
        raise fail(exc) from exc
    items = parse_prepared_items(prepared.content)
    citations = [
        {
            "entry_id": item.get("citation", {}).get("entry_id"),
            "title": split_document(item.get("content", ""))[0],
            "content": item.get("content", ""),
            "truncated": item.get("truncated", False),
        }
        for item in items
    ]
    return {
        "schema": prepared.schema_,
        "status": str(prepared.status),
        "query": body.query,
        "max_bytes": body.max_bytes,
        "content": prepared.content,
        "content_bytes": prepared.content_bytes,
        "citations": citations,
    }


@app.post("/api/scopes/{scope_id}/seed")
async def seed(scope_id: str, request: Request):
    try:
        pc = client(request)
        existing = await pc.list_memory_entries(ListMemoryEntriesRequest(scope_id=scope_id))
        if existing.entries:
            return {"seeded": 0, "skipped": True, "count": len(existing.entries)}
        imported = 0
        for path in sorted(SAMPLES_DIR.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            title, body = split_document(text)
            await pc.remember_memory(
                RememberMemoryRequest(
                    scope_id=scope_id,
                    kind="resource",
                    text=document_text(title, body),
                    reason=f"知序示例资料 {path.name}",
                )
            )
            imported += 1
    except Exception as exc:  # noqa: BLE001
        raise fail(exc) from exc
    return {"seeded": imported, "skipped": False, "count": imported}


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    print(f"[zhixu] app: http://{HOST}:{PORT}  PowerContext={PC_URL}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
