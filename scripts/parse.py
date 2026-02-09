"""
Document Parse CLI

统一文档解析入口，将 PDF/DOCX 简历转换为 Markdown 纯文本。

用法：
    # 单文件模式
    python parse.py --input resume.pdf --output resume.md

    # 批量模式
    python parse.py --input-dir ./resumes/ --output-dir ./parsed/

    # 指定输出到控制台
    python parse.py --input resume.pdf
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

# 确保 parsers 包可导入
sys.path.insert(0, str(Path(__file__).parent))

from parsers.pdf_parser import PdfParser
from parsers.docx_parser import DocxParser


# 文件扩展名 -> 解析器映射
PARSER_MAP = {
    ".pdf": PdfParser,
    ".docx": DocxParser,
    ".doc": DocxParser,  # python-docx 对 .doc 支持有限，但可以尝试
}

SUPPORTED_EXTENSIONS = set(PARSER_MAP.keys())


def parse_file(input_path: str, output_path: Optional[str] = None) -> str:
    """解析单个文档文件。

    Args:
        input_path: 输入文件路径 (PDF/DOCX)。
        output_path: 输出文件路径。如果为 None，不写入文件。

    Returns:
        解析后的 Markdown 文本。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 不支持的文件格式。
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    ext = path.suffix.lower()
    if ext not in PARSER_MAP:
        raise ValueError(
            f"Unsupported file format: {ext}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    parser_cls = PARSER_MAP[ext]
    parser = parser_cls()
    markdown_text = parser.parse(str(path))

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown_text, encoding="utf-8")

    return markdown_text


def parse_directory(input_dir: str, output_dir: str) -> dict:
    """批量解析目录下的所有文档文件。

    Args:
        input_dir: 输入目录路径。
        output_dir: 输出目录路径。

    Returns:
        dict: {文件名: 状态} 的映射。状态为 "ok" 或错误信息。
    """
    in_path = Path(input_dir)
    out_path = Path(output_dir)

    if not in_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    if not in_path.is_dir():
        raise ValueError(f"Not a directory: {input_dir}")

    out_path.mkdir(parents=True, exist_ok=True)

    results = {}
    files = sorted(
        f for f in in_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not files:
        print(f"No supported files found in {input_dir}")
        print(f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        return results

    for file in files:
        output_file = out_path / (file.stem + ".md")
        try:
            parse_file(str(file), str(output_file))
            results[file.name] = "ok"
            print(f"  [OK] {file.name} -> {output_file.name}")
        except Exception as e:
            results[file.name] = str(e)
            print(f"  [FAIL] {file.name}: {e}")

    return results


def main():
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="Parse PDF/DOCX resumes to Markdown text.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python parse.py --input resume.pdf --output resume.md\n"
            "  python parse.py --input resume.docx\n"
            "  python parse.py --input-dir ./resumes/ --output-dir ./parsed/\n"
        ),
    )

    # 单文件模式
    parser.add_argument(
        "--input", "-i",
        help="Input file path (PDF/DOCX).",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (.md). If omitted, prints to stdout.",
    )

    # 批量模式
    parser.add_argument(
        "--input-dir",
        help="Input directory for batch processing.",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for batch processing.",
    )

    args = parser.parse_args()

    # 参数验证
    if args.input and args.input_dir:
        parser.error("Cannot use --input and --input-dir together.")
    if not args.input and not args.input_dir:
        parser.error("Either --input or --input-dir is required.")
    if args.input_dir and not args.output_dir:
        parser.error("--output-dir is required when using --input-dir.")

    # 执行
    if args.input:
        # 单文件模式
        try:
            result = parse_file(args.input, args.output)
            if not args.output:
                # 输出到 stdout
                sys.stdout.buffer.write(result.encode("utf-8"))
                sys.stdout.buffer.write(b"\n")
            else:
                print(f"Parsed: {args.input} -> {args.output}")
        except (FileNotFoundError, ValueError, ImportError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.input_dir:
        # 批量模式
        try:
            print(f"Scanning: {args.input_dir}")
            results = parse_directory(args.input_dir, args.output_dir)
            total = len(results)
            ok = sum(1 for v in results.values() if v == "ok")
            fail = total - ok
            print(f"\nDone: {ok}/{total} succeeded, {fail} failed.")
            if fail > 0:
                sys.exit(1)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
