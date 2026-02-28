# -*- coding: utf-8 -*-
import os
import sys
import io
import json
import re
import time
import uuid
import shutil
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from contextlib import asynccontextmanager

import aiohttp
import pdfplumber

try:
    from google import genai
    from google.genai import types

    HAS_GOOGLE_GENAI = True
except Exception:
    HAS_GOOGLE_GENAI = False

# ==========================================
# UTF-8 控制台兼容
# ==========================================
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    if getattr(sys.stdout, "encoding", "") and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass


# ==========================================
# 配置
# ==========================================
CONFIG_FILENAME = "7.论文类型分类.json"
FALLBACK_CONFIG_FILENAME = "1.逐篇解析.json"

DEFAULT_SOURCE_DIRS = ["1.1待处理文件_逐篇", "1.2已完成文件_逐篇"]
DEFAULT_OUTPUT_ROOT = "7.论文分类结果"
DEFAULT_YES_FOLDER = "命中"
DEFAULT_NO_FOLDER = "未命中"
DEFAULT_ERR_FOLDER = "异常"
DEFAULT_REPORT_DIR = "_分类报告"

SUPPORTED_EXTS = {".pdf", ".md", ".txt"}

CLIENT_TIMEOUT_SEC = 1800
REQUEST_TIMEOUT_SEC = 1800


def log(msg: str, color: str = "white") -> None:
    ts = time.strftime("%H:%M:%S", time.localtime())
    colors = {
        "green": "\033[92m",
        "cyan": "\033[96m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "white": "",
    }
    print(f"{colors.get(color, '')}[{ts}] {msg}\033[0m")


def mask_key(text: str) -> str:
    s = str(text or "")
    return "*" + s[-6:] if len(s) > 6 else "*" + s


def load_config() -> Dict[str, Any]:
    cfg_path = Path(CONFIG_FILENAME)
    if cfg_path.exists():
        with cfg_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    fallback = Path(FALLBACK_CONFIG_FILENAME)
    if fallback.exists():
        log(f"⚠️ 未找到 {CONFIG_FILENAME}，回退使用 {FALLBACK_CONFIG_FILENAME}", "yellow")
        with fallback.open("r", encoding="utf-8") as f:
            return json.load(f)

    raise FileNotFoundError(f"找不到 {CONFIG_FILENAME} 或 {FALLBACK_CONFIG_FILENAME}")


def make_ascii_temp_copy(src_path: str) -> Tuple[str, callable]:
    src = Path(src_path)
    if not src.exists():
        raise FileNotFoundError(src_path)

    drive_root = Path(src.drive + os.sep) if src.drive else Path.cwd()
    tmp_dir = drive_root / "_classifier_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    ext = src.suffix.lower() if src.suffix else ".pdf"
    token = uuid.uuid4().hex
    tmp_path = tmp_dir / f"upload_{token}{ext}"
    shutil.copy2(str(src), str(tmp_path))

    def cleanup():
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    return str(tmp_path), cleanup


async def read_pdf_text(file_path: str) -> str:
    def _read() -> str:
        content = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    content.append(text)
        return "\n".join(content)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _read)


async def read_text_file(file_path: str) -> str:
    def _read() -> str:
        path = Path(file_path)
        return path.read_text(encoding="utf-8", errors="replace")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _read)


