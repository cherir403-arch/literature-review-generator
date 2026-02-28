# -*- coding: utf-8 -*-
import os
import sys
import io
import json
import asyncio
import aiohttp
import time
import re
import tempfile
import shutil

# ==========================================
# 强制全局 UTF-8 编码环境
# ==========================================
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    if getattr(sys.stdout, "encoding", None) and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    from google import genai
    from google.genai import types
    HAS_GOOGLE_GENAI = True
except Exception:
    HAS_GOOGLE_GENAI = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

# ==========================================
# 1. 基础配置与文件夹设定
# ==========================================
CONFIG_FILENAME = "6.研究缺口.json"
DIR_INPUT_CONCEPT = "5.3概念资料库"      # 放关于该概念的文献(PDF)、摘要集合
DIR_OUTPUT_CONCEPT = "5.4概念分析报告"   # 输出最终概念解构报告的文件夹

CLIENT_TIMEOUT_SEC = 1800000
REQUEST_TIMEOUT_SEC = 1800000

# ==========================================
# 2. 概念深度解构提示词
# ==========================================
PROMPT_TEMPLATE = """
# Role: 资深学术编辑与理论构建专家
专长：政策评估、制度经济学、SSCI 范式分析。
任务：基于提供的【政策文件与相关资料库】，对特定中国政策“{policy_name}”进行严谨的两阶段解构，生成一份具有 SSCI 期刊水准的背景报告。

【输入设定】
1. 政策名称：{policy_name}
2. 核心变量/概念定义：{define_A}
3. 资料库来源：{source_declaration}

# 约束与风格
1. 语气：高度学术、分析性、客观且批判性。严禁口语化或描述性文字。
2. 数据源：严格基于提供的文本库/附件进行提取与互证。不需要（也不得）利用外部搜索功能，所有引用必须在提供的资料中可溯源。
3. 论证深度：不仅要罗列事实，更要透析政策背后的“目的论（Teleology）”与“结构性差异”。
4. 取消暂停：请一次性输出完整的分析报告。

---

# Step-by-Step Instructions (执行逻辑)

### 第 1 部分：经验性政策分析（基于给定资料库）
说明：从提供的文件中提取并综合关键事实，要求精准。

1. 实施时间线：确定“{policy_name}”作为试点政策首次实施的确切年份与里程碑节点。
2. 目的论分析（政策目标）：综述政策实施者试图通过该政策解决的根本问题及预期达成的目的。
3. 概念解构：
   - 定义：根据文本，提供对“{define_A}”的精确学术定义。
   - 操作化：概述该概念在政策框架中如何具体呈现或量化（列出关键指标/维度）。
4. 试点对象识别：澄清试点的分析单元（是特定行政区划，还是特定市场主体/企业？）。
5. 比较特征分析（核心判定）：分析受试对象（试点组）与非受试对象（控制组）之间的本质性差异。
   - 若存在显著差异，请用学术术语概括（如“资源禀赋”、“行政层级”、“要素集聚”）。
   - 若结构上高度相似，请明确判定为：“Institutional Isomorphism”（制度同形性）。

### 第 2 部分：理论抽象与普遍悖论（基于资料库中的理论线索）
说明：将具体的中国政策内容拆解为全球学术界通用的“政策工具（Policy Tools）”。
注意：这里的政策工具并非是抽象的工具，而是实实在在已经在国家或地区层面广泛使用的政策工具的名称，例如：数字化税收、资源税政策等

6. 全球文献范畴内的工具界定（拆政策）：
步骤1：“拆”政策
将该政策的主要内容归类为某几项在全球文献中被界定的特定政策工具或机制（例如：中国的水资源费改水资源税政策可以归类为全球文献中的“水资源税”或者“资源税”；而中国的金税三期政策则通常被概括为“数字化税收征管”等等）。
根据资料库中的描述，将“{policy_name}”映射或解构为 1-3 个在全球 SSCI 文献中有具体定义的政策工具（如：Environmental Taxation, Algorithmic Governance等）。
*注意*：应该拆解为一种或者几种有具体名称的具体政策工具，而不是像“Intergovernmental transfers & fiscal equalisation”这种概念化的东西（“Intergovernmental transfers & fiscal equalisation”这样表述是不对的，但是可以表述为“Fiscal transfer payment”这种具体的政策工具）
*说明*：“{policy_name}”这项中国政策可能是一个综合的政策，其中的措施和相关的内容可能同时指向全球文献中被界定的几种特定政策工具或机制。这一步的目的是将“{policy_name}”这项中国政策进行拆解，并结合政策文件本身的相关内容，说明“{policy_name}”这项政策里的“工具包”拆分后，可能拆出的几项主要全球文献中被界定的几种特定政策工具或机制。
步骤2：全球辩证——“双刃剑”：
分别分析每一项特定政策工具或机制在全球实践中可能出现的积极效应与消极后果：
- 光明面（功能性）：全球人们建立这种特定政策工具或机制的目的是解决哪些根本的、普遍的问题？（列出3项最要紧的正面外部性，例如：内部化外部性损失、克服公地悲剧等）。
- 阴影面（功能失调）：这种特定政策工具或机制在全球实行的过程中诞生了哪些伴生性的消极问题？（列出3项最重要的负面外部性/意外后果，例如：绿色剥夺现象、贫富差距扩大、产生环境难民等）。
是如何产生的：
*说明*：“双刃剑”的阐述是该类型工具或机制在全球实践中存在的普遍结构性困境，与中国“{policy_name}”这项政策语境无关。

7. 多视角系统性总结：
   从以下 9 个维度剖析“{policy_name}”：三个学科视角、三个具体理论/假说、三个自由视角（自由视角无固定限制，主要用来补充具体范式下无法识别的关键信息）。这一部分需要500-600字。

### 第 3 部分：参考文献引用规范
1. 引用格式：在句中使用 (Author, Year) [编号] 进行标注。
2. 约束：一句话最多引用两篇文献；一篇文献在报告中仅限引用一次；观点句必须有据可查。
3. 参考文献列表：按 GB/T 7714-2015 格式列于末尾。必须是资料库中提供的文献，包含对应的 DOI 号（如资料中有提供）。

---

# Output Format (输出要求)
请以 Markdown 格式输出，标题层级使用 ###。确保分析文本连贯、经专家整合，而非碎片化列举。
"""

