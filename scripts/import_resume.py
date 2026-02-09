"""
Resume Import Tool

从 pipeline JSON 输出导入简历数据到 SQLite 数据库。

用法:
    # 导入单个文件
    python import_resume.py --input result.json --db data/resumes.db

    # 批量导入目录
    python import_resume.py --input-dir ./results/ --db data/resumes.db

    # 导入时显示详情
    python import_resume.py --input result.json --verbose
"""

import argparse
import json
import sys
from pathlib import Path

from storage import ResumeDB


def import_single(db: ResumeDB, input_path: Path, verbose: bool = False) -> int:
    """
    导入单个 pipeline JSON 文件

    Args:
        db: 数据库实例
        input_path: JSON 文件路径
        verbose: 是否显示详情

    Returns:
        candidate_id, 失败返回 -1
    """
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"  [FAIL] {input_path.name}: JSON parse error - {e}", file=sys.stderr)
        return -1

    # 兼容两种格式: {"extractions": [...]} 或纯数组 [...]
    if isinstance(data, dict) and "extractions" in data:
        extractions = data["extractions"]
    elif isinstance(data, list):
        extractions = data
    else:
        print(
            f"  [FAIL] {input_path.name}: expected array or object with 'extractions'",
            file=sys.stderr,
        )
        return -1

    if not extractions:
        print(f"  [SKIP] {input_path.name}: empty extractions", file=sys.stderr)
        return -1

    # 检查是否有 candidate 类型
    has_candidate = any(e.get("type") == "candidate" for e in extractions)
    if not has_candidate:
        print(
            f"  [SKIP] {input_path.name}: no 'candidate' type found",
            file=sys.stderr,
        )
        return -1

    try:
        candidate_id = db.insert_from_extractions(extractions, input_path.name)
    except Exception as e:
        print(f"  [FAIL] {input_path.name}: insert error - {e}", file=sys.stderr)
        return -1

    if verbose:
        _print_import_detail(extractions, candidate_id, input_path.name)
    else:
        # 提取候选人姓名
        candidate_ext = next(
            (e for e in extractions if e.get("type") == "candidate"), {}
        )
        name = candidate_ext.get("attributes", {}).get(
            "name", candidate_ext.get("text", "?")
        )
        print(f"  [OK] {input_path.name} -> ID {candidate_id} ({name})")

    return candidate_id


def _print_import_detail(
    extractions: list[dict], candidate_id: int, filename: str
):
    """打印导入详情"""
    # 按类型统计
    by_type = {}
    for ext in extractions:
        t = ext.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    print(f"  [OK] {filename} -> ID {candidate_id}")
    for t, count in sorted(by_type.items()):
        print(f"       {t}: {count}")


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Import pipeline JSON into resume database"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", help="single JSON file to import")
    group.add_argument("--input-dir", help="directory of JSON files to batch import")

    parser.add_argument(
        "--db",
        default=ResumeDB.DEFAULT_DB_PATH,
        help=f"SQLite database path (default: {ResumeDB.DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="show import details"
    )

    args = parser.parse_args()

    db = ResumeDB(args.db)

    try:
        if args.input:
            # 单文件导入
            input_path = Path(args.input)
            if not input_path.exists():
                print(f"Error: file not found: {args.input}", file=sys.stderr)
                sys.exit(1)

            print(f"Importing from {input_path}...")
            cid = import_single(db, input_path, args.verbose)
            if cid > 0:
                print(f"\nDone. Candidate ID: {cid}")
            else:
                print("\nImport failed.", file=sys.stderr)
                sys.exit(1)

        else:
            # 批量导入
            input_dir = Path(args.input_dir)
            if not input_dir.is_dir():
                print(f"Error: directory not found: {args.input_dir}", file=sys.stderr)
                sys.exit(1)

            json_files = sorted(input_dir.glob("*.json"))
            if not json_files:
                print(f"No JSON files found in {input_dir}", file=sys.stderr)
                sys.exit(1)

            print(f"Batch importing {len(json_files)} files from {input_dir}...")

            success = 0
            failed = 0
            for jf in json_files:
                cid = import_single(db, jf, args.verbose)
                if cid > 0:
                    success += 1
                else:
                    failed += 1

            print(f"\nDone. Success: {success}, Failed: {failed}")
            if failed > 0:
                sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