async def extract_text(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return await read_pdf_text(file_path)
    if ext in {".md", ".txt"}:
        return await read_text_file(file_path)
    raise ValueError(f"不支持的文件类型: {ext}")


def clip_text_for_model(text: str, max_chars: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    head = int(max_chars * 0.75)
    tail = max_chars - head
    return text[:head] + "\n\n...[中间内容省略]...\n\n" + text[-tail:]


def build_system_prompt(classify_prompt: str, question: str) -> str:
    classify_prompt = classify_prompt.strip() if classify_prompt else "无"
    return f"""
你是“学术论文二分类器”。你必须仅依据提供文档内容判断，不得联网，不得臆测。

【用户自定义分类提示词】
{classify_prompt}

【本次判断问题】
{question}

【输出要求（必须严格遵守）】
1) 仅输出 JSON 对象，不要输出任何额外文字。
2) JSON 字段固定为：
{{
  "is_match": true/false,
  "confidence": 0-100 的整数,
  "reason": "不超过120字的判断依据",
  "evidence": ["来自文档的关键证据1", "证据2"]
}}
3) 若证据不足，is_match 必须为 false，且 confidence <= 40。
""".strip()


def normalize_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "yes", "y", "1", "是", "命中", "匹配"}:
            return True
        if v in {"false", "no", "n", "0", "否", "未命中", "不匹配"}:
            return False
    return None


def parse_model_json(raw_text: str) -> Dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("模型返回为空")

    # 去除代码块包裹
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()

    data = None
    try:
        data = json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = json.loads(text[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("无法解析为 JSON 对象")

    raw_match = data.get("is_match", data.get("match", data.get("label")))
    is_match = normalize_bool(raw_match)
    if is_match is None:
        raise ValueError(f"is_match 字段无效: {raw_match}")

    confidence = data.get("confidence", 50)
    try:
        confidence = int(confidence)
    except Exception:
        confidence = 50
    confidence = max(0, min(100, confidence))

    reason = str(data.get("reason", "")).strip()
    if not reason:
        reason = "模型未提供原因"

    evidence = data.get("evidence", [])
    if isinstance(evidence, str):
        evidence = [evidence]
    if not isinstance(evidence, list):
        evidence = []
    evidence = [str(x).strip() for x in evidence if str(x).strip()][:3]

    return {
        "is_match": is_match,
        "confidence": confidence,
        "reason": reason,
        "evidence": evidence,
    }


class AIClassifier:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.settings = config.get("Settings", {}) or {}
        self.interface_type = self.settings.get("interface_type", "openai_protocol")
        self.proxy = self.settings.get("proxy_url", None) or None
        self.max_text_chars = int(self.settings.get("max_text_chars", 120000))

        if self.proxy:
            os.environ["http_proxy"] = self.proxy
            os.environ["https_proxy"] = self.proxy

        gcfg = config.get("Google_Native_Config", {}) or {}
        self.google_input_method = str(gcfg.get("input_method", "upload")).lower()
        self.google_keys = gcfg.get("api_keys", []) or []
        self.google_model = gcfg.get("model_name", "gemini-2.5-flash")
        self.google_max_attempts = max(1, int(gcfg.get("max_attempts", 3)))

        ocfg = config.get("OpenAI_Protocol_Config", {}) or {}
        self.openai_input_method = str(ocfg.get("input_method", "text")).lower()
        self.openai_pool = ocfg.get("api_pool", []) or []
        self.openai_max_attempts = max(1, int(ocfg.get("max_attempts", 3)))
        self.files_api_path = str(ocfg.get("files_api_path", "/v1/files"))

        self.timeout_settings = aiohttp.ClientTimeout(
            total=CLIENT_TIMEOUT_SEC,
            connect=REQUEST_TIMEOUT_SEC,
            sock_connect=REQUEST_TIMEOUT_SEC,
            sock_read=REQUEST_TIMEOUT_SEC,
        )

    async def classify(self, file_path: str, system_prompt: str, question: str) -> Dict[str, Any]:
        if self.interface_type == "native_response":
            if not HAS_GOOGLE_GENAI:
                raise RuntimeError("未安装 google-genai 库，无法使用 native_response")
            if not self.google_keys:
                raise RuntimeError("Google_Native_Config.api_keys 为空")
            return await self._classify_gemini(file_path, system_prompt, question)

        if self.interface_type == "openai_protocol":
            if not self.openai_pool:
                raise RuntimeError("OpenAI_Protocol_Config.api_pool 为空")
            return await self._classify_openai(file_path, system_prompt, question)

        raise ValueError(f"未知 interface_type: {self.interface_type}")

    async def _classify_gemini(self, file_path: str, system_prompt: str, question: str) -> Dict[str, Any]:
        ext = Path(file_path).suffix.lower()
        for attempt in range(1, self.google_max_attempts + 1):
            api_key = self.google_keys[(attempt - 1) % len(self.google_keys)]
            try:
                client = genai.Client(api_key=api_key)
                cfg = types.GenerateContentConfig(temperature=0.0, system_instruction=system_prompt)

                if self.google_input_method == "upload" and ext == ".pdf":
                    tmp_upload_path, cleanup_tmp = make_ascii_temp_copy(file_path)
                    uploaded = None
                    try:
                        log(f"   -> [Gemini] upload 模式, key={mask_key(api_key)}", "cyan")
                        uploaded = await asyncio.to_thread(client.files.upload, file=tmp_upload_path)
                        while uploaded.state.name == "PROCESSING":
                            await asyncio.sleep(2)
                            uploaded = await asyncio.to_thread(client.files.get, name=uploaded.name)
                        if uploaded.state.name == "FAILED":
                            raise RuntimeError("Gemini 文件解析失败")

                        prompt = f"请判断该文档是否满足以下问题：{question}"
                        resp = await asyncio.to_thread(
                            client.models.generate_content,
                            model=self.google_model,
                            contents=[prompt, uploaded],
                            config=cfg,
                            timeout=REQUEST_TIMEOUT_SEC,
                        )
                    finally:
                        cleanup_tmp()
                        if uploaded is not None:
                            try:
                                await asyncio.to_thread(client.files.delete, name=uploaded.name)
                            except Exception:
                                pass
                else:
                    text = await extract_text(file_path)
                    text = clip_text_for_model(text, self.max_text_chars)
                    user_content = f"请判断该文档是否满足以下问题：{question}\n\n文档文本如下：\n{text}"
                    log(f"   -> [Gemini] text 模式, key={mask_key(api_key)}", "cyan")
                    resp = await asyncio.to_thread(
                        client.models.generate_content,
                        model=self.google_model,
                        contents=[user_content],
                        config=cfg,
                        timeout=REQUEST_TIMEOUT_SEC,
                    )

                model_text = getattr(resp, "text", "") or ""
                return parse_model_json(model_text)
            except Exception as e:
                log(f"⚠️ [Gemini] 第 {attempt} 次失败: {e}", "yellow")
                await asyncio.sleep(min(5, 1 + attempt))

        raise RuntimeError("Gemini 多次重试后仍失败")

    async def _classify_openai(self, file_path: str, system_prompt: str, question: str) -> Dict[str, Any]:
        ext = Path(file_path).suffix.lower()
        proxy = self.proxy if self.proxy else None

        async with aiohttp.ClientSession(timeout=self.timeout_settings) as session:
            for attempt in range(1, self.openai_max_attempts + 1):
                node = self.openai_pool[(attempt - 1) % len(self.openai_pool)]
                remark = node.get("remark", f"Node-{attempt}")
                base_url = node["base_url"]
                url = f"{base_url.rstrip('/')}{node['api_path']}"
                headers = {
                    "Authorization": f"Bearer {node['api_key']}",
                    "Content-Type": "application/json",
                }
                model = node["model_name"]
                try:
                    if self.openai_input_method == "upload" and ext == ".pdf":
                        log(f"   -> [OpenAI] upload 模式, 节点={remark}", "cyan")
                        raw = await self._openai_upload_once(
                            session=session,
                            url=url,
                            base_url=base_url,
                            headers=headers,
                            model=model,
                            file_path=file_path,
                            system_prompt=system_prompt,
                            question=question,
                            proxy=proxy,
                        )
                    else:
                        if self.openai_input_method == "upload" and ext != ".pdf":
                            log(f"⚠️ [OpenAI] 当前文件非 PDF，upload 模式自动回退 text：{Path(file_path).name}", "yellow")
                        log(f"   -> [OpenAI] text 模式, 节点={remark}", "cyan")
                        raw = await self._openai_text_once(
                            session=session,
                            url=url,
                            headers=headers,
                            model=model,
                            file_path=file_path,
                            system_prompt=system_prompt,
                            question=question,
                            proxy=proxy,
                        )
                    return parse_model_json(raw)
                except Exception as e:
                    log(f"⚠️ [OpenAI] 第 {attempt} 次失败（节点 {remark}）: {e}", "yellow")
                    if attempt < self.openai_max_attempts:
                        next_node = self.openai_pool[attempt % len(self.openai_pool)]
                        log(f"⚠️ 已切换到备用节点: {next_node.get('remark', 'Unknown')}", "yellow")
                    await asyncio.sleep(min(5, 1 + attempt))

        raise RuntimeError("OpenAI Protocol 多次重试后仍失败")

    async def _post_json(
        self,
        session: aiohttp.ClientSession,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        proxy: Optional[str],
    ) -> str:
        async with session.post(url, headers=headers, json=payload, proxy=proxy) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}: {text[:300]}")
            return self._parse_openai_response_text(text)

    def _parse_openai_response_text(self, text: str) -> str:
        try:
            data = json.loads(text)
        except Exception:
            raise RuntimeError(f"响应不是 JSON: {text[:300]}")

        if isinstance(data, dict) and data.get("choices"):
            try:
                return data["choices"][0]["message"]["content"]
            except Exception:
                pass

        if isinstance(data, dict) and isinstance(data.get("output_text"), str) and data["output_text"]:
            return data["output_text"]

        if isinstance(data, dict) and isinstance(data.get("output"), list):
            out = []
            for item in data.get("output", []):
                for c in item.get("content", []):
                    if c.get("type") in ("output_text", "text") and c.get("text"):
                        out.append(c["text"])
            if out:
                return "\n".join(out)

        raise RuntimeError(f"无法解析响应结构: {list(data.keys())[:30]}")

    async def _openai_text_once(
        self,
        session: aiohttp.ClientSession,
        url: str,
        headers: Dict[str, str],
        model: str,
        file_path: str,
        system_prompt: str,
        question: str,
        proxy: Optional[str],
    ) -> str:
        text = await extract_text(file_path)
        text = clip_text_for_model(text, self.max_text_chars)
        user_content = f"请判断该文档是否满足以下问题：{question}\n\n文档文本如下：\n{text}"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.0,
        }
        return await self._post_json(session, url, headers, payload, proxy)

    async def _upload_files_get_id(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        headers: Dict[str, str],
        file_path: str,
        proxy: Optional[str],
    ) -> str:
        upload_url = f"{base_url.rstrip('/')}{self.files_api_path}"
        form = aiohttp.FormData()
        form.add_field("purpose", "assistants")
        headers_no_ct = {k: v for k, v in headers.items() if k.lower() != "content-type"}

        with open(file_path, "rb") as f:
            form.add_field("file", f, filename=os.path.basename(file_path), content_type="application/octet-stream")
            async with session.post(upload_url, headers=headers_no_ct, data=form, proxy=proxy) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise RuntimeError(f"[files.upload] HTTP {resp.status}: {text[:300]}")
                data = json.loads(text)
                file_id = data.get("id") or data.get("file_id")
                if not file_id:
                    raise RuntimeError(f"[files.upload] 未返回 file_id: {data}")
                return str(file_id)

    async def _openai_generate_with_file_id(
        self,
        session: aiohttp.ClientSession,
        url: str,
        headers: Dict[str, str],
        model: str,
        file_id: str,
        system_prompt: str,
        question: str,
        proxy: Optional[str],
    ) -> str:
        user_text = f"请仅基于已上传附件回答：{question}"

        candidates = [
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                "file_ids": [file_id],
                "temperature": 0.0,
            },
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                "attachments": [{"file_id": file_id}],
                "temperature": 0.0,
            },
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_text},
                            {"type": "file", "file_id": file_id},
                        ],
                    },
                ],
                "temperature": 0.0,
            },
        ]

        last_err = None
        for payload in candidates:
            try:
                return await self._post_json(session, url, headers, payload, proxy)
            except Exception as e:
                last_err = e
        raise RuntimeError(f"file_id 引用失败: {last_err}")

    async def _openai_multipart_direct(
        self,
        session: aiohttp.ClientSession,
        url: str,
        headers: Dict[str, str],
        model: str,
        file_path: str,
        system_prompt: str,
        question: str,
        proxy: Optional[str],
    ) -> str:
        user_text = f"请仅基于本次上传附件判断：{question}"
        base_payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.0,
        }
        headers_no_ct = {k: v for k, v in headers.items() if k.lower() != "content-type"}

        async def parse_resp(resp: aiohttp.ClientResponse) -> str:
            text = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}: {text[:300]}")
            return self._parse_openai_response_text(text)

        async def try_payload_json() -> str:
            form = aiohttp.FormData()
            form.add_field("payload_json", json.dumps(base_payload, ensure_ascii=False))
            with open(file_path, "rb") as f:
                form.add_field("file", f, filename=os.path.basename(file_path), content_type="application/octet-stream")
                async with session.post(url, headers=headers_no_ct, data=form, proxy=proxy) as resp:
                    return await parse_resp(resp)

        async def try_messages_json() -> str:
            form = aiohttp.FormData()
            form.add_field("model", model)
            form.add_field("temperature", "0.0")
            form.add_field("system", system_prompt)
            form.add_field("messages_json", json.dumps(base_payload["messages"], ensure_ascii=False))
            with open(file_path, "rb") as f:
                form.add_field("files", f, filename=os.path.basename(file_path), content_type="application/octet-stream")
                async with session.post(url, headers=headers_no_ct, data=form, proxy=proxy) as resp:
                    return await parse_resp(resp)

        last_err = None
        for fn in (try_payload_json, try_messages_json):
            try:
                return await fn()
            except Exception as e:
                last_err = e
        raise RuntimeError(f"multipart 上传失败: {last_err}")

    async def _openai_upload_once(
        self,
        session: aiohttp.ClientSession,
        url: str,
        base_url: str,
        headers: Dict[str, str],
        model: str,
        file_path: str,
        system_prompt: str,
        question: str,
        proxy: Optional[str],
    ) -> str:
        # 方案 A：先 files.upload，再 file_id 引用
        try:
            file_id = await self._upload_files_get_id(session, base_url, headers, file_path, proxy)
            return await self._openai_generate_with_file_id(
                session, url, headers, model, file_id, system_prompt, question, proxy
            )
        except Exception as e:
            log(f"⚠️ [OpenAI] upload 方案A失败，尝试方案B: {e}", "yellow")

        # 方案 B：multipart 同请求直传
        return await self._openai_multipart_direct(
            session, url, headers, model, file_path, system_prompt, question, proxy
        )