# ==========================================
# 3. 辅助函数：扫描、解析与交互
# ==========================================
def log(msg, color="white"):
    colors = {"green": "\033[92m", "cyan": "\033[96m", "yellow": "\033[93m", "red": "\033[91m"}
    print(f"{colors.get(color, '')}[{time.strftime('%H:%M:%S')}] {msg}\033[0m")

async def show_heartbeat(start_time, stop_event, mode_msg="进行概念深度解构"):
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    i = 0
    while not stop_event.is_set():
        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)
        frame = spinner[i % len(spinner)]
        sys.stdout.write(f"\r\033[93m[{time.strftime('%H:%M:%S')}] {frame} 🧠 AI 正在{mode_msg}... 已耗时: {mins:02d}分{secs:02d}秒\033[0m")
        sys.stdout.flush()
        i += 1
        await asyncio.sleep(0.1)
    sys.stdout.write("\r" + " " * 110 + "\r")
    sys.stdout.flush()

def get_files_from_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        return []
    valid_exts = (".pdf", ".md", ".txt")
    return [os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith(valid_exts)]

def read_text_from_files(filepaths):
    combined_text = ""
    for filepath in filepaths:
        filename = os.path.basename(filepath)
        if filepath.lower().endswith(".pdf"):
            if not HAS_PDFPLUMBER:
                log(f"⚠️ 缺少 pdfplumber 库，跳过 PDF: {filename}。请执行: pip install pdfplumber", "yellow")
                continue
            try:
                import warnings
                warnings.filterwarnings("ignore", category=UserWarning)
                with pdfplumber.open(filepath) as pdf:
                    pdf_text = ""
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted:
                            pdf_text += extracted + "\n"
                combined_text += f"\n\n============= 【PDF 原文：{filename}】 =============\n{pdf_text}\n"
            except Exception as e:
                log(f"⚠️ 无法读取 PDF {filename}: {e}", "yellow")
        else:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    combined_text += f"\n\n============= 【文本来源：{filename}】 =============\n{f.read()}\n"
            except Exception as e:
                log(f"⚠️ 无法读取文本 {filename}: {e}", "yellow")
    return combined_text

