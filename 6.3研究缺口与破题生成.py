# -*- coding: utf-8 -*-
import os
import sys
import io
import json
import asyncio
import aiohttp
import time
import re
from contextlib import asynccontextmanager

# ==========================================
# 强制全局 UTF-8 编码环境
# ==========================================
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    if getattr(sys.stdout, "encoding", "") and sys.stdout.encoding.lower() != "utf-8":
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

# ==========================================
# 1. 基础配置与超时设置
# ==========================================
CONFIG_FILENAME = "6.研究缺口.json"
PACK_FILE_PATH = os.path.join("2.1合成pack文件", "pack.md")
DIR_OUTPUT_GAP = "5.研究缺口与破题"

CLIENT_TIMEOUT_SEC = 1800000
REQUEST_TIMEOUT_SEC = 1800000

# ==========================================
# 2. 论证型研究缺口挖掘提示词 (模块化整合版)
# ==========================================
PROMPT_TEMPLATE = """
# Role: 顶级期刊审稿人与论文破题专家

任务：基于提供的【底层文献证据 (Pack)】和【多份深度分析报告集】等资料，结合作者提供的【核心洞察】，按照三大理论发现原理，一次性推导出三个差异化的、深刻且创新的研究缺口 (Research Gap)，以证明【目标选题】的在目前的研究中非常具备创新性，具有写作的理论意义。

## 一、 基础知识（必须阅读和理解并应用在后续 Action 中）

（一） 研究缺口（Research Gap）分类指南

研究 Gap 指现有文献中尚未解决、尚未探索、存在争议或理解不透彻的领域。Gap 是进行研究的理由和合法性来源。

 1. 证据空白/矛盾空白 (Evidence/Contradiction Gap)-推荐

 定义：针对同一个问题，现有的实证研究得出了截然不同、甚至完全相反的结论。
 例子：
 Gap 陈述：“关于远程办公对员工创造力的影响，学界存在争议。派别 A 认为远程办公提供了安静环境，提升了创造力；派别 B 则认为缺乏面对面交流削弱了思想碰撞。目前的文献未能解释这种差异产生的条件。”
 切入点：我认为这取决于“任务的性质”（独立型任务 vs. 协作型任务）。

 2. 知识空白 (Knowledge Gap)-推荐

 定义：针对某种新现象、新趋势，学术界还没有足够的研究数据或理论解释。
 例子：
 Gap 陈述：“现有的消费者行为理论大多基于 Web 2.0 的电商模式。然而，随着生成式 AI（如 ChatGPT）介入购物决策，消费者的信任机制和决策路径发生了根本性变化，目前的文献对此尚缺乏系统的实证探索。”

 3. 方法论空白 (Methodology Gap)-一般不采用，不到万不得已不使用这个

 定义：前人的研究虽然有结论，但使用的方法存在缺陷、局限，或者过于单一，导致结论可能不准确或不全面。
 例子：
 Gap 陈述：“虽然已有研究证实了社交媒体会导致焦虑，但现有研究多采用横截面设计（Cross-sectional design），无法排除反向因果关系（即：是因为焦虑才刷手机，还是刷手机导致焦虑？）。本研究将采用纵向追踪设计来厘清这一因果链条。”

 4. 理论应用空白 (Theoretical Application Gap)-推荐

 定义：现有的理论框架解释力不足，或者我们可以把 A 领域的成熟理论，借用到 B 领域来解释新问题。
 例子：
 Gap 陈述：“以往对员工离职倾向的研究主要基于‘社会交换理论’（利益交换）。然而，对于以‘自我实现’为核心的新生代员工，这一理论解释力下降。本研究尝试引入‘工作重塑理论’（Job Crafting Theory），从心理需求满足的新视角来解释这一现象。”

 5. 情境/对象空白 (Context/Population Gap)-一般

 定义：某个理论在 A 环境（如西方国家、大企业）被验证了，但在 B 环境（如中国、中小企业）是否适用？
 例子：
 弱 Gap：“没人研究过中国四川地区的案例。”（Reviewer 会问：四川有什么特别的吗？如果没有，这个研究没意义。）
 强 Gap：“现有的企业社会责任（CSR）模型主要建立在西方制度背景下。然而，在中国‘关系本位’和政府主导的特殊商业环境中，企业履行 CSR 的动机可能截然不同。因此，有必要检验西方模型在中国情境下的适用性。”

 6. 实践-应用空白 (Practice-Application Gap)-一般

 定义：学术研究的建议与实际从业者的行为之间存在脱节。
 例子：
 Gap 陈述：“尽管大量文献建议医生在告知坏消息时应遵循‘SPIKES 模型’，但临床观察发现，急诊科医生极少使用该模型。现有的研究忽略了‘高时间压力’这一现实约束对理论应用的影响，本研究旨在探索适合急诊环境的改良沟通模型。”

（二）研究缺口发现的三大原理
在进行推导前，请务必理解并应用以下原理：
1. 透镜原理 (Lens Principle)：聚焦文献结论的矛盾与不一致性，寻找被忽视的调节变量或边界条件。
2. 时滞原理 (Time-Lag Principle)：识别经典理论在面对新政策、新情境或新机制下的解释力失效。
3. 光影原理 (Light-Shadow Principle)：批判主流范式所系统性遮蔽的视角。

（三）有无Gap写作示例：
- 没有 Gap描述： 我想研究“运动对减肥的影响”。（这已经被研究烂了，没有意义）。
- 有 Gap 描述： 现有研究大量证实了有氧运动对减肥的效果（综），但大多集中在长期坚持运动的人群（评）。然而，对于那些“三天打鱼两天晒网”的间歇性运动者，其代谢机制有何不同，目前尚缺乏足够的实证证据（这是Gap）。 因此，本研究旨在……

## 二、 输入设定
- 目标选题：{topic}
- 作者洞察：{user_suggestion}
  (注：这是破题的核心支点，请将其植入三个方案的论证逻辑中，实现理论与机制的贯通。)
- 目标字数：每个方案约 {target_words} 字。

## 三、 上下文材料 (Context)
1. **底层文献证据库 (Pack)**：提供颗粒度实证证据（向下扎根）。
2. **深度分析报告集**：包含了作者前期对相关概念、政策或现有综述的高维解构（向上生长）。请以此作为理论推演的基石，将这些概念或政策的属性融合到缺口的推导中。

## 四、 执行逻辑：并行产出三套方案
请取消暂停，直接输出以下三个方案，每个方案均须严格遵守“三明治模型”撰写：

### 方案 A：基于【透镜原理】的逻辑推演
- 逻辑：通过 Pack 寻找证据冲突，利用【深度分析报告】中的变量属性与【作者洞察】作为“透镜”来解释。
- 撰写：[肯定现状(引述报告集定调)] -> [指出缺口(引用Pack靶子)] -> [占据缺口(引出选题)]
- 类型：标出这个 Gap 属于研究缺口分类中的哪一类，并简要说明原因

### 方案 B：基于【时滞原理】的逻辑推演
- 逻辑：论证现有理论在处理【目标选题】涉及的现实变化（基于政策或概念报告）时存在滞后，急需情境化补充。
- 撰写：[肯定现状(引述报告集定调)] -> [指出缺口(引用Pack靶子)] -> [占据缺口(引出选题)]
- 类型：标出这个 Gap 属于研究缺口分类中的哪一类，并简要说明原因

### 方案 C：基于【光影原理】的逻辑推演
- 逻辑：利用【作者洞察】批判现有研究范式的盲区，证明你补充的变量或视角是光影背后的关键真相。
- 撰写：[肯定现状(引述报告集定调)] -> [指出缺口(引用Pack靶子)] -> [占据缺口(引出选题)]
- 类型：标出这个 Gap 属于研究缺口分类中的哪一类，并简要说明原因

## 五、 约束
1. 引用格式：(Author, year) [n]。
2. 参考文献：在文末统一按照 GBT7714-2015 格式列出，每行仅限一条文献，严禁合并。
""".strip()

