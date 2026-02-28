# -*- coding: utf-8 -*-
import os
import json
import asyncio
import aiohttp
import time
import re
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
DIR_OUTPUT_MODEL = "3.2三三三模型"

# ==========================================
# 2. 动态提示词模板
# ==========================================
PROMPT_TEMPLATE = """
文献筛选三三三模型（Field Mapping 3-3-3）
你是资深文献综述研究顾问。请基于单一子领域 Pack，完成“3人物-3观点-3文献-3缺口”的结构化洞察。

【输入设定】
切入领域：{subfield_name}
目标字数：{target_words}字左右

【硬约束】
1. 只使用 Pack 内容，不得引入外部文献或常识补全。
2. 如证据不足，明确标注“Pack 证据不足”。
3. 在引用的语句中使用（Author,year）[n]，其中[n]为参考文献列表中的引用条目的序号。
4. 排版要求：严格使用 Markdown 格式，主标题使用 ###。

【输出结构】（严格按序）

### A. 三类核心学术角色（The Who）
- 奠基者（Founder）
- 挑战者（Challenger）
- 集成者（Synthesizer）
每类给出：代表学者/代表研究路径、核心贡献、与另外两类的关系一句话

### B. 三条核心观点轴线（The What）
每条轴线必须包含：轴线名称（如“效率逻辑 vs 公平逻辑”）、支持证据簇（对应文献）、争议点与适用边界

### C. 三篇“锚点文献”（The Evidence）
选择 Pack 中最能支撑该领域结构的 3 篇文献，逐篇给出：为什么是锚点、对后续综述写作的价值

### D. 三个研究缺口候选（The Gap）
- Gap-1：边界条件缺口
- Gap-2：机制解释缺口
- Gap-3：情境/对象迁移缺口
每个缺口需写：既有研究已解释什么、尚未解释什么、为什么值得研究

### E. 综述推进建议
用一段话说明：该子领域在 Step 2 最适合采用哪种叙述模式（overall/top-down/bottom-up）。

### F. 参考文献
仅列正文实际引用条目（GBT7714-2015）。
**排版强约束**：请务必以 [1], [2], [3] 的编号形式独立成行输出，每一行只写一条参考文献，绝对不要把多条文献连在一行！
"""


# ==========================================
# 3. 代码级强制清洗与排版函数 (专属三三三模型)
# ==========================================
def beautify_333_markdown(text):
    if not text:
        return text

    # 1. 强制纠正大标题格式 (防止 AI 忘记加 ### 导致 A. B. C. 变成普通文本)
    text = re.sub(r'(?m)^(?!\s*#)\s*([A-F]\.\s+.*?)$', r'### \1', text)

    # 2. 定位到“### F. 参考文献”这一节进行切分
    match = re.search(r'(### F\.\s*参考文献.*?\n)(.*)', text, flags=re.IGNORECASE | re.DOTALL)

    if match:
        before_refs = text[:match.start(2)]
        refs_content = match.group(2)

        # 3. 强行切割参考文献：找到所有 "[1]", "[2]" 并在它们前面加换行符
        cleaned_refs = re.sub(r'\s*\[(\d+)\]\s*', r'\n[\1] ', refs_content)
        cleaned_refs = re.sub(r'\n{2,}', r'\n', cleaned_refs).strip()

        # 重新拼接文本
        text = before_refs + cleaned_refs + '\n'

    # 4. 标题前强制加空行，让版面更透气
    text = re.sub(r'(?<!\n)\n(### [A-F]\.)', r'\n\n\1', text)

    return text.strip()


def log(msg, color="white"):
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    colors = {"green": "\033[92m", "cyan": "\033[96m", "yellow": "\033[93m", "red": "\033[91m"}
    print(f"{colors.get(color, '')}[{timestamp}] {msg}\033[0m")


# ==========================================
# 4. API 调用器 (复用之前的配置逻辑)
# ==========================================
async def call_gemini(pack_content, prompt, config):
    gcfg = config.get("Google_Native_Config", {})
    keys = gcfg.get("api_keys", [])
    model_name = gcfg.get("model_name", "gemini-2.5-flash")

    if not keys or not HAS_GOOGLE_GENAI:
        raise RuntimeError("Google Gemini 配置缺失或未安装SDK。")

    for attempt, key in enumerate(keys, 1):
        try:
            client = genai.Client(api_key=key)
            cfg = types.GenerateContentConfig(temperature=0.3, system_instruction=prompt)
            log(f"   -> [Gemini] 正在构建模型框架 (使用 Key {attempt}/{len(keys)})...", "cyan")

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


async def call_openai(pack_content, prompt, config):
    ocfg = config.get("OpenAI_Protocol_Config", {})
    pool = ocfg.get("api_pool", [])
    proxy = config.get("Settings", {}).get("proxy_url", None)

    if not pool: raise RuntimeError("OpenAI 节点池为空。")

    timeout = aiohttp.ClientTimeout(total=180)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for attempt, node in enumerate(pool, 1):
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

                log(f"   -> [OpenAI] 正在构建模型框架 (调用节点: {remark})...", "cyan")
                async with session.post(url, headers=headers, json=payload, proxy=proxy) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        txt = await resp.text()
                        log(f"⚠️ OpenAI 节点 {remark} 失败 {resp.status}: {txt[:100]}", "yellow")
            except Exception as e:
                log(f"⚠️ OpenAI 节点异常: {e}", "yellow")

            await asyncio.sleep(2)

    raise RuntimeError("所有 OpenAI 节点均调用失败。")


# ==========================================
# 5. 主程序流程
# ==========================================
async def main():
    print("===========================================")
    print("    文献筛选三三三模型生成器 (Field Mapping)  ")
    print("===========================================")

    os.makedirs(DIR_OUTPUT_MODEL, exist_ok=True)

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
    target_words = input("✍️  请输入【目标字数】(例如: 2000): ").strip()

    if not subfield_name or not target_words:
        log("❌ 领域或字数不能为空，程序退出。", "red")
        return

    final_prompt = PROMPT_TEMPLATE.format(
        subfield_name=subfield_name,
        target_words=target_words
    )

    provider = config.get("Settings", {}).get("interface_type", "openai_protocol")
    log("\n🚀 开始调度 AI 大模型生成三三三模型洞察...", "cyan")

    try:
        if provider == "native_response":
            result_md = await call_gemini(pack_content, final_prompt, config)
        elif provider == "openai_protocol":
            result_md = await call_openai(pack_content, final_prompt, config)
        else:
            raise ValueError(f"未知的协议类型: {provider}")

        if not result_md:
            raise RuntimeError("AI 返回了空结果。")

        # 【核心步骤】使用正则函数进行洗稿排版，确保 A~F 标题及参考文献完美输出
        result_md = beautify_333_markdown(result_md)

        safe_name = subfield_name.replace("/", "_").replace("\\", "_")
        output_path = os.path.join(DIR_OUTPUT_MODEL, f"Step2_{safe_name}_三三三模型.md")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# 文献筛选三三三模型：{subfield_name}\n\n")
            f.write(result_md)

        log(f"\n🎉 结构化洞察生成成功并已完成代码排版！\n📁 文件已保存至: {output_path}", "green")

    except Exception as e:
        log(f"\n❌ 生成失败: {e}", "red")


if __name__ == "__main__":
    import sys

    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())