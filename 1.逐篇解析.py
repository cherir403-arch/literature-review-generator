# -*- coding: utf-8 -*-
import os
import sys
import io

# ==========================================
# 【核心修复】强制全局 UTF-8 编码环境
# 解决控制台打印中文或底层库传输中文时报 'ascii' codec 错误（仅针对 stdout/stderr）
# ==========================================
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    if getattr(sys.stdout, "encoding", "") and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

import json
import shutil
import asyncio
import aiohttp
import pdfplumber
import time
import glob
import re
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

try:
    from google import genai
    from google.genai import types

    HAS_GOOGLE_GENAI = True
except Exception:
    HAS_GOOGLE_GENAI = False

# ==========================================
# 1. 基础路径与配置项
# ==========================================
CONFIG_FILENAME = "1.逐篇解析.json"
DIR_INPUT = "1.1待处理文件_逐篇"
DIR_PROCESSED = "1.2已完成文件_逐篇"
DIR_OUTPUT_MD = "1.3完成后的md_整表"

# 超时常量（单位：秒）
CLIENT_TIMEOUT_SEC = 1800000
REQUEST_TIMEOUT_SEC = 1800000

# ==========================================
# 2. 核心提示词定义 (内置强约束排版与身份锁死机制)
# ==========================================
SYSTEM_PROMPT = """
#单篇论文证据级逆向工程模板
你是“证据级学术审稿人”。你的任务是对单篇论文进行逻辑拆解，输出可直接进入综述材料库的结构化分析结果。

【输入】
当前解析文献编号：[{{FILE_INDEX}}]
当前仅处理 1 篇论文（PDF 或其文本）。不得混入其他论文内容。

【硬约束】
1. 每个判断都要有“原文铁证”（原句或高度贴近原句的证据）。
2. 不做空泛评价，不写“该文很有意义”之类套话。
3. 输出中的“核心价值总结”只能做方向性表述（如“提高/降低/促进/抑制”），不要写具体数字、百分比、系数。
4. 参考文献条目使用 GBT7714-2015。
5. 排版强制要求：请严格使用 Markdown 格式。主结构使用 ### 三级标题；“分析”、“原文铁证”等字眼必须加粗（如 **分析：**）；英文原文证据必须使用引用块 > 嵌套；列举项必须使用无序列表 - 以增强可读性。
6. 身份锁死（核心防混淆）：在本解析任务中，你的身份被锁定为“文献 [{{FILE_INDEX}}] 的专属解析员”。在输出的所有“分析”与“总结”段落中，凡涉及论点或发现描述，必须强制使用：“在文献 [{{FILE_INDEX}}] 中，{作者} ({年份}) 认为/发现...”作为开头。严禁使用“本文”、“作者”等模糊代词。

【输出结构】（严格按序）

### 0) 文献身份锚点
- **文献编号**：[{{FILE_INDEX}}]
- **锁定引用**：{Author} ({Year})
- **核心标签**：{提取3个核心关键词}

### 1) 核心假设（Premise）
**分析：** 在文献 [{{FILE_INDEX}}] 中，{作者} ({年份}) 的研究从什么前提出发？隐藏假设是什么？
**原文铁证：**

### 2) 推演路径（Inference）
**分析：** 在文献 [{{FILE_INDEX}}] 中，推演路径如何从问题推导到结论（A→B→C）？（请用项目列表形式罗列）
**原文铁证：**

### 3) 证据审查（Evidence Check）
**分析：** 在文献 [{{FILE_INDEX}}] 中，证据类型是什么？证据强度和局限在哪里？（请分类别用列表说明）
**原文铁证：**

### 4) 逻辑断点（Logic Gap）
**分析：** 在文献 [{{FILE_INDEX}}] 中，哪一步存在跳跃、外推过度或边界条件不清？
**原文铁证：**

### 5) 五句祛魅（Five-Sentence Demystification）
- **真实动机（The Motivation）：**
- **实际操作（The Method）：**
- **核心发现（The Result）：**
- **隐藏局限（The Fine Print）：**
- **一句话定性（The Verdict）：**

### 6) 基于上述1)到5)核心价值总结
（在写核心总结时，不要出现具体的数据，例如：13.2%等这种具体的数据。这一步的目的是为了总结文章的结论、理论、贡献等，为后面建立文献台账做准备。请确保段落中包含引用标记 [{{FILE_INDEX}}]）
（写 700-750 字中文段落，注意段落之间的空行排版）：

### 7) 参考文献条目（GB/T 7714-2015）
仅输出该论文 1 条标准参考文献。
""".strip()