def discover_files(source_dirs: List[str], recursive: bool) -> List[Tuple[Path, Path]]:
    found: List[Tuple[Path, Path]] = []
    for src in source_dirs:
        src_path = Path(src)
        if not src_path.exists():
            log(f"⚠️ 目录不存在，跳过: {src_path}", "yellow")
            continue

        pattern_fn = src_path.rglob if recursive else src_path.glob
        for ext in SUPPORTED_EXTS:
            for p in pattern_fn(f"*{ext}"):
                if p.is_file():
                    found.append((src_path, p))
    return sorted(found, key=lambda x: str(x[1]))


def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    return parent / f"{stem}_{ts}_{uuid.uuid4().hex[:6]}{suffix}"


def route_file(
    src_root: Path,
    src_file: Path,
    target_bucket_dir: Path,
    move_files: bool,
) -> Path:
    rel_parent = src_file.parent.relative_to(src_root)
    dst_dir = target_bucket_dir / src_root.name / rel_parent
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_path = ensure_unique_path(dst_dir / src_file.name)

    if move_files:
        shutil.move(str(src_file), str(dst_path))
    else:
        shutil.copy2(str(src_file), str(dst_path))
    return dst_path


async def worker(
    sem: asyncio.Semaphore,
    classifier: AIClassifier,
    src_root: Path,
    src_file: Path,
    system_prompt: str,
    question: str,
    dirs: Dict[str, Path],
    move_files: bool,
    records: List[Dict[str, Any]],
    lock: asyncio.Lock,
):
    async with sem:
        start = time.time()
        rec: Dict[str, Any] = {
            "source_root": str(src_root),
            "source_file": str(src_file),
            "status": "unknown",
            "is_match": None,
            "confidence": None,
            "reason": "",
            "evidence": [],
            "target_file": "",
            "error": "",
        }
        try:
            log(f"🔍 分类中: {src_file.name}", "cyan")
            result = await classifier.classify(str(src_file), system_prompt, question)

            rec["is_match"] = bool(result["is_match"])
            rec["confidence"] = int(result["confidence"])
            rec["reason"] = result["reason"]
            rec["evidence"] = result["evidence"]

            bucket = "yes" if rec["is_match"] else "no"
            rec["status"] = "ok"
            dst = route_file(src_root, src_file, dirs[bucket], move_files)
            rec["target_file"] = str(dst)
            log(f"✅ {src_file.name} -> {bucket.upper()} (confidence={rec['confidence']})", "green")
        except Exception as e:
            rec["status"] = "error"
            rec["error"] = str(e)
            try:
                dst = route_file(src_root, src_file, dirs["error"], move_files=False)
                rec["target_file"] = str(dst)
            except Exception as e2:
                rec["error"] = f"{e}; 路由失败: {e2}"
            log(f"❌ 分类失败: {src_file.name} | {e}", "red")
        finally:
            rec["elapsed_sec"] = round(time.time() - start, 2)
            async with lock:
                records.append(rec)


