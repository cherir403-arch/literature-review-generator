# -*- coding: utf-8 -*-
import os
import glob

# ==========================================
# 文件夹与文件配置
# ==========================================
DIR_INPUT_MD = "1.3完成后的md_整表"
DIR_OUTPUT_PACK = "2.1合成pack文件"
OUTPUT_FILENAME = "pack.md"


def merge_markdown_files():
    print("===========================================")
    print("        Markdown 批量合成打包工具          ")
    print("===========================================")

    # 1. 确保输入文件夹存在
    if not os.path.exists(DIR_INPUT_MD):
        print(f"❌ 找不到输入目录 '{DIR_INPUT_MD}'，请检查路径！")
        return

    # 2. 创建输出文件夹（如果不存在会自动创建）
    os.makedirs(DIR_OUTPUT_PACK, exist_ok=True)
    output_path = os.path.join(DIR_OUTPUT_PACK, OUTPUT_FILENAME)

    # 3. 扫描所有的 .md 文件
    md_files = glob.glob(os.path.join(DIR_INPUT_MD, "*.md"))

    if not md_files:
        print(f"⚠️ 在 '{DIR_INPUT_MD}' 目录下没有找到任何 .md 文件。")
        return

    # 对文件进行排序（按文件名拼音或数字顺序），确保每次合成的顺序固定
    md_files.sort()

    print(f"🚀 共找到 {len(md_files)} 个 Markdown 文件，准备开始合成...\n")

    # 4. 执行拼接写入
    with open(output_path, "w", encoding="utf-8") as outfile:
        # 在大文件开头加个总标题（可选）
        outfile.write("# 📚 文献逆向工程解析总集 (Pack)\n\n")
        outfile.write(f"> 共收录 {len(md_files)} 篇文献分析\n\n---\n\n")

        for index, file_path in enumerate(md_files, 1):
            filename = os.path.basename(file_path)
            print(f"   -> [{index}/{len(md_files)}] 正在拼装: {filename}")

            with open(file_path, "r", encoding="utf-8") as infile:
                content = infile.read()

                # 将当前文件内容写入总文件
                outfile.write(content)

                # 如果不是最后一个文件，就在末尾追加一个分割线和空行，保证排版美观
                if index < len(md_files):
                    outfile.write("\n\n<br>\n\n***\n\n<br>\n\n")
                else:
                    outfile.write("\n\n")  # 最后一个文件只加普通换行

    print("\n===========================================")
    print(f"✅ 合成大业完毕！共无缝拼接了 {len(md_files)} 个文件。")
    print(f"📁 最终版合集已保存在: {output_path}")
    print("===========================================")


if __name__ == "__main__":
    merge_markdown_files()