# ==========================================
# 代码级强制排版清洗函数
# ==========================================
def beautify_markdown(text: str) -> str:
    if not text:
        return text

    # 1. 强制纠正大标题格式 (兼容 0) 到 7) )
    text = re.sub(r'(?m)^(?!\s*#)\s*(\d\)\s+.*?)$', r'### \1', text)

    # 2. 强制加粗关键字段汇
    text = re.sub(r'(?m)^(\s*)(分析[：:])', r'\1**\2** ', text)
    text = re.sub(r'(?m)^(\s*)(原文铁证[：:])', r'\1**\2** ', text)

    # 3. 原文铁证处理：强行插入引用符号 '>'
    text = re.sub(r'(?m)^(\s*)(\*\*原文铁证[：:]\*\*\s*)(.*)$', r'\1\2\n> \3', text)

    # 4. 清理连续的多个空行
    text = re.sub(r'\n{3,}', r'\n\n', text)

    # 5. 五句祛魅的强制无序列表和加粗
    for keyword in ["真实动机", "实际操作", "核心发现", "隐藏局限", "一句话定性"]:
        text = re.sub(fr'(?m)^[-\*\s]*({keyword}.*?[：:])', r'- **\1** ', text)

    return text.strip()


def log(msg, color="white"):
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    colors = {"green": "\033[92m", "cyan": "\033[96m", "yellow": "\033[93m", "red": "\033[91m"}
    print(f"{colors.get(color, '')}[{timestamp}] {msg}\033[0m")


