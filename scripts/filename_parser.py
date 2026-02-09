"""
Filename Parser

解析招聘平台简历文件名中的元数据，生成 context_hints 供 Claude 提取时参考。

支持格式:
  【岗位_城市 薪资K】姓名 年限
  【【2026秋招】游戏算法工程师_成都 15-16K】姚智强 26年应届生
  【高级Web后端开发工程师_成都 18-25K】唐双 6年

用法:
  python filename_parser.py "【高级Web后端开发工程师_成都 18-25K】唐双 6年.pdf"
"""

import re
import json
import sys
from pathlib import Path


def parse_filename(filename: str) -> dict:
    """从招聘平台文件名中提取元数据。

    Args:
        filename: 文件名 (含或不含路径/扩展名)

    Returns:
        dict: 提取的元数据 (position, city, salary_range, candidate_name, years, tags)
              空 dict 表示无法解析
    """
    # 取纯文件名 (去除路径和扩展名)
    stem = Path(filename).stem

    result = {}

    # 提取最外层方括号内容: 【...】(贪婪匹配，找最后一个 】)
    bracket_match = re.search(r"[【\[](.+)[】\]]([^【\[]*)", stem)
    if not bracket_match:
        return result

    inner = bracket_match.group(1).strip()
    outer = bracket_match.group(2).strip()

    # 处理嵌套方括号: 【2026秋招】游戏算法工程师_成都 15-16K
    nested = re.match(r"[【\[]([^】\]]+)[】\]]\s*(.*)", inner)
    if nested:
        tag = nested.group(1).strip()
        inner = nested.group(2).strip()
        result["tags"] = [tag]

    # 从 inner 解析: 岗位_城市 薪资K
    # 尝试: "高级Web后端开发工程师_成都 18-25K"
    parts_match = re.match(r"(.+?)_(.+?)\s+(\d+(?:-\d+)?K)", inner)
    if parts_match:
        result["position"] = parts_match.group(1).strip()
        result["city"] = parts_match.group(2).strip()
        salary_str = parts_match.group(3)
        result["salary_text"] = salary_str
        # 解析薪资范围
        sal_match = re.match(r"(\d+)-(\d+)K", salary_str)
        if sal_match:
            result["salary_min"] = int(sal_match.group(1)) * 1000
            result["salary_max"] = int(sal_match.group(2)) * 1000
        else:
            sal_single = re.match(r"(\d+)K", salary_str)
            if sal_single:
                result["salary_min"] = int(sal_single.group(1)) * 1000
    else:
        # 降级: 仅岗位_城市
        parts_simple = re.match(r"(.+?)_(.+)", inner)
        if parts_simple:
            result["position"] = parts_simple.group(1).strip()
            result["city"] = parts_simple.group(2).strip()

    # 从 outer 解析: 姓名 年限
    if outer:
        # "唐双 6年" 或 "姚智强 26年应届生"
        name_match = re.match(r"(\S+)\s*(.*)", outer)
        if name_match:
            result["candidate_name"] = name_match.group(1).strip()
            years_part = name_match.group(2).strip()
            if years_part:
                years_num = re.match(r"(\d+)年", years_part)
                if years_num:
                    result["years_text"] = years_part
                    yr = int(years_num.group(1))
                    # 区分工作年限 vs 应届生年份
                    if "应届" in years_part:
                        # "26年应届生" → 2026, "25年应届生" → 2025
                        result["graduate_year"] = 2000 + yr if yr < 100 else yr
                    else:
                        result["years_of_experience"] = yr

    return result


def format_context_hints(metadata: dict) -> str:
    """将元数据格式化为 Claude 提取时的 context_hints 文本。

    Args:
        metadata: parse_filename() 返回的元数据

    Returns:
        str: 人类可读的提示文本
    """
    if not metadata:
        return ""

    hints = []
    if "candidate_name" in metadata:
        hints.append(f"Candidate name: {metadata['candidate_name']}")
    if "position" in metadata:
        hints.append(f"Applied position: {metadata['position']}")
    if "city" in metadata:
        hints.append(f"Target city: {metadata['city']}")
    if "salary_text" in metadata:
        hints.append(f"Salary range: {metadata['salary_text']}")
    if "years_of_experience" in metadata:
        hints.append(f"Years of experience: {metadata['years_of_experience']}")
    if "graduate_year" in metadata:
        hints.append(f"Graduate year: {metadata['graduate_year']} (fresh graduate)")
    if "tags" in metadata:
        hints.append(f"Tags: {', '.join(metadata['tags'])}")

    return "\n".join(hints)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python filename_parser.py <filename>", file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]
    result = parse_filename(filename)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    hints = format_context_hints(result)
    if hints:
        print(f"\n--- context_hints ---\n{hints}")


if __name__ == "__main__":
    main()
