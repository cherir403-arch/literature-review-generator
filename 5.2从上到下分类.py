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
DIR_OUTPUT_ARCH = "4.2从上到下文献回顾"

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
# Role: 顶级学术期刊主编级顾问
任务：基于提供的文献全集 (Pack)，按照“论点解构-金字塔建模”逻辑撰写一篇高质量文献综述。

【输入设定】
切入领域（选题）：{subfield_name}
目标字数：{target_words} 字。目标字数仅指【Step 4: 综述正文撰写】部分的纯文本内容

【硬约束】
1. 只使用 Pack 内容，引用格式为 (Author, year) [n]。
2. Pack 中列举的所有论文必须在综述中被引用且仅能引用一次。
3. 一句话最多引用两篇文献。
4. 取消暂停，一次性输出以下所有步骤结果。
5. 排版要求：严格使用 Markdown 格式，主阶段标题使用 ###。
6. Pack 内容中列举了多少篇论文，这一份文献综述中就要对所有论文都进行引用。
7. 1篇论文只能在【Step 4: 综述正文撰写】中进行一次引用。
8. 【Step 4: 综述正文撰写】中单独一句话可以引用1篇文献，也可以引用2篇文献。但最多不能超过2篇。
9. 叙事逻辑脱钩方法论（Conceptual over Methodological）： > 严禁在【Step 4: 综述正文撰写】中显性提及实证方法名称（如“利用DID”、“基于PSM-DID”、“采用双重差分法”等）。文献回顾的重心必须锁定在“观点冲突”和“逻辑脉络”上。如果需要强调证据的可靠性，请将其转化为学术语境下的质量描述（如“基于大样本准自然实验”、“通过对异质性效应的稳健性处理”、“从XXX提供的证据表明”等），或者直接隐去方法，仅陈述核心发现。
10. 观点驱动型叙事： 强制采用“批注型引用”风格，即优先陈述完整的学术观点或实证规律，随后以括号形式批注参考文献 (Author, Year) [n]；除非涉及极具开创性的理论对垒，否则严禁以“某学人(年份)认为/发现”作为句首开篇，并鼓励对相同发现的文献进行“聚合引用”以增强论证密度。


【基础知识】（必须阅读和理解并应用在后续写作中）
文献是为综述服务的、综述是为选题服务的。综述的最核心对象是选题中的研究对象。
一.依据研究对象的结构，综述结构可以划分为三种类型：
-研究单位型：只针对研究单位进行综述，适用于研究维度比较宽泛的情况。这种情况下可以选择整体型文献综述的写作。通常篇幅不会很长，在论文结构上，一般和理论框架放在一起。
-研究单位、研究维度型：分别对研究单位和研究维度（或子概念）进行综述。适用于研究单位和研究维度都是独立性较强的学术概念。
-研究单位+研究维度型：将研究单位和研究维度看作一个整体，对整体进行分类，分成几个视角或类别。适用于研究单位和研究维度概念上结合特别紧密的情况。
二.基本推导过程
第一步：首先拆分选题结构，提炼出研究单位、研究维度、限定词等要素，形成基本分类；​
第二步：根据研究单位、研究维度、限定词等要素内容，形成有判断的观点式小标题；​
第三步：以观点式小标题为基本框架，对文献进行分类，并挑选出能够证明该观点的文献，作为参考文献；​
第四步：形成具体的、完整的文献综述；

# 执行步骤（严格按序）

### Step 1: 综述对象定位 (Object Identification)
根据选题拆解“研究单位”与“研究维度”。请明确判断并告知属于哪种形式：
1. 研究单位型：这种组合适合研究单位比较具体，而研究维度比较泛，不需要通过文献综述的形式也能够理解。
2. 研究单位与研究维度型：研究单位和研究维度都比较具体，在文献综述中分别进行阐述，最典型的就是自变量和因变量阐述。
3. 研究单位+研究维度型：将研究对象作为一个整体进行阐述
示例如下：综述对象是根据选题中的研究单位和研究维度确定的（如“文化资本理论视角下的新生代农民工城市融入研究——基于问卷调查法”这个标题中，“新生代”是限定词，“农民工”是研究单位，“城市融入”是研究维度。在A变量影响B变量的选题中，A变量是研究维度，B变量是研究单位）