def clean_filename(filename: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip()


def mask_key(s: str) -> str:
    s = str(s or "")
    return "*" + s[-6:] if len(s) > 6 else "*"


class NoAvailableAPI(Exception):
    pass


# ==========================================
# 【核心修复】Gemini 上传时避免中文路径/中文文件名进入 HTTP header
# ==========================================
def make_ascii_temp_copy(src_path: str) -> tuple[str, callable]:
    src = Path(src_path)
    if not src.exists():
        raise FileNotFoundError(src_path)

    drive_root = Path(src.drive + os.sep) if src.drive else Path.cwd()
    tmp_dir = drive_root / "_gemini_tmp"
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


# ==========================================
# 异步安全轮询池 (带熔断禁用机制)
# ==========================================
class RoundRobinPool:
    def __init__(self, items, id_fn):
        self.id_fn = id_fn
        self.total = len(items)
        self.q = asyncio.Queue()
        for it in items:
            self.q.put_nowait(it)
        self.parked = []
        self.in_use = 0
        self.round_id = 0

    def begin_round(self, round_id: int):
        self.round_id = round_id
        if self.parked:
            for it in self.parked:
                self.q.put_nowait(it)
            self.parked = []

    def end_round(self):
        if self.parked:
            for it in self.parked:
                self.q.put_nowait(it)
            self.parked = []

    def _all_banned_now(self, banned_set):
        return (len(banned_set) >= self.total) and (self.in_use == 0) and (self.q.qsize() == 0)

    @asynccontextmanager
    async def borrow(self, banned_set: set, round_id: int):
        if self.total <= 0:
            raise NoAvailableAPI("池为空")
        if self._all_banned_now(banned_set):
            raise NoAvailableAPI("本轮所有 API 已被禁用")

        item = None
        while True:
            if self._all_banned_now(banned_set):
                raise NoAvailableAPI("本轮所有 API 已被禁用")
            try:
                item = await asyncio.wait_for(self.q.get(), timeout=2.0)
            except asyncio.TimeoutError:
                continue

            item_id = self.id_fn(item)
            if item_id in banned_set:
                self.parked.append(item)
                item = None
                continue
            break

        self.in_use += 1
        try:
            yield item
        finally:
            self.in_use -= 1
            item_id = self.id_fn(item)
            if item_id in banned_set:
                self.parked.append(item)
            else:
                self.q.put_nowait(item)


class RoundContext:
    def __init__(self, round_id: int):
        self.round_id = round_id
        self.gemini_banned = set()
        self.openai_banned = set()


# ==========================================
# AI 核心处理器
# ==========================================
class AIProcessor:
    def __init__(self, config):
        self.config = config
        self.settings = config.get("Settings", {})
        self.interface_type = self.settings.get("interface_type", "openai_protocol")
        self.proxy = self.settings.get("proxy_url", None)

        if self.proxy:
            os.environ["http_proxy"] = self.proxy
            os.environ["https_proxy"] = self.proxy

        gcfg = self.config.get("Google_Native_Config", {})
        self.google_model = gcfg.get("model_name", "gemini-2.5-flash")
        self.google_input_method = gcfg.get("input_method", "upload").lower()
        self.google_max_attempts = gcfg.get("max_attempts", 3)
        keys = gcfg.get("api_keys", [])
        self.gemini_pool = RoundRobinPool(keys, id_fn=lambda k: str(k)) if keys else None

        ocfg = self.config.get("OpenAI_Protocol_Config", {})
        self.openai_pool_items = ocfg.get("api_pool", [])
        self.openai_pool = RoundRobinPool(self.openai_pool_items,
                                          id_fn=self._node_id) if self.openai_pool_items else None
        self.openai_input_method = ocfg.get("input_method", "text").lower()
        self.openai_max_attempts = ocfg.get("max_attempts", 3)

    def begin_round(self, round_ctx):
        if self.gemini_pool:
            self.gemini_pool.begin_round(round_ctx.round_id)
        if self.openai_pool:
            self.openai_pool.begin_round(round_ctx.round_id)

    def end_round(self):
        if self.gemini_pool:
            self.gemini_pool.end_round()
        if self.openai_pool:
            self.openai_pool.end_round()

    def _node_id(self, node: dict):
        return node.get("remark", f"{node.get('base_url')}|{node.get('model_name')}")

    async def extract_full_text(self, file_path: str) -> str:
        loop = asyncio.get_event_loop()

        def _read():
            text = ""
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            text += t + "\n"
            except Exception as e:
                log(f"PDF提取失败: {e}", "red")
            return text

        return await loop.run_in_executor(None, _read)

    async def _heartbeat_monitor(self, filename: str, stop_event: asyncio.Event):
        start_time = time.time()
        try:
            while not stop_event.is_set():
                await asyncio.sleep(5)
                if stop_event.is_set():
                    break
                elapsed = int(time.time() - start_time)
                print(f"\r\033[90m[心跳] ⏳ {filename[:15]}... AI正在思考，已等待 {elapsed} 秒...\033[0m", end="")
        except asyncio.CancelledError:
            pass
        finally:
            print("\r" + " " * 80 + "\r", end="")  # 清理心跳行

    async def _process_gemini(self, file_path: str, filename: str, round_ctx: RoundContext, file_index: int):
        abs_file_path = os.path.abspath(file_path)
        # 🟢 动态注入身份锚点
        dynamic_prompt = SYSTEM_PROMPT.replace("{{FILE_INDEX}}", str(file_index))

        for attempt in range(1, self.google_max_attempts + 1):
            async with self.gemini_pool.borrow(round_ctx.gemini_banned, round_ctx.round_id) as api_key:
                client = genai.Client(api_key=api_key)

                stop_heartbeat = asyncio.Event()
                heartbeat_task = asyncio.create_task(self._heartbeat_monitor(filename, stop_heartbeat))

                uploaded = None
                try:
                    cfg = types.GenerateContentConfig(temperature=0.2, system_instruction=dynamic_prompt)

                    if self.google_input_method == "upload":
                        log(f"   -> [Gemini] 正在上传: {filename}", "cyan")
                        tmp_upload_path, cleanup_tmp = make_ascii_temp_copy(abs_file_path)
                        try:
                            uploaded = await asyncio.to_thread(client.files.upload, file=tmp_upload_path)
                        finally:
                            cleanup_tmp()

                        while uploaded.state.name == "PROCESSING":
                            await asyncio.sleep(2)
                            uploaded = await asyncio.to_thread(client.files.get, name=uploaded.name)
                        if uploaded.state.name == "FAILED":
                            raise Exception("云端解析失败")
                        contents = ["请按照系统提示词的要求进行逆向工程拆解。", uploaded]
                    else:
                        text = await self.extract_full_text(abs_file_path)
                        contents = [f"纯文本内容如下：\n\n{text}"]

                    log(f"   -> [Gemini] 正在生成报告 ({self.google_model}) - 分配身份ID: [{file_index}]", "cyan")
                    resp = await asyncio.to_thread(
                        client.models.generate_content,
                        model=self.google_model,
                        contents=contents,
                        config=cfg,
                    )

                    if resp.text:
                        return resp.text

                except Exception as e:
                    msg = str(e).lower()
                    if "429" in msg or "exhausted" in msg:
                        round_ctx.gemini_banned.add(str(api_key))
                        log(f"🚫 触发限流，本轮禁用 Gemini Key {mask_key(api_key)}", "yellow")
                        await asyncio.sleep(5)
                    else:
                        log(f"⚠️ Gemini 异常 (尝试 {attempt}): {e}", "yellow")
                        await asyncio.sleep(2)

                finally:
                    stop_heartbeat.set()
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except Exception:
                        pass

                    if uploaded:
                        try:
                            await asyncio.to_thread(client.files.delete, name=uploaded.name)
                        except Exception:
                            pass

        return None

    async def _process_openai(self, file_path: str, filename: str, round_ctx: RoundContext, file_index: int):
        abs_file_path = os.path.abspath(file_path)
        text = await self.extract_full_text(abs_file_path)
        if not text:
            raise RuntimeError("提取不到文本")

        # 🟢 动态注入身份锚点
        dynamic_prompt = SYSTEM_PROMPT.replace("{{FILE_INDEX}}", str(file_index))

        timeout = aiohttp.ClientTimeout(
            total=CLIENT_TIMEOUT_SEC,
            connect=REQUEST_TIMEOUT_SEC,
            sock_connect=REQUEST_TIMEOUT_SEC,
            sock_read=REQUEST_TIMEOUT_SEC,
        )

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in range(1, self.openai_max_attempts + 1):
                async with self.openai_pool.borrow(round_ctx.openai_banned, round_ctx.round_id) as node:
                    remark = node.get("remark", "Unknown")
                    url = f"{node['base_url'].rstrip('/')}{node['api_path']}"
                    headers = {"Authorization": f"Bearer {node['api_key']}", "Content-Type": "application/json"}

                    payload = {
                        "model": node["model_name"],
                        "messages": [
                            {"role": "system", "content": dynamic_prompt},
                            {"role": "user", "content": f"文本如下，请拆解：\n\n{text}"},
                        ],
                        "temperature": 0.2,
                    }

                    stop_heartbeat = asyncio.Event()
                    heartbeat_task = asyncio.create_task(self._heartbeat_monitor(filename, stop_heartbeat))

                    try:
                        log(f"   -> [OpenAI] 调用节点 {remark} ({node['model_name']}) - 分配身份ID: [{file_index}]",
                            "cyan")
                        async with session.post(url, headers=headers, json=payload, proxy=self.proxy) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                return data["choices"][0]["message"]["content"]
                            elif resp.status in [429, 503]:
                                round_ctx.openai_banned.add(self._node_id(node))
                                log(f"🚫 触发限流，本轮禁用节点 {remark}", "yellow")
                            else:
                                txt = await resp.text()
                                log(f"⚠️ OpenAI 报错 {resp.status}: {txt[:200]}", "yellow")

                    except Exception as e:
                        msg = str(e).lower()
                        if "rate" in msg or "429" in msg:
                            round_ctx.openai_banned.add(self._node_id(node))
                        log(f"⚠️ OpenAI 网络异常 | {remark}: {e}", "yellow")

                    finally:
                        stop_heartbeat.set()
                        heartbeat_task.cancel()
                        try:
                            await heartbeat_task
                        except Exception:
                            pass

                    await asyncio.sleep(2 + attempt)

        return None

    async def process_paper(self, file_path: str, round_ctx: RoundContext, file_index: int):
        filename = os.path.basename(file_path)

        if self.interface_type == "native_response":
            if not HAS_GOOGLE_GENAI:
                raise RuntimeError("未安装 google-genai 库")
            if not self.gemini_pool:
                raise RuntimeError("Google_Native_Config.api_keys 为空，无法调用 Gemini")
            return await self._process_gemini(file_path, filename, round_ctx, file_index)

        elif self.interface_type == "openai_protocol":
            if not self.openai_pool:
                raise RuntimeError("OpenAI_Protocol_Config.api_pool 为空，无法调用 OpenAI Protocol")
            return await self._process_openai(file_path, filename, round_ctx, file_index)

        else:
            raise ValueError("未知的 interface_type")


# ==========================================
# Worker 事务工作流
# ==========================================
async def worker(sem, round_ctx, index, file_path, processor: AIProcessor):
    async with sem:
        filename = os.path.basename(file_path)
        base_name = os.path.splitext(filename)[0]
        log(f"🚀 [R{round_ctx.round_id}-No.{index}] 开始处理: {filename}", "cyan")

        outer_max = 3
        for outer_attempt in range(1, outer_max + 1):
            tmp_md = None
            moved = False
            try:
                # 1. 调用 AI 获取 Markdown 文本 (传递 index 作为身份锚点)
                md_content = await processor.process_paper(file_path, round_ctx, file_index=index)
                if not md_content:
                    raise RuntimeError("AI 返回为空或彻底失败")

                # 2. 代码级清洗并美化排版
                md_content = beautify_markdown(md_content)

                # 3. 写入临时文件 (.tmp.md)
                safe_title = clean_filename(base_name)
                final_md_path = os.path.join(DIR_OUTPUT_MD, f"{safe_title}.md")
                tmp_md = os.path.join(DIR_OUTPUT_MD, f"{safe_title}.tmp.md")

                loop = asyncio.get_event_loop()

                def write_md():
                    with open(tmp_md, "w", encoding="utf-8") as f:
                        f.write(f"# {base_name} 逆向工程分析\n\n")
                        f.write(md_content)

                await loop.run_in_executor(None, write_md)

                # 4. 移动 PDF 到已完成文件夹
                target_pdf = os.path.join(DIR_PROCESSED, filename)
                if os.path.exists(target_pdf):
                    os.remove(target_pdf)
                await loop.run_in_executor(None, shutil.move, file_path, target_pdf)
                moved = True

                # 5. 重命名临时文件为正式文件 (事务提交)
                await loop.run_in_executor(None, os.replace, tmp_md, final_md_path)

                log(f"✅ 完成入库 (ID:[{index}]): {filename}", "green")
                return

            except NoAvailableAPI:
                if tmp_md and os.path.exists(tmp_md):
                    os.remove(tmp_md)
                if moved:
                    try:
                        shutil.move(os.path.join(DIR_PROCESSED, filename), file_path)
                    except Exception:
                        pass

                if outer_attempt < outer_max:
                    log(f"⚠️ 无可用API，外层重试 {outer_attempt}/{outer_max}: {filename}", "yellow")
                    await asyncio.sleep(5)
                    continue
                log(f"❌ 彻底失败 (无可用API): {filename}", "red")
                return

            except Exception as e:
                if tmp_md and os.path.exists(tmp_md):
                    os.remove(tmp_md)
                if moved:
                    try:
                        shutil.move(os.path.join(DIR_PROCESSED, filename), file_path)
                    except Exception:
                        pass

                if outer_attempt < outer_max:
                    log(f"⚠️ 事务异常将重试 {outer_attempt}/{outer_max}: {filename} | {e}", "yellow")
                    await asyncio.sleep(3)
                    continue
                log(f"❌ 解析失败: {filename} | {e}", "red")
                return


# ==========================================
# 主循环调度
# ==========================================
async def main():
    print("===========================================")
    print(" 单篇文献逆向工程解析 (内置代码排版与身份锁死) ")
    print("===========================================")

    for d in [DIR_INPUT, DIR_PROCESSED, DIR_OUTPUT_MD]:
        os.makedirs(d, exist_ok=True)

    try:
        with open(CONFIG_FILENAME, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        log(f"❌ 找不到 {CONFIG_FILENAME}", "red")
        return

    processor = AIProcessor(config)
    concurrency = int(config.get("Settings", {}).get("Document_Analysis_concurrency", 1))

    round_id = 1
    while True:
        files = glob.glob(os.path.join(DIR_INPUT, "*.pdf"))
        if not files:
            break

        log(f"🔁 开始第 {round_id} 轮：待处理 {len(files)} 个文件", "cyan")
        round_ctx = RoundContext(round_id)
        processor.begin_round(round_ctx)

        sem = asyncio.Semaphore(concurrency)
        tasks = [worker(sem, round_ctx, i, f, processor) for i, f in enumerate(files, 1)]
        await asyncio.gather(*tasks)

        processor.end_round()
        pending_after = glob.glob(os.path.join(DIR_INPUT, "*.pdf"))
        log(f"✅ 第 {round_id} 轮结束；剩余待处理 {len(pending_after)} 个", "cyan")

        if len(pending_after) == len(files):
            log("🛑 连续一轮没有任何文件成功，为防止死循环，主动结束。", "red")
            break

        round_id += 1

    log("\n🎉 所有任务处理完毕！", "green")


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())