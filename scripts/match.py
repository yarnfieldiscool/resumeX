"""
JD Matching Tool

将职位描述 (JD) 与候选人库匹配，按综合评分排序输出。

用法:
    # 从 JD 文本文件匹配
    python match.py --jd jd.txt --db data/resumes.db --top 10

    # 从 JSON 需求文件匹配
    python match.py --jd-json requirements.json --db data/resumes.db

JD JSON 格式:
    {
        "skills": ["Python", "Django"],
        "min_years": 3,
        "education": "Bachelor",
        "city": "Beijing",
        "salary_range": [20000, 35000]
    }
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

from storage import ResumeDB


class JDMatcher:
    """JD-候选人匹配器"""

    # 各维度权重
    WEIGHTS = {
        "skill": 0.40,
        "experience": 0.20,
        "education": 0.15,
        "city": 0.15,
        "salary": 0.10,
    }

    # 学历等级 (用于比较)
    EDUCATION_LEVELS = {
        "high_school": 1, "highschool": 1,
        "associate": 2, "college": 2,
        "bachelor": 3,
        "master": 4,
        "phd": 5, "doctor": 5, "doctorate": 5,
    }

    # 中文学历映射
    EDUCATION_CN = {
        "high_school": 1, "highschool": 1,
        "associate": 2, "college": 2,
        "bachelor": 3,
        "master": 4,
        "phd": 5, "doctor": 5, "doctorate": 5,
    }

    def match(
        self, jd_requirements: dict, candidates: list[dict]
    ) -> list[dict]:
        """
        计算每个候选人与 JD 的匹配度

        Args:
            jd_requirements: JD 需求 dict
            candidates: 候选人详情列表 (从 db.get_candidate 获取)

        Returns:
            按 total_score 降序排列的匹配结果列表
        """
        results = []

        for candidate in candidates:
            scores = self._score_candidate(jd_requirements, candidate)
            total = sum(
                scores.get(dim, 0) * weight
                for dim, weight in self.WEIGHTS.items()
            )
            results.append({
                "candidate_id": candidate["id"],
                "name": candidate.get("name", "?"),
                "total_score": round(total, 3),
                "scores": {k: round(v, 3) for k, v in scores.items()},
                "city": candidate.get("city", "-"),
                "education": candidate.get("education_level", "-"),
            })

        results.sort(key=lambda x: x["total_score"], reverse=True)
        return results

    def _score_candidate(self, jd: dict, candidate: dict) -> dict:
        """计算单个候选人各维度得分 (0~1)"""
        return {
            "skill": self._score_skill(jd, candidate),
            "experience": self._score_experience(jd, candidate),
            "education": self._score_education(jd, candidate),
            "city": self._score_city(jd, candidate),
            "salary": self._score_salary(jd, candidate),
        }

    def _score_skill(self, jd: dict, candidate: dict) -> float:
        """技能匹配分: 命中 JD 要求的技能占比"""
        required_skills = jd.get("skills", [])
        if not required_skills:
            return 1.0  # 无要求 = 满分

        candidate_skills = {
            s["name"].lower() for s in candidate.get("skills", [])
        }

        matched = 0
        for rs in required_skills:
            rs_lower = rs.lower()
            # 精确匹配或包含匹配
            if any(rs_lower in cs or cs in rs_lower for cs in candidate_skills):
                matched += 1

        return matched / len(required_skills)

    def _score_experience(self, jd: dict, candidate: dict) -> float:
        """工作年限分"""
        min_years = jd.get("min_years")
        if not min_years:
            return 1.0

        # 从 experiences 的 duration_months 加总
        total_months = sum(
            e.get("duration_months", 0) or 0
            for e in candidate.get("experiences", [])
        )
        actual_years = total_months / 12.0

        if actual_years >= min_years:
            return 1.0
        elif actual_years == 0:
            return 0.0
        else:
            return actual_years / min_years

    def _score_education(self, jd: dict, candidate: dict) -> float:
        """学历匹配分"""
        required = jd.get("education")
        if not required:
            return 1.0

        actual = candidate.get("education_level", "")
        if not actual:
            return 0.0

        req_level = self._education_level(required)
        act_level = self._education_level(actual)

        if req_level == 0 or act_level == 0:
            # 无法解析学历，降级为字符串匹配
            return 1.0 if required.lower() in actual.lower() else 0.3

        if act_level >= req_level:
            return 1.0
        elif act_level == req_level - 1:
            return 0.6  # 差一级
        else:
            return 0.2

    def _score_city(self, jd: dict, candidate: dict) -> float:
        """城市匹配分"""
        required_city = jd.get("city")
        if not required_city:
            return 1.0

        actual_city = candidate.get("city", "")
        if not actual_city:
            return 0.3  # 未知城市给基础分

        if required_city.lower() in actual_city.lower():
            return 1.0
        if actual_city.lower() in required_city.lower():
            return 1.0
        return 0.0

    def _score_salary(self, jd: dict, candidate: dict) -> float:
        """薪资匹配分"""
        salary_range = jd.get("salary_range")
        if not salary_range or len(salary_range) < 2:
            return 1.0

        jd_min, jd_max = salary_range[0], salary_range[1]

        # 从 job_intentions 获取候选人期望薪资
        intentions = candidate.get("job_intentions", [])
        if not intentions:
            return 0.5  # 无期望 = 中间分

        # 取第一条意向
        intention = intentions[0]
        exp_min = intention.get("salary_min")
        exp_max = intention.get("salary_max")

        if not exp_min and not exp_max:
            return 0.5

        exp_min = exp_min or 0
        exp_max = exp_max or exp_min * 1.5  # 无上限则估算

        # 重叠度计算
        overlap_start = max(jd_min, exp_min)
        overlap_end = min(jd_max, exp_max)

        if overlap_start >= overlap_end:
            # 无重叠: 差距越大分越低
            gap = max(overlap_start - overlap_end, 0)
            mid = (jd_min + jd_max) / 2
            return max(0.0, 1.0 - gap / mid) if mid > 0 else 0.0

        overlap = overlap_end - overlap_start
        total_range = max(jd_max - jd_min, 1)
        return min(1.0, overlap / total_range)

    def _education_level(self, edu_str: str) -> int:
        """将学历字符串转为等级数字"""
        if not edu_str:
            return 0
        key = edu_str.lower().strip().replace(" ", "_")
        level = self.EDUCATION_LEVELS.get(key)
        if level:
            return level
        # 中文匹配
        cn_map = {
            "high_school": ["high_school", "highschool"],
            "college": ["college", "associate"],
            "bachelor": ["bachelor"],
            "master": ["master"],
            "phd": ["phd", "doctor", "doctorate"],
        }
        for k, aliases in cn_map.items():
            if any(a in key for a in aliases):
                return self.EDUCATION_LEVELS.get(k, 0)
        return 0


# ── JD Text Parser ────────────────────────────────────────────────

def parse_jd_text(text: str) -> dict:
    """
    从纯文本 JD 中提取结构化需求

    使用简单规则/正则提取，不依赖 AI。

    Args:
        text: JD 原始文本

    Returns:
        结构化需求字典
    """
    requirements = {}
    text_lower = text.lower()

    # 提取技能关键词 (常见技术栈)
    skill_patterns = [
        r'\b(Python|Java|JavaScript|TypeScript|Go|Golang|Rust|C\+\+|C#|Ruby|PHP|Swift|Kotlin)\b',
        r'\b(React|Vue|Angular|Django|Flask|FastAPI|Spring|Node\.js|Express)\b',
        r'\b(MySQL|PostgreSQL|MongoDB|Redis|Elasticsearch|Kafka)\b',
        r'\b(Docker|Kubernetes|K8s|AWS|Azure|GCP|Linux)\b',
        r'\b(Git|CI/CD|Jenkins|GitHub Actions|TensorFlow|PyTorch)\b',
        r'\b(SQL|NoSQL|GraphQL|REST|gRPC|Microservices)\b',
    ]

    skills = set()
    for pattern in skill_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        skills.update(m.strip() for m in matches if m.strip())

    if skills:
        requirements["skills"] = sorted(skills)

    # 提取年限要求
    year_patterns = [
        r'(\d+)\s*(?:years?|yr)',
        r'(\d+)\s*[\+]?\s*(?:years?|yr)',
    ]
    for pattern in year_patterns:
        m = re.search(pattern, text_lower)
        if m:
            requirements["min_years"] = int(m.group(1))
            break

    # 提取学历要求
    edu_patterns = {
        "PhD": r'\b(?:phd|doctor|doctorate)\b',
        "Master": r'\b(?:master|mba)\b',
        "Bachelor": r'\b(?:bachelor|undergraduate|bs|ba)\b',
        "Associate": r'\b(?:associate|college|diploma)\b',
    }
    for level, pattern in edu_patterns.items():
        if re.search(pattern, text_lower):
            requirements["education"] = level
            break

    # 提取城市 (简单匹配常见城市)
    cities = [
        "Beijing", "Shanghai", "Shenzhen", "Guangzhou", "Hangzhou",
        "Chengdu", "Nanjing", "Wuhan", "Xi'an", "Suzhou",
        "Remote",
    ]
    for city in cities:
        if city.lower() in text_lower:
            requirements["city"] = city
            break

    # 提取薪资范围
    salary_patterns = [
        r'(\d+)[kK]\s*[-~]\s*(\d+)[kK]',
        r'(\d{4,})\s*[-~]\s*(\d{4,})',
    ]
    for pattern in salary_patterns:
        m = re.search(pattern, text)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            # 如果是 K 格式 (< 100 说明是千为单位)
            if lo < 100:
                lo *= 1000
                hi *= 1000
            requirements["salary_range"] = [lo, hi]
            break

    return requirements


# ── CLI ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="JD-Candidate Matching Tool")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--jd", help="JD text file path")
    group.add_argument("--jd-json", help="JD requirements JSON file path")

    parser.add_argument(
        "--db",
        default=ResumeDB.DEFAULT_DB_PATH,
        help=f"database path (default: {ResumeDB.DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--top", type=int, default=10, help="number of top matches to show (default: 10)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="show detailed scores"
    )

    args = parser.parse_args()

    # 解析 JD 需求
    if args.jd:
        jd_path = Path(args.jd)
        if not jd_path.exists():
            print(f"Error: file not found: {args.jd}", file=sys.stderr)
            sys.exit(1)
        with open(jd_path, "r", encoding="utf-8") as f:
            jd_text = f.read()
        requirements = parse_jd_text(jd_text)
        print("Parsed JD requirements:")
        print(json.dumps(requirements, indent=2, ensure_ascii=False))
        print()
    else:
        jd_json_path = Path(args.jd_json)
        if not jd_json_path.exists():
            print(f"Error: file not found: {args.jd_json}", file=sys.stderr)
            sys.exit(1)
        with open(jd_json_path, "r", encoding="utf-8") as f:
            requirements = json.load(f)

    if not requirements:
        print("Warning: no requirements extracted from JD.", file=sys.stderr)

    # 从数据库加载所有候选人详情
    db = ResumeDB(args.db)
    try:
        candidate_list = db.list_candidates(limit=10000)
        if not candidate_list:
            print("No candidates in database.", file=sys.stderr)
            sys.exit(1)

        # 获取每个候选人的完整详情
        candidates = []
        for c in candidate_list:
            detail = db.get_candidate(c["id"])
            if detail:
                candidates.append(detail)

        print(f"Matching {len(candidates)} candidates...\n")

        # 执行匹配
        matcher = JDMatcher()
        results = matcher.match(requirements, candidates)

        # 输出结果
        top_n = results[: args.top]
        print(f"Top {len(top_n)} matches:")
        print(f"{'Rank':>4}  {'ID':>4}  {'Name':<16} {'Score':>6}  "
              f"{'City':<10} {'Education':<10}")
        print("-" * 65)

        for i, r in enumerate(top_n, 1):
            name = r["name"]
            if len(name) > 16:
                name = name[:14] + ".."
            print(
                f"{i:>4}  {r['candidate_id']:>4}  {name:<16} "
                f"{r['total_score']:>6.1%}  "
                f"{_s(r.get('city'), 10):<10} "
                f"{_s(r.get('education'), 10):<10}"
            )

            if args.verbose:
                scores = r["scores"]
                parts = [f"{k}={v:.0%}" for k, v in scores.items()]
                print(f"        [{', '.join(parts)}]")

    finally:
        db.close()


def _s(value, max_len: int = 0) -> str:
    """Safe string with truncation"""
    s = str(value) if value else "-"
    if max_len and len(s) > max_len:
        s = s[: max_len - 2] + ".."
    return s


if __name__ == "__main__":
    main()
