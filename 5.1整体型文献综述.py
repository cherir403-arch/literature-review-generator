# -*- coding: utf-8 -*-
import os
import sys
import io
import json
import asyncio
import aiohttp
import time
import re
import uuid
from contextlib import asynccontextmanager

# ==========================================
# 强制全局 UTF-8 编码环境 (防止控制台/底层库乱码)
# ==========================================
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ==========================================
# 引入 Google 新版 SDK
# ==========================================
try:
    from google import genai
    from google.genai import types

    HAS_GOOGLE_GENAI = True
except Exception:
    HAS_GOOGLE_GENAI = False

# ==========================================
# 1. 基础路径配置
# ==========================================
CONFIG_FILENAME = "5.文献回顾.json"
PACK_FILE_PATH = os.path.join("2.1合成pack文件", "pack.md")
DIR_OUTPUT_ARCH = "4.1整体型文献回顾"

# ==========================================
# ✅【改法 2】Gemini 超时设置（只新增这一条功能，不动其它逻辑）
# - CLIENT_TIMEOUT_SEC: 作用于 Client 的 http_options
# - REQUEST_TIMEOUT_SEC: 作用于 generate_content 的 timeout（如版本支持）
# ==========================================
CLIENT_TIMEOUT_SEC = 1800000        # 建议 600~1800
REQUEST_TIMEOUT_SEC = 1800000       # 建议与 Client 一致