def save_reports(output_root: Path, records: List[Dict[str, Any]]) -> None:
    report_dir = output_root / DEFAULT_REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)

    ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    json_path = report_dir / f"classify_report_{ts}.json"
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    jsonl_path = report_dir / f"classify_report_{ts}.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    log(f"📝 报告已保存: {json_path}", "cyan")
    log(f"📝 报告已保存: {jsonl_path}", "cyan")


async def main():
    print("===========================================")
    print("      论文类型二分类器（配置兼容版）         ")
    print("===========================================")

    try:
        config = load_config()
    except Exception as e:
        log(f"❌ 读取配置失败: {e}", "red")
        return

    settings = config.get("Settings", {}) or {}
    source_dirs = settings.get("source_dirs", DEFAULT_SOURCE_DIRS)
    if not isinstance(source_dirs, list) or not source_dirs:
        source_dirs = DEFAULT_SOURCE_DIRS

    output_root = Path(settings.get("output_root", DEFAULT_OUTPUT_ROOT))
    yes_folder = str(settings.get("yes_folder", DEFAULT_YES_FOLDER))
    no_folder = str(settings.get("no_folder", DEFAULT_NO_FOLDER))
    err_folder = str(settings.get("error_folder", DEFAULT_ERR_FOLDER))
    move_files = bool(settings.get("move_files", False))
    recursive = bool(settings.get("recursive", False))
    concurrency = max(
        1,
        int(
            settings.get(
                "Document_Analysis_concurrency",
                settings.get("Classification_concurrency", 1),
            )
        ),
    )

    output_dirs = {
        "yes": output_root / yes_folder,
        "no": output_root / no_folder,
        "error": output_root / err_folder,
    }
    for d in output_dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    print("\n-------------------------------------------")
    classify_prompt = input("✍️ 请输入【分类提示词】(可留空): ").strip()
    question = input("✍️ 请输入【分类问题】(例如: 被解释变量是不是商业信用融资): ").strip()
    if not question:
        log("❌ 分类问题不能为空，程序退出。", "red")
        return

    files = discover_files(source_dirs, recursive=recursive)
    if not files:
        log("⚠️ 未发现可处理文件（支持: .pdf/.md/.txt）。", "yellow")
        return

    log(f"✅ 发现待分类文件: {len(files)} 个", "green")
    log(f"模式: provider={settings.get('interface_type', 'openai_protocol')} | 并发={concurrency}", "cyan")
    log(f"输出目录: {output_root}", "cyan")

    system_prompt = build_system_prompt(classify_prompt=classify_prompt, question=question)
    classifier = AIClassifier(config)

    sem = asyncio.Semaphore(concurrency)
    records: List[Dict[str, Any]] = []
    lock = asyncio.Lock()

    tasks = [
        worker(
            sem=sem,
            classifier=classifier,
            src_root=src_root,
            src_file=src_file,
            system_prompt=system_prompt,
            question=question,
            dirs=output_dirs,
            move_files=move_files,
            records=records,
            lock=lock,
        )
        for src_root, src_file in files
    ]
    await asyncio.gather(*tasks)

    save_reports(output_root=output_root, records=records)

    ok = [r for r in records if r["status"] == "ok"]
    yes = [r for r in ok if r["is_match"] is True]
    no = [r for r in ok if r["is_match"] is False]
    err = [r for r in records if r["status"] != "ok"]

    print("\n===========================================")
    print("分类完成")
    print("===========================================")
    print(f"总数: {len(records)}")
    print(f"命中: {len(yes)}")
    print(f"未命中: {len(no)}")
    print(f"异常: {len(err)}")
    print(f"结果目录: {output_root}")


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