# ==========================================
# 3. 辅助函数：扫描、排版与日志
# ==========================================
def scan_analysis_files():
    """扫描目录下的模块化分析报告，支持 3~9 开头的文件夹"""
    analysis_files = []
    valid_dirs = [d for d in os.listdir('.') if os.path.isdir(d) and re.match(r'^[3-9]\.', d)]
    for d in valid_dirs:
        for f in os.listdir(d):
            if f.endswith('.md'):
                analysis_files.append({"folder": d, "filename": f, "path": os.path.join(d, f)})
    return analysis_files

def beautify_gap_md(text):
    if not text:
        return text
    text = re.sub(r'(?m)^(?!\s*#)\s*(Phase \d:.*?)$', r'### \1', text)
    if "参考文献" in text:
        parts = re.split(r'(###.*?参考文献.*?\n)', text, flags=re.IGNORECASE)
        if len(parts) > 2:
            ref_content = parts[-1]
            ref_content = re.sub(r'\s*\[(\d+)\]\s*', r'\n[\1] ', ref_content)
            text = "".join(parts[:-1]) + ref_content.strip() + "\n"
    return text.strip()

def log(msg, color="white"):
    colors = {"green": "\033[92m", "cyan": "\033[96m", "yellow": "\033[93m", "red": "\033[91m"}
    print(f"{colors.get(color, '')}[{time.strftime('%H:%M:%S')}] {msg}\033[0m")

