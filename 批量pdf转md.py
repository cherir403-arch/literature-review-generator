# -*- coding: utf-8 -*-
"""
批量将 PDF 转为 Markdown，默认扫描：
1) 1.1待处理文件_逐篇
2) 1.2已完成文件_逐篇

输出目录结构：
pdf转md/
  ├─ 1.1待处理文件_逐篇/
  │   ├─ xxx.md
  │   └─ xxx_assets/
  └─ 1.2已完成文件_逐篇/
      ├─ yyy.md
      └─ yyy_assets/

可通过参数扩展扫描目录，便于后续模块化添加。
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import fitz  # PyMuPDF
import pdfplumber


DEFAULT_SOURCE_FOLDERS = [
    "1.1待处理文件_逐篇",
    "1.2已完成文件_逐篇",
]

SOURCE_ALIASES = {
    "1.1": "1.1待处理文件_逐篇",
    "1.2": "1.2已完成文件_逐篇",
}

DEFAULT_OUTPUT_ROOT = "pdf转md"


@dataclass
class ConvertConfig:
    source_folders: List[Path]
    output_root: Path
    recursive: bool = True
    include_images: bool = True
    include_tables: bool = True
    overwrite: bool = False
    dry_run: bool = False


def log(message: str) -> None:
    print(message)


def resolve_source(source: str) -> Path:
    return Path(SOURCE_ALIASES.get(source, source))


def normalize_cell(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    text = text.replace("|", "\\|")
    return text


def table_to_markdown(table: List[List[object]]) -> List[str]:
    if not table:
        return []

    max_cols = max(len(row) for row in table if row) if table else 0
    if max_cols == 0:
        return []

    normalized_rows: List[List[str]] = []
    for row in table:
        cells = [normalize_cell(cell) for cell in row]
        if len(cells) < max_cols:
            cells.extend([""] * (max_cols - len(cells)))
        normalized_rows.append(cells)

    header = normalized_rows[0]
    if all(not cell for cell in header):
        header = [f"Column {i}" for i in range(1, max_cols + 1)]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * max_cols) + " |",
    ]

    for row in normalized_rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def extract_tables_by_page(pdf_path: Path) -> Dict[int, List[List[List[object]]]]:
    tables_by_page: Dict[int, List[List[List[object]]]] = {}
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            try:
                raw_tables = page.extract_tables() or []
            except Exception:
                raw_tables = []

            valid_tables: List[List[List[object]]] = []
            for table in raw_tables:
                if not table:
                    continue
                if not any(any((cell or "").strip() for cell in row) for row in table):
                    continue
                valid_tables.append(table)

            if valid_tables:
                tables_by_page[page_index] = valid_tables
    return tables_by_page


def extract_images_by_page(
    doc: fitz.Document, assets_dir: Path
) -> Dict[int, List[Path]]:
    images_by_page: Dict[int, List[Path]] = {}
    assets_dir.mkdir(parents=True, exist_ok=True)

    for page_index in range(len(doc)):
        page = doc[page_index]
        image_refs = page.get_images(full=True)
        if not image_refs:
            continue

        seen_xrefs = set()
        saved_paths: List[Path] = []

        for image_index, image_info in enumerate(image_refs, start=1):
            xref = image_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                image = doc.extract_image(xref)
            except Exception:
                continue

            image_bytes = image.get("image")
            image_ext = image.get("ext", "png")
            if not image_bytes:
                continue

            image_name = f"page_{page_index + 1:03d}_img_{image_index:02d}.{image_ext}"
            image_path = assets_dir / image_name
            image_path.write_bytes(image_bytes)
            saved_paths.append(image_path)

        if saved_paths:
            images_by_page[page_index + 1] = saved_paths

    return images_by_page


def extract_text_by_page(doc: fitz.Document) -> Dict[int, str]:
    text_by_page: Dict[int, str] = {}
    for page_index in range(len(doc)):
        text = doc[page_index].get_text("text").strip()
        text_by_page[page_index + 1] = text
    return text_by_page


def build_markdown(
    pdf_path: Path,
    text_by_page: Dict[int, str],
    tables_by_page: Dict[int, List[List[List[object]]]],
    images_by_page: Dict[int, List[Path]],
    md_output_path: Path,
) -> str:
    lines: List[str] = [
        f"# {pdf_path.stem}",
        "",
        f"- Source PDF: `{pdf_path.as_posix()}`",
        "",
    ]

    page_numbers = sorted(
        set(text_by_page.keys()) | set(tables_by_page.keys()) | set(images_by_page.keys())
    )

    for page_no in page_numbers:
        lines.append(f"## Page {page_no}")
        lines.append("")

        page_text = text_by_page.get(page_no, "").strip()
        if page_text:
            lines.append(page_text)
            lines.append("")
        else:
            lines.append("*(No text extracted on this page.)*")
            lines.append("")

        page_tables = tables_by_page.get(page_no, [])
        if page_tables:
            lines.append("### Tables")
            lines.append("")
            for idx, table in enumerate(page_tables, start=1):
                lines.append(f"#### Table {page_no}-{idx}")
                lines.extend(table_to_markdown(table))
                lines.append("")

        page_images = images_by_page.get(page_no, [])
        if page_images:
            lines.append("### Images")
            lines.append("")
            for idx, image_path in enumerate(page_images, start=1):
                rel_path = Path(
                    Path(image_path).relative_to(md_output_path.parent).as_posix()
                )
                lines.append(f"![Page {page_no} - Image {idx}]({rel_path})")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def discover_pdfs(source_dir: Path, recursive: bool) -> List[Path]:
    if recursive:
        return sorted(source_dir.rglob("*.pdf"))
    return sorted(source_dir.glob("*.pdf"))


def convert_single_pdf(
    pdf_path: Path,
    source_root: Path,
    source_output_root: Path,
    config: ConvertConfig,
) -> Tuple[bool, str]:
    relative_pdf = pdf_path.relative_to(source_root)
    md_output_path = (source_output_root / relative_pdf).with_suffix(".md")
    assets_dir = md_output_path.parent / f"{md_output_path.stem}_assets"

    if md_output_path.exists() and not config.overwrite:
        return True, f"跳过(已存在): {md_output_path}"

    if config.dry_run:
        return True, f"[Dry Run] {pdf_path} -> {md_output_path}"

    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        return False, f"打开失败: {pdf_path} ({exc})"

    try:
        text_by_page = extract_text_by_page(doc)
        tables_by_page = extract_tables_by_page(pdf_path) if config.include_tables else {}
        images_by_page = (
            extract_images_by_page(doc, assets_dir) if config.include_images else {}
        )
        markdown_text = build_markdown(
            pdf_path=pdf_path,
            text_by_page=text_by_page,
            tables_by_page=tables_by_page,
            images_by_page=images_by_page,
            md_output_path=md_output_path,
        )
        md_output_path.write_text(markdown_text, encoding="utf-8")
    except Exception as exc:
        return False, f"转换失败: {pdf_path} ({exc})"
    finally:
        doc.close()

    return True, f"完成: {md_output_path}"


def run(config: ConvertConfig) -> int:
    total = 0
    success = 0
    failed = 0

    config.output_root.mkdir(parents=True, exist_ok=True)

    for source_dir in config.source_folders:
        if not source_dir.exists() or not source_dir.is_dir():
            log(f"⚠️ 源目录不存在，跳过: {source_dir}")
            continue

        source_name = source_dir.name
        source_output_root = config.output_root / source_name
        pdf_files = discover_pdfs(source_dir, config.recursive)

        log(f"\n==> 扫描目录: {source_dir}")
        log(f"    发现 PDF: {len(pdf_files)}")

        for pdf in pdf_files:
            total += 1
            ok, message = convert_single_pdf(
                pdf_path=pdf,
                source_root=source_dir,
                source_output_root=source_output_root,
                config=config,
            )
            if ok:
                success += 1
                log(f"✅ {message}")
            else:
                failed += 1
                log(f"❌ {message}")

    log("\n" + "=" * 50)
    log("转换完成")
    log("=" * 50)
    log(f"总任务数: {total}")
    log(f"成功: {success}")
    log(f"失败: {failed}")
    log(f"输出目录: {config.output_root}")

    return 0 if failed == 0 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="批量将 PDF 转为 Markdown，并按来源目录分子文件夹输出。"
    )
    parser.add_argument(
        "--only-sources",
        nargs="+",
        help="仅使用这些源目录（可用别名: 1.1, 1.2）。",
    )
    parser.add_argument(
        "--add-source",
        action="append",
        default=[],
        help="在默认源目录基础上追加一个目录（可重复）。",
    )
    parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_ROOT,
        help=f"输出根目录（默认: {DEFAULT_OUTPUT_ROOT}）",
    )
    parser.add_argument(
        "--non-recursive",
        action="store_true",
        help="仅扫描源目录当前层，不递归子目录。",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="不提取图片。",
    )
    parser.add_argument(
        "--no-tables",
        action="store_true",
        help="不提取表格。",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="覆盖已存在的 md 文件。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印计划，不执行转换。",
    )
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> ConvertConfig:
    if args.only_sources:
        source_values = args.only_sources
    else:
        source_values = list(DEFAULT_SOURCE_FOLDERS) + list(args.add_source)

    source_paths = [resolve_source(value) for value in source_values]

    return ConvertConfig(
        source_folders=source_paths,
        output_root=Path(args.output_root),
        recursive=not args.non_recursive,
        include_images=not args.no_images,
        include_tables=not args.no_tables,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )


def main() -> int:
    args = parse_args()
    config = build_config(args)
    return run(config)


if __name__ == "__main__":
    sys.exit(main())
