const state = {
  scopes: [],
  scopeId: null,
  documents: [],
  query: "",
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: options.body instanceof FormData ? {} : { "Content-Type": "application/json" },
    ...options,
  });
  const text = await response.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = { detail: text }; }
  if (!response.ok) throw new Error(data?.detail || `请求失败（${response.status}）`);
  return data;
}

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove("show"), 2400);
}

function shortId(value, size = 18) {
  if (!value) return "—";
  return value.length > size ? `${value.slice(0, size)}…` : value;
}

function setRaw(endpoint, data) {
  $("rawEndpoint").textContent = endpoint;
  $("rawPre").textContent = JSON.stringify(data, null, 2);
  $("copyRaw").hidden = false;
}

async function loadStatus() {
  const pill = $("connPill");
  try {
    const status = await api("/api/status");
    if (!status.connected) throw new Error(status.error || "未连接");
    pill.className = "pill ok";
    $("connText").textContent = "PowerContext 已连接";
    $("statBackend").textContent = "PowerContext · SQLite";
    $("statModes").textContent = (status.search_modes || []).join(" / ");
    $("statVersion").textContent = `v${status.pc_version}`;
    $("statDb").textContent = status.database;
    $("statDb").title = status.database;
  } catch (error) {
    pill.className = "pill bad";
    $("connText").textContent = "PowerContext 未连接";
    $("statBackend").textContent = "未连接";
    toast(`无法连接 PowerContext：${error.message}`);
  }
}

async function loadScopes() {
  const data = await api("/api/scopes");
  state.scopes = (data.items || []).filter(
    (scope) => !(scope.title === "Default" && scope.summary === "Default context"),
  );
  const list = $("scopeList");
  list.innerHTML = "";
  for (const scope of state.scopes) {
    const li = document.createElement("li");
    li.className = `scope-item${scope.scope_id === state.scopeId ? " active" : ""}`;
    li.innerHTML = `<b></b><span></span>`;
    li.querySelector("b").textContent = scope.title;
    li.querySelector("span").textContent = scope.summary || "—";
    li.addEventListener("click", () => selectScope(scope.scope_id));
    list.appendChild(li);
  }
  if (!state.scopeId && state.scopes.length) {
    await selectScope(state.scopes[state.scopes.length - 1].scope_id);
  } else if (!state.scopes.length) {
    $("searchState").textContent = "还没有知识库。先新建一个，或载入示例知识库。";
  }
}

async function selectScope(scopeId) {
  state.scopeId = scopeId;
  document.querySelectorAll(".scope-item").forEach((el, index) => {
    el.classList.toggle("active", state.scopes[index]?.scope_id === scopeId);
  });
  await loadDocuments();
}

async function loadDocuments() {
  if (!state.scopeId) return;
  const data = await api(`/api/scopes/${encodeURIComponent(state.scopeId)}/documents`);
  state.documents = data.items || [];
  $("docCount").textContent = data.count ?? state.documents.length;
  renderDocuments();
}

function renderDocuments() {
  const list = $("docList");
  list.innerHTML = "";
  for (const doc of state.documents) {
    const li = document.createElement("li");
    li.className = "doc-item";
    const main = document.createElement("div");
    main.className = "doc-main";
    const title = document.createElement("b");
    title.textContent = doc.title;
    title.title = doc.title;
    const preview = document.createElement("small");
    preview.textContent = doc.preview || doc.kind_label;
    main.append(title, preview);
    const kind = document.createElement("span");
    kind.className = "kind";
    kind.textContent = doc.kind_label;
    const del = document.createElement("button");
    del.className = "del";
    del.textContent = "×";
    del.title = "从记忆中停用该条目";
    del.addEventListener("click", () => deleteDocument(doc));
    li.append(main, kind, del);
    list.appendChild(li);
  }
  $("docEmpty").hidden = state.documents.length > 0;
  $("docEmpty").querySelector("p").textContent = state.scopes.length ? "这个知识库还没有资料。" : "还没有知识库。点击下方按钮开始。";
}

