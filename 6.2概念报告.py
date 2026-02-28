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
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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
# Role: SSCI 顶级期刊副主编 & 讲席教授
专长：理论构建、定量实证反思、批判性思维。
任务：基于提供的【核心文献资料库】，对特定概念“{Concept}”进行系统性的理论解构与升华。

【输入设定】
1. 核心概念：{Concept}
2. 资料库来源：{source_declaration}

# Core Philosophy
你认为学术研究不应止于描述，而应致力于发现理论悖论。你的分析风格：由表及里、跨学科交织、通过实证结果反思理论边界。

# Constraints
1. 资料源：严格基于提供的文本库/附件进行提取与互证。关闭实时联网搜索，所有论点必须在资料库中有据可依。
2. 引用规范：严格遵守 APA 格式。一句话最多引用两篇文献；一篇文献仅限引用一次；观点句、理论句必须引用。
3. 定量导向：优先采纳资料库中的定量研究（Quantitative Research）证据。
4. 取消暂停：请一次性输出完整的深度解构报告。

---
[CONTEXT]
我正在撰写一篇关于概念“{Concept}”的 SSCI 一区级研究论文。附件 PDF 是目前学术界对“{Concept}”的重点研究论文和相关资料。
[TASK]
请调用你深度推理能力，执行以下系统性深度解构工作流。请确保回答不夹杂其他无关变量，保持概念的独立性。
1. 核心定义归纳 (Ontological Definition)：
从本体论角度总结{Concept}的准确定义。请清晰界定其内涵（核心特征）与外延（适用范围），重点区分其作为“理论概念”与“衡量指标”的不同。
2. 宏观维度自主剖析 (Autonomous Macro-Mapping)：
这是一项战略性任务，请按以下步骤执行，不要直接回答：
 Step 1 深度扫描：结合 PDF 内容以及参考文献内容，总结3个与概念最匹配的宏观视角。
 Step 2 价值评估：在 `<thinking>` 标签内，评估哪一个维度最能提升本研究的立意，使其符合 SSCI 期刊对“大问题”的偏好。
 Step 3 最终阐述：自主选择一个最佳维度，建立孤立概念{Concept}与该宏观视角的逻辑联系。你需要阐述：
 选择理由：为何该视角能最大化理论贡献？
 逻辑映射：{Concept}是如何作为微观机制嵌入并影响该宏观表现的
3. 现象级学术扩展 (Phenomenon F)：
将{Concept}扩展到一个与上述宏观层面相关的现象 “F”。详细阐述{Concept}与 “F” 之间的因果链条或逻辑演化。该分析应具有超越狭隘时空的普适性，为全球学术研究提供借鉴。
4. 性质规范性评估 (Normative Assessment)：
基于文本逻辑，判定{Concept}的本质属性（积极、中性或消极），并提供理由。
5. 学术关注动因分析 (Epistemological Reasons)：
阐述{Concept}议题在当前学术语境下受到关注的深层原因（如：理论缺失、现实冲突或政策转型等）。
6. 九维系统性综述 (9-Dimensional Matrix)：
这是本报告的核心，需展现高级博士水平的批判性思考，将经验性政策与理论悖论连接起来。请从以下九个维度深度剖析{Concept}：
 3 个学科视角：
 3 个具体理论/假说：(引入 3 个相互竞争或互补的经典理论框架进行解释)
 3 个自由视角：(自主识别具体范式无法捕捉的关键信息，如非线性关系、阈值效应或文化情境)
7. 参考文献与引证 (References & Citations)：
（1）以 (Author, Year) [n]的格式，标注参考内容。并在(Author, Year) [n]标注好对应参考列表中的哪一篇文章，以便于查找
（2）一句话只能对应引用最多两篇文献。
（3）一篇文献只能提供一句话引用，不可重复引用。
（4）观点句、理论句必须进行引用。
（5）在末尾，以 GB/T 7714-2015 格式列示参考文献列表
[OUTPUT STRUCTURE]
请按以下格式输出：
一、 概念深度解构
(包含任务 1-5 的内容)
二、 九维系统性综述
(包含任务 6 的内容)
三、 参考文献
(包含任务 7 的内容，GB/T 7714-2015 格式列表)
[1] ...
[2] ...
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
        sys.stdout.write(
            f"\r\033[93m[{time.strftime('%H:%M:%S')}] {frame} 🧠 AI 正在{mode_msg}... 已耗时: {mins:02d}分{secs:02d}秒\033[0m"
        )
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