async def show_heartbeat(start_time, stop_event):
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    i = 0
    while not stop_event.is_set():
        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)
        frame = spinner[i % len(spinner)]
        sys.stdout.write(
            f"\r\033[93m[{time.strftime('%H:%M:%S')}] {frame} 🧠 AI 正在融合多模块报告推演 GAP 方案... 已耗时: {mins:02d}分{secs:02d}秒\033[0m"
        )
        sys.stdout.flush()
        i += 1
        await asyncio.sleep(0.1)
    sys.stdout.write("\r" + " " * 110 + "\r")
    sys.stdout.flush()

# ==========================================
# 4. 轮询池 + 熔断上下文（稳健性核心）
# ==========================================
class NoAvailableAPI(Exception):
    pass

class RoundRobinPool:
    """
    轮询池：支持“本轮禁用(banned_set)”与 parked 缓冲。
    borrow() 会自动跳过被禁用项，并在 finally 时回收。
    """
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

def mask_key(s: str) -> str:
    s = str(s or "")
    return "***" + s[-6:] if len(s) > 6 else "***"

# ==========================================
# 5. 稳健 AI 调用器（替换原 call_ai）
# ==========================================
class AIClientRobust:
    def __init__(self, config: dict):
        self.config = config
        self.settings = config.get("Settings", {}) or {}
        self.interface_type = self.settings.get("interface_type", "openai_protocol")
        self.proxy = self.settings.get("proxy_url", None)

        if self.proxy:
            os.environ["http_proxy"] = self.proxy
            os.environ["https_proxy"] = self.proxy

        # Gemini 配置
        gcfg = config.get("Google_Native_Config", {}) or {}
        self.google_model = gcfg.get("model_name", "gemini-2.5-flash")
        self.google_max_attempts = max(1, int(gcfg.get("max_attempts", 3)))
        self.google_keys = gcfg.get("api_keys", []) or []
        self.gemini_pool = RoundRobinPool(self.google_keys, id_fn=lambda k: str(k)) if self.google_keys else None

        # OpenAI Protocol 配置
        ocfg = config.get("OpenAI_Protocol_Config", {}) or {}
        self.openai_max_attempts = max(1, int(ocfg.get("max_attempts", 3)))
        self.openai_nodes = ocfg.get("api_pool", []) or []
        self.openai_pool = RoundRobinPool(self.openai_nodes, id_fn=self._node_id) if self.openai_nodes else None

        # 超时（保持你原来的“超大超时”设定）
        self.timeout_settings = aiohttp.ClientTimeout(total=CLIENT_TIMEOUT_SEC, sock_read=REQUEST_TIMEOUT_SEC)

    def begin_round(self, round_ctx: RoundContext):
        if self.gemini_pool:
            self.gemini_pool.begin_round(round_ctx.round_id)
        if self.openai_pool:
            self.openai_pool.begin_round(round_ctx.round_id)

    def end_round(self):
        if self.gemini_pool:
            self.gemini_pool.end_round()
        if self.openai_pool:
            self.openai_pool.end_round()

    def _node_id(self, node: dict) -> str:
        return node.get("remark", f"{node.get('base_url')}|{node.get('model_name')}")

    async def call(self, combined_content: str, prompt: str, round_ctx: RoundContext) -> str:
        provider = self.interface_type

        if provider == "native_response":
            if not HAS_GOOGLE_GENAI:
                raise RuntimeError("未安装 google-genai，无法使用 native_response")
            if not self.gemini_pool:
                raise RuntimeError("Google_Native_Config.api_keys 为空，无法调用 Gemini")
            return await self._call_gemini(combined_content, prompt, round_ctx)

        if provider == "openai_protocol":
            if not self.openai_pool:
                raise RuntimeError("OpenAI_Protocol_Config.api_pool 为空，无法调用 OpenAI Protocol")
            return await self._call_openai_protocol(combined_content, prompt, round_ctx)

        raise ValueError("未知的 interface_type")

    async def _call_gemini(self, combined_content: str, prompt: str, round_ctx: RoundContext) -> str:
        """
        Gemini：轮询 key + 熔断 + 重试
        - 对 429/RESOURCE_EXHAUSTED：本轮禁用该 key
        - 其它异常：继续换 key / 重试
        """
        last_err = None

        for attempt in range(1, self.google_max_attempts + 1):
            async with self.gemini_pool.borrow(round_ctx.gemini_banned, round_ctx.round_id) as api_key:
                key_short = mask_key(api_key)
                try:
                    client = genai.Client(api_key=api_key, http_options={'timeout': REQUEST_TIMEOUT_SEC})
                    cfg = types.GenerateContentConfig(temperature=0.3, system_instruction=prompt)

                    log(f"-> [Gemini] Attempt {attempt}/{self.google_max_attempts} | Key {key_short} | model={self.google_model}", "cyan")
                    resp = await asyncio.to_thread(
                        client.models.generate_content,
                        model=self.google_model,
                        contents=[combined_content],
                        config=cfg
                    )
                    text = getattr(resp, "text", None)
                    if text:
                        return text
                    raise RuntimeError("Gemini 返回为空")

                except Exception as e:
                    last_err = e
                    msg = str(e).lower()

                    # 常见限流/配额耗尽
                    if ("429" in msg) or ("resource_exhausted" in msg) or ("exhausted" in msg) or ("quota" in msg):
                        round_ctx.gemini_banned.add(str(api_key))
                        log(f"🚫 [Gemini] 触发限流/配额，本轮禁用 Key {key_short} | {e}", "yellow")
                        await asyncio.sleep(min(8, 2 + attempt))
                        continue

                    # 其他错误：记录并短退避后继续（会换 key）
                    log(f"⚠️ [Gemini] 异常（将重试/换Key）: {e}", "yellow")
                    await asyncio.sleep(min(6, 1 + attempt))
                    continue

        raise RuntimeError(f"Gemini 已达到最大重试次数，仍失败：{last_err}")

    async def _call_openai_protocol(self, combined_content: str, prompt: str, round_ctx: RoundContext) -> str:
        """
        OpenAI Protocol：轮询 node + 熔断 + 重试
        - 对 429/503/504：本轮禁用该节点（更激进，避免卡死）
        - 对 非 200：读取 text 作为错误信息；必要时禁用
        - 对网络异常：禁用并换节点
        """
        last_err = None

        async with aiohttp.ClientSession(timeout=self.timeout_settings) as session:
            for attempt in range(1, self.openai_max_attempts + 1):
                async with self.openai_pool.borrow(round_ctx.openai_banned, round_ctx.round_id) as node:
                    node_id = self._node_id(node)
                    remark = node.get("remark", "Unknown")
                    url = f"{node['base_url'].rstrip('/')}{node['api_path']}"
                    headers = {"Authorization": f"Bearer {node['api_key']}", "Content-Type": "application/json"}

                    payload = {
                        "model": node["model_name"],
                        "messages": [
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": combined_content}
                        ],
                        "temperature": 0.3
                    }

                    try:
                        log(f"-> [OpenAI] Attempt {attempt}/{self.openai_max_attempts} | Node {remark} | model={node.get('model_name')}", "cyan")
                        async with session.post(url, headers=headers, json=payload, proxy=self.proxy) as resp:
                            if resp.status == 200:
                                # 兼容：可能不是 JSON（极少），先 try json，失败再 text
                                try:
                                    data = await resp.json()
                                except Exception:
                                    txt = await resp.text()
                                    raise RuntimeError(f"OpenAI 响应非JSON：{txt[:300]}")

                                # chat.completions 结构
                                try:
                                    return data["choices"][0]["message"]["content"]
                                except Exception:
                                    # 尝试其它结构（尽量不破坏原功能）
                                    if isinstance(data, dict) and isinstance(data.get("output_text"), str) and data["output_text"]:
                                        return data["output_text"]
                                    raise RuntimeError(f"OpenAI 返回结构无法解析：{list(data.keys())[:40]}")

                            # 非 200：尽可能拿到错误文本
                            err_text = ""
                            try:
                                err_text = await resp.text()
                            except Exception:
                                err_text = "<no body>"

                            # 429/503/504：通常认为节点暂不可用 -> 本轮禁用
                            if resp.status in (429, 503, 504):
                                round_ctx.openai_banned.add(node_id)
                                log(f"🚫 [OpenAI] HTTP {resp.status} 本轮禁用节点 {remark} | {err_text[:200]}", "yellow")
                                await asyncio.sleep(min(10, 2 + attempt))
                                continue

                            # 其他 4xx/5xx：不一定要禁用，但为了稳健可按需禁用
                            if resp.status >= 500:
                                round_ctx.openai_banned.add(node_id)
                                log(f"🚫 [OpenAI] HTTP {resp.status}（服务器错误）禁用节点 {remark} | {err_text[:200]}", "yellow")
                                await asyncio.sleep(min(10, 2 + attempt))
                                continue

                            # 其他错误（如 400/401/403）：可能是参数或 key 问题，禁用避免死循环
                            if resp.status in (400, 401, 403):
                                round_ctx.openai_banned.add(node_id)
                                log(f"🚫 [OpenAI] HTTP {resp.status}（可能是Key/参数）禁用节点 {remark} | {err_text[:200]}", "yellow")
                                await asyncio.sleep(min(8, 2 + attempt))
                                continue

                            # 默认：保守重试
                            last_err = RuntimeError(f"OpenAI HTTP {resp.status}: {err_text[:300]}")
                            log(f"⚠️ [OpenAI] HTTP {resp.status}：{err_text[:200]}", "yellow")
                            await asyncio.sleep(min(6, 1 + attempt))
                            continue

                    except aiohttp.ClientError as e:
                        last_err = e
                        round_ctx.openai_banned.add(node_id)
                        log(f"🚫 [OpenAI] 网络异常，禁用节点 {remark} | {e}", "yellow")
                        await asyncio.sleep(min(8, 2 + attempt))
                        continue
                    except asyncio.TimeoutError as e:
                        last_err = e
                        round_ctx.openai_banned.add(node_id)
                        log(f"🚫 [OpenAI] 超时，禁用节点 {remark}", "yellow")
                        await asyncio.sleep(min(10, 2 + attempt))
                        continue
                    except Exception as e:
                        last_err = e
                        # 若报错特征像限流/拥塞，也禁用
                        msg = str(e).lower()
                        if "429" in msg or "rate" in msg or "overloaded" in msg:
                            round_ctx.openai_banned.add(node_id)
                        log(f"⚠️ [OpenAI] 异常（将重试/换节点）：{e}", "yellow")
                        await asyncio.sleep(min(6, 1 + attempt))
                        continue

        raise RuntimeError(f"OpenAI Protocol 已达到最大重试次数，仍失败：{last_err}")

