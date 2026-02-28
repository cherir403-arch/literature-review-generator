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
DIR_OUTPUT_ARCH = "4.3隐喻型文献回顾"

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
# Role: 资深学术编辑与理论构建专家

## Background
我正在撰写一篇高质量的学术文献综述。我有若干篇文献的摘要/笔记，但我不想进行传统的“罗列式”综述。我希望采用“从下到上（Bottom-Up）”的归纳法，结合“扎根理论三级编码”和“隐喻与功能分类法”，构建一个具有创新性和逻辑深度的理论框架。

## Input
切入领域：{subfield_name}
文献来源：读取自下方的 pack.md 文本。
正文目标字数：{target_words} 字（注：该指标仅限【3. 创新性综述框架】的正文，不包括编码过程分析表）。

【硬约束】
1. 只使用 Pack 内容，引用格式为 (Author, year) [n]。
2. Pack 中列举的所有论文必须在综述中被引用且仅能引用一次。
3. 一句话最多引用两篇文献。
4. 取消暂停，一次性输出以下所有步骤结果。
5. 排版要求：严格使用 Markdown 格式，主阶段标题使用 ###。
6. Pack 内容中列举了多少篇论文，这一份文献综述中就要对所有论文都进行引用。
7. 1篇论文只能在文献综述中进行一次引用。
8. 【3. 创新性综述框架】单独一句话可以引用1篇文献，也可以引用2篇文献。但最多不能超过两篇。
9. 叙事逻辑脱钩方法论（Conceptual over Methodological）： > 严禁在【3. 创新性综述框架】中显性提及实证方法名称（如“利用DID”、“基于PSM-DID”、“采用双重差分法”等）。文献回顾的重心必须锁定在“观点冲突”和“逻辑脉络”上。如果需要强调证据的可靠性，请将其转化为学术语境下的质量描述（如“基于大样本准自然实验”、“通过对异质性效应的稳健性处理”、“从XXX提供的证据表明”等），或者直接隐去方法，仅陈述核心发现。


【基础知识】（必须阅读和理解并应用在后续写作中）
一.归类中的基础方法：三级编码
借鉴扎根理论的三级编码，形成归类文献的三级编码。
- 一级编码（开放式编码 Open Coding）： 打碎文献。给每一个具体的观点、变量、发现贴上最初始的标签（Label）。
- 二级编码（主轴编码 Axial Coding）： 找关系。将一级标签进行聚类，寻找它们之间的因果、互动或功能联系，形成副范畴（Sub-category）。
- 三级编码（选择性编码 Selective Coding）： 定核心。找到一个核心范畴（Core Category），统领所有副范畴，形成一个完整的理论故事。
二.隐喻型归类法
- 隐喻：用一个大家熟悉的系统（如生物系统、机械系统、生态系统、戏剧舞台）来类比研究领域，从而构建分类框架。
- 隐喻型归类：不只看文献说了什么（Content），而是看文献中的概念在整个机制中起什么作用（Function），并用一个形象的系统（Metaphor）将其串联起来

## Task
请阅读【文献材料 (Pack)】，并严格按照以下三个步骤进行分析和重构：

### Step 1: 一级编码（开放式编码 - 功能化）
* 动作： 打碎文献。不要只提取名词，要提取“功能性动词”或“角色标签”。
* 思考核心： 这个变量/观点在研究对象的结果中起到了什么作用？是加速、阻碍、过滤、还是作为容器？
* 输出： 提取出若干个【功能标签】。

### Step 2: 二级编码（主轴编码 - 聚类化）
* 动作： 寻找关系。将步骤1中的功能标签进行归类。
* 思考核心： 哪些功能是相似的？它们之间存在什么逻辑关系（如：动力 vs 阻力，输入 vs 输出，宏观 vs 微观）？
* 输出： 归纳出 3 个左右的【功能群组】。

### Step 3: 三级编码（选择性编码 - 隐喻化）
* 动作： 确定核心隐喻并撰写综述。
* 思考核心： 观察步骤 2 的功能群组，想象这像一个什么系统？（例如：生态系统、机械驱动系统、一场博弈、一次英雄之旅等）。
* 要求： 
    1. 必须引用 Pack 中列出的所有论文，且 1 篇论文仅限引用一次。一句话最多引用 2 篇文献。
    2. 引用格式为 (Author, year) [n]。
    3. 按照隐喻逻辑，撰写出总字数约 {target_words} 字的综述正文。
    4. 基于该隐喻，重新命名所有的二级群组，形成极具理论感的“综述小标题”。

## Constraint
1. 拒绝平庸： 不要使用“定义”、“分类”、“影响因素”这种通用标题。
2. 注重逻辑： 标题必须体现出文献之间的互动和机制。
3. 学术规范： 保持语言的学术性，同时兼具生动性。
4. 取消暂停： 一次性完成所有步骤的输出。

## Output Format (请严格执行)

### 1. 编码过程分析表
| 文献要点 (提取自 Pack) | 一级编码 (功能/角色标签) | 二级编码 (归属的功能群组) | 参考条目(Author, year) [n] |
| :--- | :--- | :--- | :--- |
| ... | ... | ... | ... |

### 2. 核心隐喻选择
我选择的隐喻模型是： [例如：车辆驾驶模型 / 植物生长模型]
理由： [简述为什么这批文献适合这个隐喻]

### 3. 创新性综述框架 (最终产出)
总标题建议： [基于隐喻的学术标题]

* 3.1 [隐喻化的一级标题]：[学术化的解释]
    - [撰写该部分的综述正文，确保引用文献并体现功能逻辑]
* 3.2 [隐喻化的一级标题]：[学术化的解释]
    - [综述正文...]
* 3.3 [隐喻化的一级标题]：[学术化的解释]
    - [综述正文...]

### 4. 参考文献
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
async def call_gemini(pack_content, prompt, config):
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

    for attempt, key in enumerate(keys, 1):
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

            log(f"   -> [Gemini] 正在构建批判性综述架构 (使用 Key {attempt}/{len(keys)})...", "cyan")

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

    if not subfield_name or not target_words:
        log("❌ 领域或字数不能为空，程序退出。", "red")
        return

    final_prompt = PROMPT_TEMPLATE.format(
        subfield_name=subfield_name,
        target_words=target_words
    )

    provider = config.get("Settings", {}).get("interface_type", "openai_protocol")
    log("\n🚀 开始调度 AI 大模型生成批判性综述架构...", "cyan")

    try:
        if provider == "native_response":
            result_md = await call_gemini(pack_content, final_prompt, config)
        elif provider == "openai_protocol":
            result_md = await call_openai(pack_content, final_prompt, config)
        else:
            raise ValueError(f"未知的协议类型: {provider}")

        if not result_md:
            raise RuntimeError("AI 返回了空结果。")

        # 核心排版清洗 (已适配 Phase 5)
        result_md = beautify_architecture_md(result_md)

        safe_name = subfield_name.replace("/", "_").replace("\\", "_")
        output_path = os.path.join(DIR_OUTPUT_ARCH, f"Step3_{safe_name}_综述架构.md")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# 综合文献架构与批判性回顾：{subfield_name}\n\n")
            f.write(result_md)

        log(f"\n🎉 架构生成成功并已完成代码级排版！\n📁 文件已保存至: {output_path}", "green")

    except Exception as e:
        log(f"\n❌ 生成失败: {e}", "red")


if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