def read_extra_prompt_from_config(config: dict) -> str:
    """
    预设提示词：从配置读取路径并读取文件内容（可选）
    优先级：
      Settings.extra_prompt_path
      OpenAI_Protocol_Config.extra_prompt_path
      Google_Native_Config.extra_prompt_path
    """
    settings = config.get("Settings", {}) or {}
    ocfg = config.get("OpenAI_Protocol_Config", {}) or {}
    gcfg = config.get("Google_Native_Config", {}) or {}

    path = settings.get("extra_prompt_path") or ocfg.get("extra_prompt_path") or gcfg.get("extra_prompt_path") or ""
    path = str(path).strip()
    if not path:
        return ""

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            return content
    except Exception as e:
        log(f"⚠️ 无法读取预设提示词文件 {path}: {e}", "yellow")
    return ""

def merge_prompt(base_prompt: str, extra_prompt: str) -> str:
    extra_prompt = (extra_prompt or "").strip()
    if not extra_prompt:
        return base_prompt
    return base_prompt + "\n\n---\n\n# Extra Preset Prompt (预设补充指令)\n" + extra_prompt + "\n"

# ==========================================
# 4. API 调用核心逻辑
#    - Gemini: 支持多PDF上传（原生 upload）/ 或 text
#    - OAI Protocol: 支持多方式直传PDF（A: /v1/files file_id 引用；B: multipart 直传；回退 text）
#    - 同一任务：多个PDF + 一份预设提示词（extra prompt）一起作为一个任务输入
# ==========================================
async def process_with_ai(filepaths, final_prompt, config):
    settings = config.get("Settings", {})
    provider = settings.get("interface_type", "openai_protocol")
    proxy_url = settings.get("proxy_url", "")

    if proxy_url:
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url

    # 读取预设提示词，并合并进 final_prompt（同一任务一起生效）
    extra_prompt = read_extra_prompt_from_config(config)
    final_prompt = merge_prompt(final_prompt, extra_prompt)

    # -----------------------------
    # A) Google Native
    # -----------------------------
    if provider == "native_response" and HAS_GOOGLE_GENAI:
        gcfg = config.get("Google_Native_Config", {})
        input_method = str(gcfg.get("input_method", "text")).lower()
        max_attempts = max(1, int(gcfg.get("max_attempts", 3)))
        api_keys = gcfg.get("api_keys", [])
        model_name = gcfg.get("model_name", "gemini-2.5-flash")

        if not api_keys:
            raise ValueError("Google_Native_Config 中未提供 api_keys。")

        for attempt in range(max_attempts):
            current_key = api_keys[attempt % len(api_keys)]
            client = genai.Client(api_key=current_key, http_options={'timeout': REQUEST_TIMEOUT_SEC})

            try:
                if input_method == "upload":
                    uploaded_files = []
                    local_temp_paths = []

                    log(f"-> [Attempt {attempt+1}/{max_attempts}] 正在构建安全编码并上传 {len(filepaths)} 个文件...", "cyan")
                    try:
                        for fp in filepaths:
                            # 核心修复：创建纯 ASCII 名称的临时文件用于上传（避免中文文件名/路径触发 header 编码问题）
                            ext = os.path.splitext(fp)[1]
                            temp_fd, temp_path = tempfile.mkstemp(suffix=ext, prefix="gemini_temp_")
                            os.close(temp_fd)
                            shutil.copy2(fp, temp_path)
                            local_temp_paths.append(temp_path)

                            uf = await asyncio.to_thread(client.files.upload, file=temp_path)
                            uploaded_files.append(uf)

                        # 等待云端就绪
                        for i in range(len(uploaded_files)):
                            uf = uploaded_files[i]
                            while uf.state.name == "PROCESSING":
                                await asyncio.sleep(2)
                                uf = await asyncio.to_thread(client.files.get, name=uf.name)
                            uploaded_files[i] = uf

                        log(f"-> 上传完毕。AI 正在提取并解构概念文献...", "cyan")
                        cfg = types.GenerateContentConfig(temperature=0.3, system_instruction=final_prompt)

                        # 同一任务：多个PDF + 预设提示词（已合并在 system_instruction）
                        contents = uploaded_files + ["请严格基于上述所有附件执行概念解构指令（禁止联网）。"]
                        resp = await asyncio.to_thread(client.models.generate_content, model=model_name, contents=contents, config=cfg)
                        return resp.text

                    finally:
                        # 清理云端与本地缓存
                        for uf in uploaded_files:
                            try:
                                await asyncio.to_thread(client.files.delete, name=uf.name)
                            except:
                                pass
                        for tp in local_temp_paths:
                            try:
                                os.remove(tp)
                            except:
                                pass

                else:
                    # Native 的 Text 模式（多文件合并纯文本）
                    log(f"-> [Attempt {attempt+1}/{max_attempts}] 本地提取内容并发送...", "cyan")
                    combined_context = read_text_from_files(filepaths)
                    if not combined_context.strip():
                        raise Exception("提取文本为空，请检查文件。")
                    full_message = f"请基于以下【概念资料库】分析：\n\n{combined_context}"
                    cfg = types.GenerateContentConfig(temperature=0.3, system_instruction=final_prompt)
                    resp = await asyncio.to_thread(client.models.generate_content, model=model_name, contents=[full_message], config=cfg)
                    return resp.text

            except Exception as e:
                log(f"⚠️ 第 {attempt + 1} 次请求失败 (Key: {current_key[:6]}...): {e}", "yellow")
                if attempt == max_attempts - 1:
                    raise Exception("已达到最大重试次数，所有可用 Key 均失败。")
                await asyncio.sleep(3)

    # -----------------------------
    # B) OpenAI Protocol / 中转站（多方式直传PDF）
    # -----------------------------
    else:
        ocfg = config.get("OpenAI_Protocol_Config", {})
        max_attempts = max(1, int(ocfg.get("max_attempts", 3)))
        api_pool = ocfg.get("api_pool", [])
        input_method = str(ocfg.get("input_method", "text")).lower()  # "upload" / "text"

        if not api_pool:
            raise ValueError("OpenAI_Protocol_Config 中未提供 api_pool。")

        proxy = proxy_url if proxy_url else None
        timeout_settings = aiohttp.ClientTimeout(total=CLIENT_TIMEOUT_SEC, sock_read=REQUEST_TIMEOUT_SEC)

        # ---------- JSON 发起 + 响应解析（兼容多种返回结构） ----------
        async def _post_json(session: aiohttp.ClientSession, url: str, headers: dict, payload: dict) -> str:
            async with session.post(url, headers=headers, json=payload, proxy=proxy) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}: {text}")
                try:
                    data = json.loads(text)
                except Exception:
                    raise Exception(f"响应不是 JSON: {text[:300]}")

                # chat.completions
                if isinstance(data, dict) and "choices" in data and data["choices"]:
                    try:
                        return data["choices"][0]["message"]["content"]
                    except Exception:
                        pass

                # responses 风格：output_text
                if isinstance(data, dict) and isinstance(data.get("output_text"), str) and data["output_text"]:
                    return data["output_text"]

                # responses 风格：output 数组
                if isinstance(data, dict) and isinstance(data.get("output"), list):
                    out = []
                    for item in data.get("output", []):
                        for c in item.get("content", []):
                            if c.get("type") in ("output_text", "text") and c.get("text"):
                                out.append(c["text"])
                    if out:
                        return "\n".join(out)

                raise Exception(f"无法从响应中解析文本内容：{list(data.keys())[:30]}")

        # ---------- Text 回退（多文件合并纯文本） ----------
        async def _text_generate(session: aiohttp.ClientSession, url: str, headers: dict, model: str) -> str:
            log("-> [Text 模式] 正在本地提取所有文件纯文本...", "cyan")
            combined_context = read_text_from_files(filepaths)
            if not combined_context.strip():
                raise Exception("提取文本为空，请检查文件。")
            full_message = f"请基于以下【概念资料库】分析：\n\n{combined_context}"

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": final_prompt},
                    {"role": "user", "content": full_message}
                ],
                "temperature": 0.3
            }
            return await _post_json(session, url, headers, payload)

        # ---------- 方案 A：/v1/files 上传获取 file_id（多文件） ----------
        async def _upload_files_get_ids(session: aiohttp.ClientSession, base_url: str, headers: dict, files: list) -> list:
            upload_path = str(ocfg.get("files_api_path", "/v1/files"))
            upload_url = f"{base_url.rstrip('/')}{upload_path}"

            file_ids = []
            for fp in files:
                filename = os.path.basename(fp)

                form = aiohttp.FormData()
                form.add_field("purpose", "assistants")

                fobj = open(fp, "rb")
                try:
                    form.add_field("file", fobj, filename=filename, content_type="application/octet-stream")
                    headers_no_ct = {k: v for k, v in headers.items() if k.lower() != "content-type"}
                    async with session.post(upload_url, headers=headers_no_ct, data=form, proxy=proxy) as resp:
                        text = await resp.text()
                        if resp.status != 200:
                            raise Exception(f"[files.upload] HTTP {resp.status}: {text}")
                        data = json.loads(text)
                        fid = data.get("id") or data.get("file_id")
                        if not fid:
                            raise Exception(f"[files.upload] 未返回 file id：{data}")
                        file_ids.append(fid)
                finally:
                    try:
                        fobj.close()
                    except:
                        pass

            return file_ids

        # ---------- 方案 A：引用 file_id 生成（多 payload 探测，多文件） ----------
        async def _generate_with_file_ids(session: aiohttp.ClientSession, url: str, headers: dict, model: str, file_ids: list) -> str:
            user_text = "请严格基于已上传的所有附件执行概念解构指令（禁止联网）。"
            candidates = []

            # 1) 顶层 file_ids（部分中转支持）
            candidates.append({
                "model": model,
                "messages": [
                    {"role": "system", "content": final_prompt},
                    {"role": "user", "content": user_text}
                ],
                "file_ids": file_ids,
                "temperature": 0.3
            })

            # 2) attachments: [{file_id: ...}]
            candidates.append({
                "model": model,
                "messages": [
                    {"role": "system", "content": final_prompt},
                    {"role": "user", "content": user_text}
                ],
                "attachments": [{"file_id": fid} for fid in file_ids],
                "temperature": 0.3
            })

            # 3) content 数组（多模态：text + file_id）
            candidates.append({
                "model": model,
                "messages": [
                    {"role": "system", "content": final_prompt},
                    {"role": "user", "content": (
                        [{"type": "text", "text": user_text}] +
                        [{"type": "file", "file_id": fid} for fid in file_ids]
                    )}
                ],
                "temperature": 0.3
            })

            last_err = None
            for payload in candidates:
                try:
                    return await _post_json(session, url, headers, payload)
                except Exception as e:
                    last_err = e
            raise Exception(f"引用 file_id 生成失败（已尝试 {len(candidates)} 种 payload）：{last_err}")

        # ---------- 方案 B：multipart 同请求直传（多文件） ----------
        async def _multipart_generate_direct(session: aiohttp.ClientSession, url: str, headers: dict, model: str) -> str:
            user_text = "请严格基于本次随请求上传的所有附件执行概念解构指令（禁止联网）。"
            base_payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": final_prompt},
                    {"role": "user", "content": user_text}
                ],
                "temperature": 0.3
            }

            headers_no_ct = {k: v for k, v in headers.items() if k.lower() != "content-type"}

            async def _parse_resp(resp: aiohttp.ClientResponse) -> str:
                text = await resp.text()
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}: {text}")
                data = json.loads(text)
                if "choices" in data and data["choices"]:
                    return data["choices"][0]["message"]["content"]
                if "output_text" in data and isinstance(data["output_text"], str):
                    return data["output_text"]
                if "output" in data and isinstance(data["output"], list):
                    out = []
                    for item in data.get("output", []):
                        for c in item.get("content", []):
                            if c.get("type") in ("output_text", "text") and c.get("text"):
                                out.append(c["text"])
                    if out:
                        return "\n".join(out)
                raise Exception(f"无法解析 multipart 响应：{list(data.keys())[:30]}")

            # 形态 1：payload_json + file(同名多次)
            async def try_payload_json() -> str:
                form = aiohttp.FormData()
                form.add_field("payload_json", json.dumps(base_payload, ensure_ascii=False))

                fobjs = []
                try:
                    for fp in filepaths:
                        fobj = open(fp, "rb")
                        fobjs.append(fobj)
                        form.add_field("file", fobj, filename=os.path.basename(fp), content_type="application/octet-stream")

                    async with session.post(url, headers=headers_no_ct, data=form, proxy=proxy) as resp:
                        return await _parse_resp(resp)
                finally:
                    for f in fobjs:
                        try:
                            f.close()
                        except:
                            pass

            # 形态 2：messages_json + files(多次)
            async def try_messages_json() -> str:
                form = aiohttp.FormData()
                form.add_field("model", model)
                form.add_field("temperature", "0.3")
                form.add_field("system", final_prompt)
                form.add_field("messages_json", json.dumps(base_payload["messages"], ensure_ascii=False))

                fobjs = []
                try:
                    for fp in filepaths:
                        fobj = open(fp, "rb")
                        fobjs.append(fobj)
                        form.add_field("files", fobj, filename=os.path.basename(fp), content_type="application/octet-stream")

                    async with session.post(url, headers=headers_no_ct, data=form, proxy=proxy) as resp:
                        return await _parse_resp(resp)
                finally:
                    for f in fobjs:
                        try:
                            f.close()
                        except:
                            pass

            last_err = None
            for fn in (try_payload_json, try_messages_json):
                try:
                    return await fn()
                except Exception as e:
                    last_err = e
            raise Exception(f"multipart 直传失败：{last_err}")

        # ========== 主循环：按节点重试 ==========
        for attempt in range(max_attempts):
            node = api_pool[attempt % len(api_pool)]
            base_url = node["base_url"]
            url = f"{base_url.rstrip('/')}{node['api_path']}"
            headers = {"Authorization": f"Bearer {node['api_key']}", "Content-Type": "application/json"}
            model = node["model_name"]

            try:
                log(f"-> [Attempt {attempt+1}/{max_attempts}] 发送至中转站节点 ({model})...", "cyan")
                async with aiohttp.ClientSession(timeout=timeout_settings) as session:
                    if input_method == "upload":
                        # 方案 A：/v1/files -> file_id 引用
                        try:
                            log("-> 尝试方案A：/v1/files 先上传再引用 file_id（多文件）...", "cyan")
                            file_ids = await _upload_files_get_ids(session, base_url, headers, filepaths)
                            log(f"-> 上传成功，获得 {len(file_ids)} 个 file_id，开始引用生成...", "cyan")
                            return await _generate_with_file_ids(session, url, headers, model, file_ids)
                        except Exception as eA:
                            log(f"⚠️ 方案A失败：{eA}", "yellow")

                        # 方案 B：multipart 同请求直传（多文件）
                        try:
                            log("-> 尝试方案B：multipart 同请求直传文件流（多文件）...", "cyan")
                            return await _multipart_generate_direct(session, url, headers, model)
                        except Exception as eB:
                            log(f"⚠️ 方案B失败：{eB}", "yellow")

                        # 回退 text
                        log("-> 两种 upload 均失败，回退到 text 模式 ...", "yellow")
                        return await _text_generate(session, url, headers, model)

                    # 非 upload：保持原功能（text）
                    return await _text_generate(session, url, headers, model)

            except Exception as e:
                log(f"⚠️ 第 {attempt + 1} 次请求失败: {e}", "yellow")
                if attempt == max_attempts - 1:
                    raise Exception("已达到最大重试次数，所有节点均失败。")
                next_node = api_pool[(attempt + 1) % len(api_pool)]
                next_remark = next_node.get("remark", f"Node-{(attempt + 1) % len(api_pool) + 1}")
                log(f"⚠️ 已切换到备用节点: {next_remark}", "yellow")
                await asyncio.sleep(3)