### Step 2: 论点式小标题构建 (Argumentative Subheadings)
规则是：和第一步中的综述对象一一对应，如果是研究单位型，那么就从3-5个角度阐述研究单位；如果是研究单位和研究维度型，那就分别阐述研究单位和研究维度，如果研究单位或研究维度是由多个核心概念组成，可以对核心概念进行单独阐述；如果是研究单位+研究维度型号，则把研究对象（研究单位+研究维度）作为统一的阐述对象，从3-5个视角进行阐述；使用如“最佳”、“关键”、“重要”等词汇可以为标题加入观点色彩，少用“的”、“是”等静态词；目标受众是核心期刊编辑，尽量使用有内涵的学术概念；使用动词，动词可以赋予标题行动感，使其更具吸引力；不要写成描述性句子，如“内涵”、“特征”、“路径”等。

### Step 3: 金字塔结构关键句 (Pyramid Key Sentences)
将 Step 2 的小标题拓展为 2-3 个分论点组成的金字塔结构关键句，作为每部分的提纲。
- 将第二步小标题拓展成关键句，并一一对应，起到提纲挈领的作用，同时能够按照金字塔结构，形成2-3个分论点。

### Step 4: 综述正文撰写 (Narrative Construction)
根据 Step 3 的关键句，参照金字塔结构撰写正文。
- 语言：中文。
- 逻辑：非罗列式，每一部分必须体现出证据对论点的支撑。
- 字数：满足目标字数 {target_words} 字（正文部分）。
- 重点陈述该领域已达成的共识，以及目前尚未解决的客观技术分歧。
- 确保所有观点均有文献支撑。

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


### Step 5: 参考文献
按照 GBT7714-2015 顺序列出，独立成行，严禁连写。
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
    # 注意：不同版本 types.HttpOptions 的字段名可能略有差异；下面是官方推荐用法之一。
    http_opts = None
    try:
        http_opts = types.HttpOptions(timeout=CLIENT_TIMEOUT_SEC)
    except Exception:
        http_opts = None  # 若当前 SDK 不支持该构造，则退化为仅请求级 timeout（见下）

    # ✅ 并发模式：固定一个 key；顺序模式：仍按 keys 逐个尝试（原逻辑）
    if key_index is not None:
        keys_to_try = [keys[key_index % len(keys)]]
    else:
        keys_to_try = keys

    for attempt, key in enumerate(keys_to_try, 1):
        try:
            # ✅【改法 2】Client 级超时（如当前 SDK 支持）
            if http_opts is not None:
                client = genai.Client(api_key=key, http_options=http_opts)
            else:
                client = genai.Client(api_key=key)

            cfg = types.GenerateContentConfig(
                temperature=0.2,
                system_instruction=prompt
            )

            log(f"   -> [Gemini] 正在构建批判性综述架构 (使用 Key {attempt}/{len(keys_to_try)})...", "cyan")

            # ✅【改法 2】请求级 timeout：优先传入 generate_content
            # 如果当前 SDK 版本不接受 timeout 参数，会抛 TypeError，我们捕获后自动回退到不传 timeout 的调用（不改其它逻辑）。
            try:
                resp = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model_name,
                    contents=[f"以下是子领域文献 Pack 的内容：\n\n{pack_content}"],
                    config=cfg,
                    timeout=REQUEST_TIMEOUT_SEC,
                )
            except TypeError:
                # 回退：该版本 generate_content 不支持 timeout 参数
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
                payload = {
                    "model": node["model_name"],
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"以下是子领域文献 Pack 的内容：\n\n{pack_content}"}
                    ],
                    "temperature": 0.2
                }

                log(f"   -> [OpenAI] 正在构建批判性综述架构 (调用节点: {remark})...", "cyan")
                async with session.post(url, headers=headers, json=payload, proxy=proxy) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        txt = await resp.text()
                        log(f"⚠️ OpenAI 节点 {remark} 失败 {resp.status}: {txt[:100]}", "yellow")
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
    run_times = input("✍️  请输入【运行次数】(例如: 3): ").strip()
    use_concurrency_in = input("⚡ 是否启用【并发模式】? (y/N): ").strip().lower()
    use_concurrency = use_concurrency_in in ("y", "yes", "1", "true", "t")

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
    log(f"模式：{'并发' if use_concurrency else '顺序'}；轮次：{run_times}", "cyan")

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

        # 核心排版清洗 (已适配 Phase 5)
        result_md = beautify_architecture_md(result_md)

        # ✅ 不覆盖命名：run序号 + 时间戳 + 短UUID（并发同秒也不会撞）
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        uid = uuid.uuid4().hex[:8]
        output_path = os.path.join(
            DIR_OUTPUT_ARCH,
            f"Step3_{safe_name}_综述架构——从上到下分类_run{i:02d}_{ts}_{uid}.md"
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