# ==========================================
# 2. 动态提示词模板 (已替换为你的升级版 Prompt)
# ==========================================
PROMPT_TEMPLATE = """
# Role: 资深学术导师与编辑
专长：文献综合分析、学术写作架构、客观评价。
任务：协助我基于提供的文献资料，构建并撰写一篇高质量的“批判性文献综述 (Critical Literature Review)”。

【输入设定】
切入领域：{subfield_name}
我正在撰写关于 {subfield_name} 的文献综述。我的目标不是简单的罗列文献，而是要体现“批判性”，即客观评估文献质量、分析观点分歧，以便于在下一步中推导出我的研究缺口 (Research Gap)。
目标字数：{target_words}字左右。目标字数仅指【Phase 4：客观综述叙述稿】部分的纯文本内容，不涵盖表格（如文献矩阵）、标题、参考文献列表以及标点符号。

【硬约束】
1. 只使用 Pack 内容，不做主观臆断。不得引入外部常识。
2. 正文引用短码：在【Phase 4：客观综述叙述稿】中只使用 [n] 作为引用标记，不写 (Author, year)；作者-年份完整信息仅在【Phase 5: 参考文献】中给出。
3. 取消暂停：请一次性完成全部分析流程，并直接给出最终结果。
4. 客观立场：本阶段不推导 Research Gap，仅进行客观的文献回顾、证据对比与主题映射。
5. 排版要求：严格使用 Markdown 格式，主阶段标题使用 ###。
6. Pack 内容中列举了多少篇论文，这一份文献回顾中就要对所有论文都进行引用。
7. 1篇论文只能在【Phase 4：客观综述叙述稿】中进行一次引用。
8. 【Phase 4：客观综述叙述稿】中的单独一句话可以引用1篇文献，也可以引用2篇文献。但最多不能超过2篇。
9. 叙事逻辑脱钩方法论（Conceptual over Methodological）： > 严禁在【Phase 4：客观综述叙述稿】中显性提及实证方法名称（如“利用DID”、“基于PSM-DID”、“采用双重差分法”等）。文献回顾的重心必须锁定在“观点冲突”和“逻辑脉络”上。如果需要强调证据的可靠性，请将其转化为学术语境下的质量描述（如“基于大样本准自然实验”、“通过对异质性效应的稳健性处理”、“从XXX提供的证据表明”等），或者直接隐去方法，仅陈述核心发现。
10. 观点驱动型叙事： 强制采用“批注型引用”风格，即优先陈述完整的学术观点或实证规律，随后以 [n] 形式批注参考文献；除非涉及极具开创性的理论对垒，否则严禁以“某学人(年份)认为/发现”作为句首开篇，并鼓励对相同发现的文献进行“聚合引用”以增强论证密度。
11. 字数约束仅作用于【Phase 4：客观综述叙述稿】正文：不统计标题、参考文献、编号、空白与标点符号。
12. 字数执行标准：最终 Phase 4 正文字数必须贴近目标值 {target_words}，允许误差不超过 ±10%（理想控制在 ±5%）。
13. 输出前必须完成“计字→修订→再计字”自检；若超长则压缩重复表述与例证细节，若不足则补充跨文献比较与分歧分析，直到达标。


【基础知识】（必须阅读和理解并应用在后续写作中）
整体型文献综述并不是说它“不分类”，而是它的分类界限不那么生硬，或者它更侧重于讲一个完整的故事，强调文献之间的流动性和演变。
- 特征： 可能没有很多细碎的小标题，而是通过段落之间的逻辑过渡（起承转合）来串联。它往往把整个研究领域看作一个随着时间或逻辑演变的整体。
- 形式： 文章看起来更像是一篇连贯的散文，从理论的起源讲到争议，再讲到最新的趋势，中间没有明显的物理割裂。
- 适用场景： 实证论文中的“引言”或“文献综述”部分（篇幅较短时），或者侧重于梳理历史脉络的研究。
- 优点： 逻辑连贯性强，能体现出“演进”的感觉。

# Step-by-Step Instructions (执行步骤)（严格按序）

【输出模式（运行时决定）】
请在阅读完全部规则后，严格遵守文末“### Runtime Output Contract（运行时输出协议）”中的输出范围与格式要求。

### Phase 1: 文献综合矩阵 (The Synthesis Matrix)
请分析我提供资料中的文献内容，生成一个 Markdown 表格。生成一个“文献综合矩阵 (Synthesis Matrix)”表格。不要只做总结，重点提取以下维度：
- 仅展示随机抽样的 5 篇文献用于矩阵展示（不是全部文献）；但后续 Phase 2~Phase 5 的分析与叙述仍需覆盖全部文献。
- [编号]
- 理论视角 (Theoretical Lens)
- 方法论 (Methodology: 样本、工具、方法)
- 核心争论/分歧点 (Key Debates)
- 批判性笔记 (Critical Notes: 逻辑漏洞、特定背景的限制、理论缺陷、视角局限)

### Phase 2: 主题映射 (Thematic Mapping)
基于 Phase 1，要按时间顺序排列，请识别出 3-4 个核心主题 (Themes)或争议点(Debates)。要求寻找文献之间的“对话”：
- 谁支持谁？谁反对谁？
- 详细说明分歧的原因（是方法论差异还是定义差异）。
- 输出：主题大纲，并简述每个主题下的阵营分布。

### Phase 3: 批判性撰写 (Drafting with MEAL)
对【Phase 2: 主题映射】下生成的每一个主题，按照MEAL结构 为我撰写一个示范性的综述段落：
   M(Main Idea)：本段的主旨句。
   E(Evidence)：引用相关文献作为证据。
   A(Analysis - 核心)：进行批判性分析。比较不同文献的异同，解释矛盾的原因（如：方法论差异、文化背景差异），指出证据的可信度。
   L(Link)：总结本段，并指出该主题目前仍未解决的问题。
采用非罗列式而是主题综合式的写法。

### Constraints (约束条件)
1. 语气：学术、客观、严谨。
2. 逻辑：避免流水账（He said, she said），必须使用“比较”、“对比”、“评估”的句式。
3. 常用词汇：请使用类似 "In contrast", "However", "A limitation of this approach", "Despite these findings" 等连接词（或对应的中文学术用语）。
4. 在观点句和观点句之间可以适当加入少量的连接词或者连接句，保证语段意思清晰，避免体现出“罗列式”的嫌疑

### Phase 4: 客观综述叙述稿 (The Review Narrative)
基于上述分析，生成 {target_words} 字左右的综述初稿：
- 采用非罗列式而是主题综合式的写法。
- 重点陈述该领域已达成的共识，以及目前尚未解决的客观技术分歧。
- 确保所有观点均有文献支撑。
- 字数控制：仅统计本阶段正文，最终字数需满足上方硬约束的误差范围，并尽量接近目标值。
- 生成结束前请自行校准字数，严禁明显超出目标字数（例如超过目标值 15% 以上）。

### Constraints (约束条件)
1. 语气：学术、客观、严谨。
2. 逻辑：避免流水账（He said, she said），必须使用“比较”、“对比”、“评估”的句式。
3. 常用词汇：请使用类似 "In contrast", "However", "A limitation of this approach", "Despite these findings" 等连接词（或对应的中文学术用语）。
4.逻辑合并与“同类项”归并：
- 强制逻辑聚合： 严禁出现“A发现……；B发现……”这种孤立的简单并列句式。如果多篇文献支持同一论点，必须将其整合为单句表述。
- 正向示范： 水资源税对生产效率的驱动作用在宏观层面（张三, 2022 [1]）与微观企业层面（李四, 2023 [2]）均得到了实证互证。
5.引入“对立/补充”的对冲架构
- 强制观点对撞： 每一段内部必须包含至少一组“对比”或“递进”逻辑。AI 必须识别文献在研究视角、机制路径或结论边界上的细微差异。
- “尽管 [文献A] 强调了 X 路径的导向作用，但 [文献B] 则指出这一效应在 Y 条件下可能面临失效，从而构成了对政策边界的补充视角。”

### Phase 5: 参考文献
仅列正文引用到的文献（GBT7714-2015）。
**排版强约束**：
- 请务必以 [1], [2], [3] 的编号形式独立成行输出，每一行只写一条参考文献，绝对不要把多条文献连在一行！
- 按照 GBT7714-2015 顺序列出，独立成行，严禁连写。
"""


