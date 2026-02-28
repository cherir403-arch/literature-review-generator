# -*- coding: utf-8 -*-
import os
import re
import glob

# ==========================================
# 1. 配置路径
# ==========================================
DIR_INPUT_MD = "1.3完成后的md_整表"  # 你逐篇解析生成的文件夹
OUTPUT_FILE = "精华证据包_供综述使用.md"  # 最终喂给大模型的瘦身版文件


def extract_essence(file_path):
    """增强版正则：提高对标题文字和空格的容错率"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用 re.IGNORECASE 和更宽松的匹配逻辑
    # 匹配 ### 0) 到 ### 1) 之前
    pattern_0 = r"(### 0\).*?)(?=### 1\))"
    # 匹配 ### 6) 到 ### 7) 之前
    pattern_6 = r"(### 6\).*?)(?=### 7\))"
    # 匹配 ### 7) 到文件结尾
    pattern_7 = r"(### 7\).*)$"

    # 统一使用 re.S (DOTALL) 模式
    match_0 = re.search(pattern_0, content, re.S | re.I)
    match_6 = re.search(pattern_6, content, re.S | re.I)
    match_7 = re.search(pattern_7, content, re.S | re.I)

    extracted_parts = []

    if match_0:
        extracted_parts.append(match_0.group(1).strip())
    else:
        print(f"DEBUG: {os.path.basename(file_path)} 缺失 0) 部分")

    if match_6:
        text_6 = match_6.group(1).strip()
        # 清洗括号提示语
        text_6 = re.sub(r'\n\s*（写 700-750 字.*?）', '', text_6)
        extracted_parts.append(text_6)
    else:
        print(f"DEBUG: {os.path.basename(file_path)} 缺失 6) 部分")

    if match_7:
        extracted_parts.append(match_7.group(1).strip())
    else:
        print(f"DEBUG: {os.path.basename(file_path)} 缺失 7) 部分")

    if len(extracted_parts) == 3:
        return "\n\n".join(extracted_parts)
    return None


def main():
    md_files = glob.glob(os.path.join(DIR_INPUT_MD, "*.md"))
    if not md_files:
        print(f"❌ 文件夹 [{DIR_INPUT_MD}] 是空的或不存在！")
        return

    print(f"🚀 开始提取精华，共计发现 {len(md_files)} 份文献笔记...")

    success_count = 0
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out_f:
        out_f.write("# 核心精华证据包 (已剔除推演细节，仅保留锚点、总结与引用)\n\n")

        for file in md_files:
            filename = os.path.basename(file)

            essence = extract_essence(file)
            if essence:
                out_f.write(f"=================================================================\n")
                out_f.write(f"【文献来源】: {filename}\n")
                out_f.write(f"=================================================================\n\n")
                out_f.write(f"{essence}\n\n\n")
                success_count += 1
                print(f"✅ 提取成功: {filename}")
            else:
                print(f"⚠️ 提取不完整跳过: {filename} (可能原文件缺少对应标题)")

    print(f"\n🎉 提取完毕！成功瘦身 {success_count} 篇文献，精华包已保存至: {OUTPUT_FILE}")
    print(f"💡 现在你可以把这个文件直接喂给最终的综述整合 AI 了，Token 消耗将大幅降低！")


if __name__ == "__main__":
    main()