# ==========================================
# 6. 主程序
# ==========================================
async def main():
    print("===========================================")
    print("   🎯 模块化增强型：研究缺口挖掘系统 (ABC方案)  ")
    print("===========================================")
    os.makedirs(DIR_OUTPUT_GAP, exist_ok=True)

    try:
        with open(CONFIG_FILENAME, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        log(f"❌ 无法读取配置 {CONFIG_FILENAME}: {e}", "red")
        return

    if not os.path.exists(PACK_FILE_PATH):
        log("❌ 找不到底层 Pack 文件", "red")
        return

    with open(PACK_FILE_PATH, 'r', encoding='utf-8') as f:
        pack_content = f.read()

    analysis_files = scan_analysis_files()
    if not analysis_files:
        log("❌ 未找到任何模块化分析报告 (.md)", "red")
        return

    print("\n📂 发现以下已完成的分析报告（模块库）：")
    for idx, rf in enumerate(analysis_files, 1):
        print(f"   [{idx}] {rf['folder']} / {rf['filename']}")

    # 支持多选的交互逻辑（保持原功能）
    while True:
        choice_str = input("\n👉 请选择要作为基底的报告/综述 (输入序号，多选请用逗号分隔，如 1,3,4): ").strip()
        if not choice_str:
            print("⚠️ 必须至少选择一份报告。")
            continue
        try:
            choice_str = choice_str.replace('，', ',')
            indices = [int(x.strip()) for x in choice_str.split(',') if x.strip()]

            selected_files = []
            ok = True
            for idx in indices:
                if 1 <= idx <= len(analysis_files):
                    selected_files.append(analysis_files[idx - 1])
                else:
                    ok = False
                    break

            if ok and selected_files:
                break
            print("⚠️ 包含无效的序号，请检查后重新输入。")
        except ValueError:
            print("⚠️ 格式错误，请输入数字序号，多选请用逗号分隔。")

    # 拼接多个模块报告的内容（保持原功能）
    reports_content = ""
    report_names = []
    for sf in selected_files:
        with open(sf['path'], 'r', encoding='utf-8') as f:
            reports_content += f"\n\n============= 【基底模块：{sf['filename']}】 =============\n{f.read()}\n"
            report_names.append(sf['filename'])

    print("\n-------------------------------------------")
    topic = input("✍️  请输入【目标选题】: ").strip()
    user_suggestion = input("✍️  请输入【你的核心洞察/建议】: ").strip()
    target_words = input("✍️  请输入【每个方案的目标字数】: ").strip()

    final_prompt = PROMPT_TEMPLATE.format(topic=topic, user_suggestion=user_suggestion, target_words=target_words)
    combined_content = f"---底层证据 (PACK)---\n{pack_content}\n---深度分析报告集 (REPORTS)---\n{reports_content}"

    log(f"\n🚀 已挂载 {len(selected_files)} 份深度模块，正在推演 GAP 方案...", "cyan")

    stop_event = asyncio.Event()
    start_time = time.time()
    heartbeat_task = asyncio.create_task(show_heartbeat(start_time, stop_event))

    # 轮询池上下文（保持“单任务一次推演”，这里 round_id 固定为 1）
    round_ctx = RoundContext(round_id=1)
    client = AIClientRobust(config)
    client.begin_round(round_ctx)

    try:
        result = await client.call(combined_content, final_prompt, round_ctx)
        result = beautify_gap_md(result)

        safe_name = topic.replace("/", "_").replace("\\", "_")[:20]
        output_path = os.path.join(DIR_OUTPUT_GAP, f"Step6_{safe_name}_多模块缺口论证.md")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# 模块化研究缺口三方案论证：{topic}\n\n")
            f.write(f"> **已挂载基底模块**：\n")
            for name in report_names:
                f.write(f"> - {name}\n")
            f.write("\n")
            f.write(result)

        stop_event.set()
        await heartbeat_task
        log(f"🎉 破题成功！多模块整合方案已保存至: {output_path}", "green")

    except NoAvailableAPI as e:
        stop_event.set()
        await heartbeat_task
        log(f"❌ 本轮所有 API 不可用：{e}", "red")
    except Exception as e:
        stop_event.set()
        await heartbeat_task
        log(f"❌ 生成失败: {e}", "red")
    finally:
        client.end_round()

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())