# ==========================================
# 3. 代码级强制清洗与排版函数 (已适配 Phase 5)
# ==========================================
def beautify_architecture_md(text):
    if not text:
        return text

    # 强制纠正大标题格式
    text = re.sub(r'(?m)^(?!\s*#)\s*(Phase \d:.*?)$', r'### \1', text)

    # 定位到 Phase 5 参考文献进行切割 (注意：现在参考文献是 Phase 5)
    match = re.search(r'(### Phase 5.*?\n)(.*)', text, flags=re.IGNORECASE | re.DOTALL)

    if match:
        before_refs = text[:match.start(2)]
        refs_content = match.group(2)

        # 强行切割参考文献，加换行符
        cleaned_refs = re.sub(r'\s*\[(\d+)\]\s*', r'\n[\1] ', refs_content)
        cleaned_refs = re.sub(r'\n{2,}', r'\n', cleaned_refs).strip()

        text = before_refs + cleaned_refs + '\n'

    # 标题前加空行透气 (包括 Constraints 标题)
    text = re.sub(r'(?<!\n)\n(### (Phase|Constraints))', r'\n\n\1', text)

    return text.strip()


def build_runtime_output_contract(use_full_prompt: bool) -> str:
    if use_full_prompt:
        return """
### Runtime Output Contract（运行时输出协议）
（本协议优先级高于前文中任何通用输出说明）
1. 本次为【满血提示词】模式：你必须完整输出 Phase 1、Phase 2、Phase 3、Phase 4、Phase 5，且按顺序输出。
2. 不得省略任何阶段标题，不得新增额外阶段或无关说明。
3. 在【Phase 1】中矩阵只展示随机抽样的 5 篇文献，不要输出全量文献矩阵。
4. 在【Phase 3】中不要对每个主题都写段落，只需从主题映射中选择 1 个最具代表性的主题，输出 1 段完整的 MEAL 示范段落。
5. 在【Phase 4】中仅使用 [n] 引用短码，不要写 (Author, year)；作者-年份完整信息放在【Phase 5】。
"""

    return """
### Runtime Output Contract（运行时输出协议）
（本协议优先级高于前文中任何通用输出说明）
1. 本次为【精简输出】模式：你必须在内部完整执行 Phase 1~5 的分析流程，但对外仅输出以下三部分，且按顺序：
   - ### Phase 2: 主题映射 (Thematic Mapping)
   - ### Phase 4: 客观综述叙述稿 (The Review Narrative)
   - ### Phase 5: 参考文献
2. 在【Phase 4】中仅使用 [n] 引用短码，不要写 (Author, year)；作者-年份完整信息放在【Phase 5】。
3. 【Phase 5】仅输出前 3 条参考文献，编号保持 [1]、[2]、[3] 独立成行。
4. 除上述三部分外，不得输出任何额外说明、前言、分隔线或过程性文字。
"""


def log(msg, color="white"):
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    colors = {"green": "\033[92m", "cyan": "\033[96m", "yellow": "\033[93m", "red": "\033[91m"}
    print(f"{colors.get(color, '')}[{timestamp}] {msg}\033[0m")