# ==========================================
# 4. API 调用核心逻辑 (修复中文名上传 Bug + 轮询重试)
#    + OpenAI Protocol 分支新增：先 A(file_id) 后 B(multipart) 再 text 回退
# ==========================================
async def process_with_ai(filepaths, final_prompt, config):
    settings = config.get("Settings", {})
    provider = settings.get("interface_type", "openai_protocol")
    proxy_url = settings.get("proxy_url", "")

    if proxy_url:
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url

    # -----------------------------
    # A) Google Native
    # -----------------------------
    if provider == "native_response" and HAS_GOOGLE_GENAI:
        gcfg = config.get("Google_Native_Config", {})
        input_method = gcfg.get("input_method", "text")
        max_attempts = max(1, gcfg.get("max_attempts", 3))
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
                            # 核心修复：创建纯 ASCII 名称的临时文件用于上传
                            ext = os.path.splitext(fp)[1]
                            temp_fd, temp_path = tempfile.mkstemp(suffix=ext, prefix="gemini_temp_")
                            os.close(temp_fd)
                            shutil.copy2(fp, temp_path)
                            local_temp_paths.append(temp_path)

                            uf = await asyncio.to_thread(client.files.upload, file=temp_path)
                            uploaded_files.append(uf)

                        # 等待云端就绪
                        for uf in uploaded_files:
                            while uf.state.name == "PROCESSING":
                                await asyncio.sleep(2)
                                uf = await asyncio.to_thread(client.files.get, name=uf.name)

                        log(f"-> 上传完毕。AI 正在提取并解构概念文献...", "cyan")
                        cfg = types.GenerateContentConfig(temperature=0.3, system_instruction=final_prompt)
                        contents = uploaded_files + ["请严格基于上述所有附件执行概念解构指令。"]

                        resp = await asyncio.to_thread(
                            client.models.generate_content, model=model_name, contents=contents, config=cfg
                        )
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

                else:  # Native 的 Text 模式
                    log(f"-> [Attempt {attempt+1}/{max_attempts}] 本地提取内容并发送...", "cyan")
                    combined_context = read_text_from_files(filepaths)
                    if not combined_context.strip():
                        raise Exception("提取文本为空，请检查文件。")
                    full_message = f"请基于以下【概念资料库】分析：\n\n{combined_context}"
                    cfg = types.GenerateContentConfig(temperature=0.3, system_instruction=final_prompt)
                    resp = await asyncio.to_thread(
                        client.models.generate_content, model=model_name, contents=[full_message], config=cfg
                    )
                    return resp.text

            except Exception as e:
                log(f"⚠️ 第 {attempt + 1} 次请求失败 (Key: {current_key[:6]}...): {e}", "yellow")
                if attempt == max_attempts - 1:
                    raise Exception(f"已达到最大重试次数，所有可用 Key 均失败。")
                await asyncio.sleep(3)

    # -----------------------------
    # B) OpenAI Protocol / 中转站（新增 upload A->B->text）
    # -----------------------------
    else:
        ocfg = config.get("OpenAI_Protocol_Config", {})
        max_attempts = max(1, ocfg.get("max_attempts", 3))
        api_pool = ocfg.get("api_pool", [])
        input_method = ocfg.get("input_method", "text")  # 允许 "upload" / "text"

        if not api_pool:
            raise ValueError("OpenAI_Protocol_Config 中未提供 api_pool。")

        proxy = proxy_url if proxy_url else None
        timeout_settings = aiohttp.ClientTimeout(total=CLIENT_TIMEOUT_SEC, sock_read=REQUEST_TIMEOUT_SEC)

        # ---------- JSON 发起 + 响应解析（兼容多种返回结构） ----------
        async def _post_json(session: aiohttp.ClientSession, url: str, headers: dict, payload: dict):
            async with session.post(url, headers=headers, json=payload, proxy=proxy) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}: {text}")
                try:
                    data = json.loads(text)
                except Exception:
                    raise Exception(f"响应不是 JSON: {text[:300]}")

                # 兼容 chat.completions
                if isinstance(data, dict) and "choices" in data and data["choices"]:
                    try:
                        return data["choices"][0]["message"]["content"]
                    except Exception:
                        pass

                # 兼容部分 responses 风格：output_text
                if isinstance(data, dict) and "output_text" in data and isinstance(data["output_text"], str):
                    return data["output_text"]

                # 兼容 responses 的 output 数组
                if isinstance(data, dict) and "output" in data and isinstance(data["output"], list):
                    out = []
                    for item in data.get("output", []):
                        for c in item.get("content", []):
                            if c.get("type") in ("output_text", "text") and c.get("text"):
                                out.append(c["text"])
                    if out:
                        return "\n".join(out)

                raise Exception(f"无法从响应中解析文本内容：{list(data.keys())[:30]}")

        # ---------- text 模式（原逻辑保留） ----------
        async def _text_generate(session: aiohttp.ClientSession, url: str, headers: dict, model: str):
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

        # ---------- 方案 A：先 /v1/files 上传获取 file_id ----------
        async def _upload_files_get_ids(session: aiohttp.ClientSession, base_url: str, headers: dict, files: list[str]) -> list[str]:
            upload_path = ocfg.get("files_api_path", "/v1/files")
            upload_url = f"{base_url.rstrip('/')}{upload_path}"

            file_ids: list[str] = []
            for fp in files:
                filename = os.path.basename(fp)

                form = aiohttp.FormData()
                # 常见字段：purpose + file
                form.add_field("purpose", "assistants")

                fobj = open(fp, "rb")
                try:
                    form.add_field(
                        "file", fobj,
                        filename=filename,
                        content_type="application/octet-stream"
                    )
                    # multipart 时不要强行 Content-Type: application/json
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

        # ---------- 方案 A：引用 file_id 生成（多 payload 探测） ----------
        async def _generate_with_file_ids(session: aiohttp.ClientSession, url: str, headers: dict, model: str, file_ids: list[str]) -> str:
            user_text = "请严格基于已上传的所有附件执行概念解构指令。"
            candidates: list[dict] = []

            # 1) 顶层 file_ids
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

            # 3) content 数组（多模态）
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
            for idx, payload in enumerate(candidates, 1):
                try:
                    return await _post_json(session, url, headers, payload)
                except Exception as e:
                    last_err = e
            raise Exception(f"引用 file_id 生成失败（已尝试 {len(candidates)} 种 payload）：{last_err}")

        # ---------- 方案 B：multipart 同请求直传（两种 form 形态探测） ----------
        async def _multipart_generate_direct(session: aiohttp.ClientSession, url: str, headers: dict, model: str) -> str:
            user_text = "请严格基于本次随请求上传的所有附件执行概念解构指令。"
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
                if "output_text" in data:
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
                        form.add_field(
                            "file", fobj,
                            filename=os.path.basename(fp),
                            content_type="application/octet-stream"
                        )

                    async with session.post(url, headers=headers_no_ct, data=form, proxy=proxy) as resp:
                        return await _parse_resp(resp)
                finally:
                    for f in fobjs:
                        try:
                            f.close()
                        except:
                            pass

            # 形态 2：messages_json + files
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
                        form.add_field(
                            "files", fobj,
                            filename=os.path.basename(fp),
                            content_type="application/octet-stream"
                        )

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
                    if str(input_method).lower() == "upload":
                        # 先试 A：files 上传 -> file_id 引用
                        try:
                            log("-> 尝试方案A：/v1/files 先上传再引用 file_id ...", "cyan")
                            file_ids = await _upload_files_get_ids(session, base_url, headers, filepaths)
                            log(f"-> 上传成功，获得 {len(file_ids)} 个 file_id，开始引用生成...", "cyan")
                            return await _generate_with_file_ids(session, url, headers, model, file_ids)
                        except Exception as eA:
                            log(f"⚠️ 方案A失败：{eA}", "yellow")

                        # 再试 B：multipart 同请求直传
                        try:
                            log("-> 尝试方案B：multipart 同请求直传文件流 ...", "cyan")
                            return await _multipart_generate_direct(session, url, headers, model)
                        except Exception as eB:
                            log(f"⚠️ 方案B失败：{eB}", "yellow")

                        # 最后回退 text
                        log("-> 两种 upload 均失败，回退到 text 模式 ...", "yellow")
                        return await _text_generate(session, url, headers, model)

                    else:
                        # text 模式
                        return await _text_generate(session, url, headers, model)

            except Exception as e:
                log(f"⚠️ 第 {attempt + 1} 次请求失败: {e}", "yellow")
                if attempt == max_attempts - 1:
                    raise Exception(f"已达到最大重试次数，所有节点均失败。")
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
        input_method = config.get("Google_Native_Config", {}).get("input_method", "text")
    else:
        input_method = config.get("OpenAI_Protocol_Config", {}).get("input_method", "text")

    if provider == "native_response" and input_method == "upload":
        source_declaration = "已将原生文献 PDF 阵列作为附件上传至系统。"
        mode_msg = "调用原生多模态引擎进行文献解构"
    elif provider != "native_response" and str(input_method).lower() == "upload":
        source_declaration = "已通过 OpenAI 协议兼容中转接口尝试上传附件（将自动回退至文本合并模式）。"
        mode_msg = "调用中转站上传/多模态兼容路径进行解构"
    else:
        source_declaration = "已在下方上下文中提供所有文献的合并纯文本提取。"
        mode_msg = "基于本地文献库进行解构"

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
            f.write(f"> 融合文献份数：{len(filepaths)} 份 ({str(input_method).upper()} 模式)\n\n")
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