# ==========================================
# 5. 主程序
# ==========================================
async def main():
    print("===========================================")
    print("      🧠 工业级：SSCI 概念深度解构系统       ")
    print("===========================================")
    os.makedirs(DIR_INPUT_CONCEPT, exist_ok=True)
    os.makedirs(DIR_OUTPUT_CONCEPT, exist_ok=True)

    try:
        with open(CONFIG_FILENAME, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception:
        log("❌ 找不到配置文件 1.逐篇_config.json", "red")
        return

    filepaths = get_files_from_dir(DIR_INPUT_CONCEPT)
    if not filepaths:
        log(f"⚠️ 文件夹 [{DIR_INPUT_CONCEPT}] 中没有找到文件。请放入关于该概念的 PDF/MD/TXT 文件后重新运行。", "yellow")
        return

    log(f"✅ 成功读取 {len(filepaths)} 份核心文献资料。", "green")

    print("\n-------------------------------------------")
    concept_name = input("✍️  请输入【要解构的核心概念】 (例如: 商业信用融资 / 绿色洗脱 / 组织韧性): ").strip()
    if not concept_name:
        log("❌ 输入信息为空，程序退出。", "red")
        return

    # 动态判定声明词
    provider = config.get("Settings", {}).get("interface_type", "openai_protocol")
    if provider == "native_response":
        input_method = str(config.get("Google_Native_Config", {}).get("input_method", "text")).lower()
    else:
        input_method = str(config.get("OpenAI_Protocol_Config", {}).get("input_method", "text")).lower()

    # 预设提示词存在性（仅用于声明，不改变逻辑）
    extra_prompt_path = (
        (config.get("Settings", {}) or {}).get("extra_prompt_path")
        or (config.get("OpenAI_Protocol_Config", {}) or {}).get("extra_prompt_path")
        or (config.get("Google_Native_Config", {}) or {}).get("extra_prompt_path")
        or ""
    )
    has_extra = bool(str(extra_prompt_path).strip())

    if provider == "native_response" and input_method == "upload":
        source_declaration = "已将原生文献 PDF 阵列作为附件上传至系统。"
        mode_msg = "调用原生多模态引擎进行文献解构"
    elif provider != "native_response" and input_method == "upload":
        source_declaration = "已通过 OpenAI 协议兼容中转接口尝试上传附件（将自动回退至文本合并模式）。"
        mode_msg = "调用中转站上传/多模态兼容路径进行解构"
    else:
        source_declaration = "已在下方上下文中提供所有文献的合并纯文本提取。"
        mode_msg = "基于本地文献库进行解构"

    if has_extra:
        source_declaration += "（并已加载一份预设提示词作为同任务补充约束）"

    final_prompt = PROMPT_TEMPLATE.format(
        Concept=concept_name,
        source_declaration=source_declaration
    )

    stop_event = asyncio.Event()
    start_time = time.time()
    heartbeat_task = asyncio.create_task(show_heartbeat(start_time, stop_event, mode_msg=mode_msg))

    try:
        result = await process_with_ai(filepaths, final_prompt, config)

        safe_name = concept_name.replace("/", "_").replace("\\", "_")[:20]
        output_path = os.path.join(DIR_OUTPUT_CONCEPT, f"Step8_{safe_name}_概念解构报告.md")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# SSCI 级概念变量深度解构：{concept_name}\n\n")
            f.write(f"> 融合文献份数：{len(filepaths)} 份 ({input_method.upper()} 模式)\n")
            if has_extra:
                f.write(f"> 预设提示词：已加载（{extra_prompt_path}）\n")
            f.write("\n")
            f.write(result)

        stop_event.set()
        await heartbeat_task
        log(f"🎉 报告生成成功！理论框架已保存至: {output_path}", "green")
    except Exception as e:
        stop_event.set()
        await heartbeat_task
        log(f"❌ 任务彻底失败: {e}", "red")

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
