# -*- coding: utf-8 -*-
import os
import sys
import logging
import sys
import io

# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
# 强制将标准输出设置为 UTF-8，解决 EXE 在 Windows 下打印 Emoji 报错的问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
# 尝试导入 send2trash (用于安全放入回收站)
try:
    from send2trash import send2trash
except ImportError:
    print("❌ 缺少依赖库，请先运行: pip install send2trash")
    print("   (这个库能确保文件是“放入回收站”而不是“永久删除”，防止误删)")
    input("按回车键退出...")
    sys.exit(1)

# =========================================================
# ⚙️ 目标文件夹列表
# =========================================================

TARGET_FOLDERS = [
    "1.2已完成文件_逐篇",
    "1.3完成后的md_整表",
    "2.1合成pack文件",
    "3.1综述背景",
    "3.2三三三模型",
    "4.1整体型文献回顾",
    "4.2从上到下文献回顾",
    "4.3隐喻型文献回顾",
    "4.4范式型文献回顾",
    "5.2政策分析报告",
    "5.4概念分析报告",
    "5.研究缺口与破题",
]

# =========================================================
# 🚀 主程序
# =========================================================

logging.basicConfig(level=logging.INFO, format='%(message)s')


def main():
    print("\n" + "=" * 50)
    print("   🗑️  分类文件夹 PDF 清理工具 (送入回收站)")
    print("=" * 50 + "\n")

    # 1. 扫描文件，先告诉用户有多少文件要删
    files_to_delete = []

    print("正在扫描以下文件夹：")
    for folder in TARGET_FOLDERS:
        if not os.path.exists(folder):
            continue

        print(f" - {folder}")
        for f in os.listdir(folder):
            if f.lower().endswith(('.pdf', '.md')):
                full_path = os.path.join(folder, f)
                files_to_delete.append(full_path)

    count = len(files_to_delete)

    if count == 0:
        print(f"\n✅ 扫描完毕：这些文件夹里没有任何 PDF 文件。")
        input("按回车键退出...")
        return

    # 2. 询问用户 (Y/N)
    print(f"\n⚠️  警告：共发现 {count} 个 PDF 文件。")
    print(f"   执行操作后，这些文件将被移动到【系统回收站】。")

    confirm = input("\n❓ 确认要删除吗？(输入 Y 确认，输入 N 取消): ").strip().upper()

    # 3. 执行逻辑
    if confirm == 'Y':
        print("\n🚀 开始执行清理...")
        deleted_count = 0

        for file_path in files_to_delete:
            try:
                # 核心动作：送入回收站
                send2trash(file_path)
                print(f"   [已删除] {os.path.basename(file_path)}")
                deleted_count += 1
            except Exception as e:
                print(f"   [❌ 失败] {os.path.basename(file_path)}: {e}")

        print("\n" + "=" * 50)
        print(f"🎉 清理完成！共将 {deleted_count} 个文件送入回收站。")
        print("=" * 50)

    else:
        print("\n🚫 操作已取消。文件未变动。")

    input("\n按回车键退出...")


if __name__ == "__main__":
    main()