# -*- coding: utf-8 -*-
import os
import json
import asyncio
import aiohttp
import time
import re
import uuid
from contextlib import asynccontextmanager

try:
    from google import genai
    from google.genai import types

    HAS_GOOGLE_GENAI = True
except Exception:
    HAS_GOOGLE_GENAI = False

# ==========================================
# 1. 基础路径配置
# ==========================================
CONFIG_FILENAME = "3.综述背景.json"
PACK_FILE_PATH = os.path.join("2.1合成pack文件", "pack.md")
DIR_OUTPUT_BG = "3.1综述背景"

# ==========================================
# 2. 动态提示词模板
# ==========================================
PROMPT_TEMPLATE = """
Step 1 综述背景生成模板
你是顶级期刊风格的综述写作顾问。请基于我提供的子领域 Pack 内容，生成“描述-评价-引题”三段式背景文本。

【输入设定】
切入领域：{subfield_name}
目标字数：{target_words}字左右

【硬约束】
1. 只使用 Pack 中“核心价值总结 + 参考文献条目”的信息。
2. 不逐篇罗列，必须做概念聚合。
3. 不讨论研究缺口与创新性（留给后续步骤）。
4. 在引用的语句中使用（Author,year）[n]，其中[n]为参考文献列表中的引用条目的序号。例如：(Su & Cheng, 2023)[2]。
5. 排版要求：严格使用 Markdown 格式，主标题使用 ###。

【输出结构】（严格按序）

### 1) 描述（Description）
界定该议题在学科中的研究重要性
提炼 3-5 个高频概念/理论标签

### 2) 评价（Evaluation）
归纳主要研究方法与证据结构
总结已有研究的解释贡献与边界

### 3) 引题（Lead-in）
收敛到一个可继续展开的解释视角
作为后续步骤的自然过渡，不提前写 Gap

### 4) 参考文献
仅列正文引用到的文献（GBT7714-2015）。
**排版强约束**：请务必以 [1], [2], [3] 的编号形式独立成行输出，每一行只写一条参考文献，绝对不要把多条文献连在一行！
按照 GBT7714-2015 顺序列出，每一条参考独立成行，每一行后面加上一个可以被md文件识别的换行符，严禁连写。
"""


# ==========================================
# [新增] 代码级强制清洗与排版函数
# ==========================================
def beautify_step1_markdown(text):
    if not text:
        return text

    # 1. 定位到“### 4) 参考文献”这一节
    # 将文本一分为二：前面的正文部分，和后面的参考文献部分
    match = re.search(r'(### 4\)\s*参考文献.*?\n)(.*)', text, flags=re.IGNORECASE | re.DOTALL)

    if match:
        before_refs = text[:match.start(2)]
        refs_content = match.group(2)

        # 2. 强行切割参考文献：找到所有类似 "[1]", "[2]" 的标号，并在它们前面加换行符
        # 正则含义：匹配任意空白符 + [数字] + 任意空白符，替换为 "\n[数字] "
        cleaned_refs = re.sub(r'\s*\[(\d+)\]\s*', r'\n[\1] ', refs_content)

        # 去除可能产生的多余连续空行
        cleaned_refs = re.sub(r'\n{2,}', r'\n', cleaned_refs).strip()

        # 3. 重新拼接文本
        text = before_refs + cleaned_refs + '\n'

    # 4. 顺便把所有主标题前强制加空行，让排版更透气
    text = re.sub(r'(?<!\n)\n(### \d\))', r'\n\n\1', text)

    return text.strip()


def log(msg, color="white"):
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    colors = {"green": "\033[92m", "cyan": "\033[96m", "yellow": "\033[93m", "red": "\033[91m"}
    print(f"{colors.get(color, '')}[{timestamp}] {msg}\033[0m")


# ==========================================
# 3. 极简版 API 调用器
# ==========================================
async def call_gemini(pack_content, prompt, config, key_index=None):
    gcfg = config.get("Google_Native_Config", {})
    keys = gcfg.get("api_keys", [])
    model_name = gcfg.get("model_name", "gemini-2.5-flash")

    if not keys or not HAS_GOOGLE_GENAI:
        raise RuntimeError("Google Gemini 配置缺失或未安装SDK。")

    # ✅ 并发模式：固定一个 key；顺序模式：仍按 keys 逐个尝试（原逻辑）
    if key_index is not None:
        keys_to_try = [keys[key_index % len(keys)]]
    else:
        keys_to_try = keys

    for attempt, key in enumerate(keys_to_try, 1):
        try:
            client = genai.Client(api_key=key)
            cfg = types.GenerateContentConfig(temperature=0.3, system_instruction=prompt)
            log(f"   -> [Gemini] 正在思考中 (使用 Key {attempt}/{len(keys_to_try)})...", "cyan")

            resp = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=[f"以下是子领域文献 Pack 的内容：\n\n{pack_content}"],
                config=cfg
            )
            if resp.text: return resp.text
        except Exception as e:
            log(f"⚠️ Gemini Key {attempt} 失败: {e}", "yellow")
            await asyncio.sleep(2)

    raise RuntimeError("所有 Gemini Key 均调用失败。")


async def call_openai(pack_content, prompt, config, node_index=None):
    ocfg = config.get("OpenAI_Protocol_Config", {})
    pool = ocfg.get("api_pool", [])
    proxy = config.get("Settings", {}).get("proxy_url", None)

    if not pool: raise RuntimeError("OpenAI 节点池为空。")

    timeout = aiohttp.ClientTimeout(total=180)

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
                    "temperature": 0.3
                }

                log(f"   -> [OpenAI] 正在思考中 (调用节点: {remark})...", "cyan")
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
# 4. 主程序流程
# ==========================================
async def main():
    print("===========================================")
    print("         综述背景生成器 (Step 1)           ")
    print("===========================================")

    os.makedirs(DIR_OUTPUT_BG, exist_ok=True)

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
    subfield_name = input("✍️  请输入【切入领域】(例如: 企业数字化转型与创新绩效): ").strip()
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

    log("\n🚀 开始调度 AI 大模型生成综述背景...", "cyan")
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

        # 【核心修改点】使用底层代码进行洗稿排版
        result_md = beautify_step1_markdown(result_md)

        # ✅ 不覆盖命名：run序号 + 时间戳 + 短UUID（并发同秒也不会撞）
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        uid = uuid.uuid4().hex[:8]
        output_path = os.path.join(
            DIR_OUTPUT_BG,
            f"Step1_{safe_name}_背景_run{i:02d}_{ts}_{uid}.md"
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# 综述背景：{subfield_name}\n\n")
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
    import sys

    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