# ==========================================
# 4. API 调用器
# ==========================================
async def call_gemini(pack_content, prompt, config, key_index=None):
    gcfg = config.get("Google_Native_Config", {})
    keys = gcfg.get("api_keys", [])
    model_name = gcfg.get("model_name", "gemini-2.5-flash")

    if not keys or not HAS_GOOGLE_GENAI:
        raise RuntimeError("Google Gemini 配置缺失或未安装最新版 google-genai SDK。")

    # ✅【改法 2】构造 http_options（只为超时设置服务）
    http_opts = None
    try:
        http_opts = types.HttpOptions(timeout=CLIENT_TIMEOUT_SEC)
    except Exception:
        http_opts = None

    # ✅ 并发模式：固定一个 key；顺序模式：仍按 keys 逐个尝试（原逻辑）
    if key_index is not None:
        keys_to_try = [keys[key_index % len(keys)]]
    else:
        keys_to_try = keys

    for attempt, key in enumerate(keys_to_try, 1):
        try:
            if http_opts is not None:
                client = genai.Client(api_key=key, http_options=http_opts)
            else:
                client = genai.Client(api_key=key)

            cfg = types.GenerateContentConfig(
                temperature=0.5,
                system_instruction=prompt
            )

            log(f"   -> [Gemini] 正在构建批判性综述架构 (使用 Key {attempt}/{len(keys_to_try)})...", "cyan")

            try:
                resp = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model_name,
                    contents=[f"以下是子领域文献 Pack 的内容：\n\n{pack_content}"],
                    config=cfg,
                    timeout=REQUEST_TIMEOUT_SEC,
                )
            except TypeError:
                resp = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model_name,
                    contents=[f"以下是子领域文献 Pack 的内容：\n\n{pack_content}"],
                    config=cfg
                )

            if resp.text:
                return resp.text

        except Exception as e:
            log(f"⚠️ Gemini Key {attempt} 失败: {e}", "yellow")
            await asyncio.sleep(2)

    raise RuntimeError("所有 Gemini Key 均调用失败。")


async def call_openai(pack_content, prompt, config, node_index=None):
    ocfg = config.get("OpenAI_Protocol_Config", {})
    pool = ocfg.get("api_pool", [])
    proxy = config.get("Settings", {}).get("proxy_url", None)

    if not pool:
        raise RuntimeError("OpenAI 节点池为空。")

    timeout = aiohttp.ClientTimeout(total=6000000000)

    # ✅ 并发模式：先固定主节点；若主节点发生异常，再自动切到备用节点池
    if node_index is not None:
        primary_idx = node_index % len(pool)
        primary_node = pool[primary_idx]
        backup_nodes = [node for idx, node in enumerate(pool) if idx != primary_idx]
        nodes_to_try = [primary_node]
    else:
        backup_nodes = []
        nodes_to_try = pool

    async with aiohttp.ClientSession(timeout=timeout) as session:
        switched_to_backup = False
        attempt = 0
        while nodes_to_try:
            node = nodes_to_try.pop(0)
            attempt += 1
            try:
                remark = node.get("remark", f"Node-{attempt}")
                url = f"{node['base_url'].rstrip('/')}{node['api_path']}"
                headers = {"Authorization": f"Bearer {node['api_key']}", "Content-Type": "application/json"}

                # 保持你原来的写法（几乎等于不截断）
                short_pack = pack_content[:99999999999999999999999999999999999999999999999999999999999999999999999999999]

                payload = {
                    "model": node["model_name"],
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"以下是子领域文献 Pack 的内容：\n\n{short_pack}"}
                    ],
                    "temperature": 0.2,
                    
                }

                log(f"   -> [OpenAI] 正在构建批判性综述架构 (调用节点: {remark})...", "cyan")
                async with session.post(url, headers=headers, json=payload, proxy=proxy) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        txt = await resp.text()
                        log(f"⚠️ OpenAI 节点 {remark} 失败 {resp.status}: {txt[:999999]}", "yellow")
            except Exception as e:
                log(f"⚠️ OpenAI 节点异常: {e}", "yellow")
                # 仅在并发模式下：主节点出现异常时，自动启用备用节点池
                if node_index is not None and not switched_to_backup and backup_nodes:
                    nodes_to_try.extend(backup_nodes)
                    switched_to_backup = True
                    log(f"⚠️ 主节点异常，已自动切换到备用节点（共 {len(backup_nodes)} 个）。", "yellow")

            await asyncio.sleep(2)

    raise RuntimeError("所有 OpenAI 节点均调用失败。")