async function deleteDocument(doc) {
  if (!confirm(`停用「${doc.title}」？条目会从检索中移除，但 PowerContext 保留历史版本。`)) return;
  try {
    await api(`/api/scopes/${encodeURIComponent(state.scopeId)}/documents/${encodeURIComponent(doc.entry_id)}`, { method: "DELETE" });
    toast("已停用该条目");
    await loadDocuments();
  } catch (error) {
    toast(error.message);
  }
}

async function createScope(title, summary = "知序知识库") {
  const scope = await api("/api/scopes", { method: "POST", body: JSON.stringify({ title, summary }) });
  state.scopeId = scope.scope_id;
  await loadScopes();
  return scope;
}

async function seedDemo() {
  const button = $("seedBtn");
  button.disabled = true;
  button.textContent = "正在写入记忆…";
  try {
    let scopeId = state.scopeId;
    if (!scopeId) {
      const scope = await createScope("OceanBase 大赛资料库", "第六届 OceanBase 大赛资料与备赛笔记");
      scopeId = scope.scope_id;
    }
    const result = await api(`/api/scopes/${encodeURIComponent(scopeId)}/seed`, { method: "POST" });
    toast(result.skipped ? `该知识库已有 ${result.count} 条资料` : `已导入 ${result.seeded} 篇示例资料`);
    await loadDocuments();
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "一键载入示例知识库";
  }
}

function renderResults(data) {
  const list = $("results");
  list.innerHTML = "";
  $("suggest").hidden = true;
  const mode = $("searchMode");
  mode.hidden = false;
  mode.textContent = `${String(data.mode).toUpperCase()} · ${data.hits.length} 条`;
  if (!data.hits.length) {
    $("searchState").textContent = `没有命中的资料。试试别的关键词，或先导入资料。`;
    return;
  }
  $("searchState").textContent = `「${data.query}」的检索结果（记忆版本 r${data.memory_revision}）`;
  const max = Math.max(...data.hits.map((hit) => hit.score || 0), 0.0001);
  for (const hit of data.hits) {
    const li = document.createElement("li");
    li.className = "hit";
    const title = document.createElement("h3");
    title.textContent = hit.title;
    const snippet = document.createElement("p");
    snippet.textContent = hit.snippet;
    const meta = document.createElement("div");
    meta.className = "meta";
    const bar = document.createElement("span");
    bar.className = "bar";
    const fill = document.createElement("i");
    fill.style.width = `${Math.max(6, Math.round(((hit.score || 0) / max) * 100))}%`;
    bar.appendChild(fill);
    const score = document.createElement("span");
    score.textContent = `score ${hit.score}`;
    const matched = document.createElement("span");
    matched.textContent = (hit.matched_by || []).join(" + ").toUpperCase();
    const cite = document.createElement("span");
    cite.className = "cite";
    cite.textContent = hit.citation.entry_id;
    cite.title = JSON.stringify(hit.citation);
    meta.append(bar, score, matched, cite);
    li.append(title, snippet, meta);
    list.appendChild(li);
  }
}

async function runSearch(event) {
  event?.preventDefault();
  const query = $("query").value.trim();
  if (!query) return;
  if (!state.scopeId) { toast("请先创建或选择一个知识库"); return; }
  state.query = query;
  $("searchState").textContent = "检索中…";
  try {
    const data = await api(`/api/scopes/${encodeURIComponent(state.scopeId)}/search`, {
      method: "POST",
      body: JSON.stringify({ query, limit: 8 }),
    });
    renderResults(data);
    setRaw(`POST /v1/scopes/{scope_id}/memory/search · mode=${data.mode}`, data);
  } catch (error) {
    $("searchState").textContent = error.message;
    toast(error.message);
  }
}

async function runPrepare() {
  const query = $("query").value.trim() || state.query;
  if (!query) { toast("先输入一个问题"); return; }
  if (!state.scopeId) { toast("请先创建或选择一个知识库"); return; }
  const maxBytes = Number($("budget").value);
  $("contextState").textContent = "组装中…";
  try {
    const data = await api(`/api/scopes/${encodeURIComponent(state.scopeId)}/prepare`, {
      method: "POST",
      body: JSON.stringify({ query, max_bytes: maxBytes }),
    });
    $("contextPre").textContent = data.content || "（没有可用内容）";
    $("contextState").textContent = `${data.status} · ${data.content_bytes} bytes · ${data.citations.length} 条引用`;
    $("copyContext").hidden = !data.content;
    renderCitations(data.citations);
    setRaw(`POST /v1/scopes/{scope_id}/context/prepare · max_bytes=${maxBytes}`, data);
  } catch (error) {
    $("contextState").textContent = error.message;
    toast(error.message);
  }
}

function renderCitations(citations) {
  const list = $("citationList");
  list.innerHTML = "";
  if (!citations.length) {
    const li = document.createElement("li");
    li.className = "muted";
    li.textContent = "本次上下文没有引用（可能没有命中记忆）。";
    list.appendChild(li);
    return;
  }
  for (const citation of citations) {
    const li = document.createElement("li");
    const title = document.createElement("b");
    title.textContent = citation.title || "未命名条目";
    const code = document.createElement("code");
    code.textContent = citation.entry_id || "—";
    li.append(title, code);
    if (citation.truncated) {
      const flag = document.createElement("div");
      flag.className = "muted";
      flag.textContent = "（为满足字节预算已截断）";
      li.appendChild(flag);
    }
    list.appendChild(li);
  }
}

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === name));
  document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.toggle("active", panel.id === `panel-${name}`));
  $("tabNote").textContent = name === "raw" ? "PowerContext 原始响应" : name === "context" ? "PreparedContext v1" : "检索由 PowerContext Server 执行";
}

async function saveDocument() {
  if (!state.scopeId) { toast("请先创建知识库"); return; }
  const file = $("docFile").files[0];
  try {
    if (file) {
      const form = new FormData();
      form.append("file", file);
      const result = await api(`/api/scopes/${encodeURIComponent(state.scopeId)}/upload`, { method: "POST", body: form });
      toast(`已导入 ${result.imported} 条（${result.first_title}）`);
    } else {
      const title = $("docTitle").value.trim();
      const content = $("docContent").value.trim();
      if (!title || !content) { toast("标题和内容都要填写"); return; }
      await api(`/api/scopes/${encodeURIComponent(state.scopeId)}/documents`, {
        method: "POST",
        body: JSON.stringify({ title, content, kind: $("docKind").value }),
      });
      toast("已写入 PowerContext 记忆");
    }
    $("importDialog").close();
    $("importForm").reset();
    await loadDocuments();
  } catch (error) {
    toast(error.message);
  }
}

function bind() {
  $("searchForm").addEventListener("submit", runSearch);
  $("prepareBtn").addEventListener("click", runPrepare);
  $("seedBtn").addEventListener("click", seedDemo);
  $("budget").addEventListener("input", (event) => { $("budgetValue").textContent = event.target.value; });
  $("copyContext").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("contextPre").textContent);
    toast("上下文已复制，可直接粘贴给 AI");
  });
  $("copyRaw").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("rawPre").textContent);
    toast("原始 JSON 已复制");
  });
  $("openImport").addEventListener("click", () => {
    if (!state.scopeId) { toast("请先创建知识库"); return; }
    $("importDialog").showModal();
  });
  $("saveDoc").addEventListener("click", saveDocument);
  $("newScopeBtn").addEventListener("click", () => {
    $("scopeForm").hidden = false;
    $("scopeTitle").focus();
  });
  $("cancelScope").addEventListener("click", () => { $("scopeForm").hidden = true; });
  $("scopeForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const title = $("scopeTitle").value.trim();
    if (!title) return;
    try {
      await createScope(title);
      $("scopeForm").reset();
      $("scopeForm").hidden = true;
      toast("知识库已创建");
    } catch (error) {
      toast(error.message);
    }
  });
  document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => switchTab(tab.dataset.tab)));
  document.querySelectorAll(".chips button").forEach((chip) => {
    chip.addEventListener("click", () => {
      $("query").value = chip.dataset.q;
      runSearch();
    });
  });
  $("query").addEventListener("keydown", (event) => {
    if (event.key === "Enter") runSearch(event);
  });
}

async function init() {
  bind();
  await loadStatus();
  try {
    await loadScopes();
  } catch (error) {
    toast(error.message);
  }
}

init();