# ==========================================
# 5. 主程序流程
# ==========================================
async def main():
    print("===========================================")
    print("      批判性综述架构生成器 (MEAL 强化版)      ")
    print("===========================================")

    os.makedirs(DIR_OUTPUT_ARCH, exist_ok=True)

    try:
        with open(CONFIG_FILENAME, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        log(f"❌ 找不到配置文件 '{CONFIG_FILENAME}'", "red")
        return

    if not os.path.exists(PACK_FILE_PATH):
        log(f"❌ 找不到 Pack 文件 '{PACK_FILE_PATH}'，请先运行合成脚本。", "red")
        return

    with open(PACK_FILE_PATH, 'r', encoding='utf-8') as f:
        pack_content = f.read()

    log(f"✅ 成功读取 Pack 文件 (字符数: {len(pack_content)})", "green")

    print("\n-------------------------------------------")
    subfield_name = input("✍️  请输入【切入领域】(例如: 远程办公对创造力的影响): ").strip()
    target_words = input("✍️  请输入【目标字数】(例如: 1500): ").strip()
    custom_guidance = input("🧭  可选：请输入【自定义综述导向】(可留空): ").strip()
    full_prompt_in = input("🧩 是否启用【满血提示词（全阶段输出）】? (Y/n): ").strip().lower()
    run_times = input("✍️  请输入【运行次数】(例如: 3): ").strip()
    use_concurrency_in = input("⚡ 是否启用【并发模式】? (y/N): ").strip().lower()
    use_concurrency = use_concurrency_in in ("y", "yes", "1", "true", "t")
    use_full_prompt = full_prompt_in not in ("n", "no", "0", "false", "f")

    if not subfield_name or not target_words or not run_times:
        log("❌ 领域/字数/运行次数不能为空，程序退出。", "red")
        return

    try:
        run_times = int(run_times)
        if run_times <= 0:
            raise ValueError
    except Exception:
        log("❌ 运行次数必须是正整数。", "red")
        return

    final_prompt = PROMPT_TEMPLATE.format(
        subfield_name=subfield_name,
        target_words=target_words
    )
    final_prompt = final_prompt + "\n\n" + build_runtime_output_contract(use_full_prompt)
    if custom_guidance:
        final_prompt = (
            final_prompt
            + "\n\n### User Custom Guidance (可选写作导向)\n"
            + "以下内容是用户提供的写作导向，仅作为叙述侧重点参考，不可覆盖既有硬约束；如冲突，以上方硬约束为准。\n"
            + f"{custom_guidance}\n"
        )

    provider = config.get("Settings", {}).get("interface_type", "openai_protocol")

    # ✅ 关键规则：如果只有一个可用节点/Key，则强制顺序（避免单节点并发）
    openai_pool = config.get("OpenAI_Protocol_Config", {}).get("api_pool", [])
    gemini_keys = config.get("Google_Native_Config", {}).get("api_keys", [])

    capacity = len(openai_pool) if provider == "openai_protocol" else len(gemini_keys)
    if capacity < 2:
        if use_concurrency:
            log("⚠️ 检测到可用节点/Key 少于 2 个，已自动切换为【顺序模式】以避免单节点并发。", "yellow")
        use_concurrency = False

    log("\n🚀 开始调度 AI 大模型生成批判性综述架构...", "cyan")
    log(f"模式：{'并发' if use_concurrency else '顺序'}；轮次：{run_times}；提示词：{'满血(全阶段输出)' if use_full_prompt else '精简(Phase2+4+5前3条)'}", "cyan")

    safe_name = subfield_name.replace("/", "_").replace("\\", "_")

    async def run_one(i: int):
        log(f"🔁 第 {i}/{run_times} 次生成中...", "cyan")

        if provider == "native_response":
            result_md = await call_gemini(
                pack_content, final_prompt, config,
                key_index=(i - 1) if use_concurrency else None
            )
        elif provider == "openai_protocol":
            result_md = await call_openai(
                pack_content, final_prompt, config,
                node_index=(i - 1) if use_concurrency else None
            )
        else:
            raise ValueError(f"未知的协议类型: {provider}")

        if not result_md:
            raise RuntimeError("AI 返回了空结果。")

        result_md = beautify_architecture_md(result_md)

        # ✅ 不覆盖命名：run序号 + 时间戳 + 短UUID（并发同秒也不会撞）
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        uid = uuid.uuid4().hex[:8]
        output_path = os.path.join(
            DIR_OUTPUT_ARCH,
            f"Step3_{safe_name}_综述架构——整体型_run{i:02d}_{ts}_{uid}.md"
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# 综合文献架构与批判性回顾：{subfield_name}\n\n")
            f.write(result_md)

        log(f"✅ 第 {i} 次完成：{output_path}", "green")
        return output_path

    outputs = []
    if use_concurrency:
        tasks = [asyncio.create_task(run_one(i)) for i in range(1, run_times + 1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results, 1):
            if isinstance(r, Exception):
                log(f"❌ 第 {i} 次失败: {r}", "red")
            else:
                outputs.append(r)
    else:
        for i in range(1, run_times + 1):
            try:
                outputs.append(await run_one(i))
            except Exception as e:
                log(f"❌ 第 {i} 次失败: {e}", "red")
                continue

    log(f"\n🎉 结束：成功 {len(outputs)}/{run_times} 次。", "green")


if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
