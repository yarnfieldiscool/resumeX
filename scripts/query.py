"""
Resume Query Tool

简历查询命令行工具，支持搜索、统计、详情查看。

用法:
    python query.py search "Python 3 Beijing"
    python query.py search --skill Python --min-years 3 --city Beijing
    python query.py stats
    python query.py stats --by skill
    python query.py stats --by education
    python query.py stats --by city
    python query.py detail 1
    python query.py list
    python query.py list --limit 20 --offset 10
"""

import argparse
import json
import sys

from storage import ResumeDB


def cmd_search(db: ResumeDB, args):
    """search subcommand"""
    results = db.search(
        query=args.query,
        skill=args.skill,
        city=args.city,
        min_years=args.min_years,
        education=args.education,
    )

    if not results:
        print("No candidates found.")
        return

    print(f"Found {len(results)} candidate(s):\n")
    for r in results:
        _print_candidate_summary(r)


def cmd_stats(db: ResumeDB, args):
    """stats subcommand"""
    result = db.stats(group_by=args.by)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_detail(db: ResumeDB, args):
    """detail subcommand"""
    candidate = db.get_candidate(args.id)
    if not candidate:
        print(f"Candidate ID {args.id} not found.", file=sys.stderr)
        sys.exit(1)

    _print_candidate_detail(candidate)


def cmd_list(db: ResumeDB, args):
    """list subcommand"""
    results = db.list_candidates(limit=args.limit, offset=args.offset)
    if not results:
        print("No candidates in database.")
        return

    print(f"Candidates ({len(results)} shown):\n")
    print(f"{'ID':>4}  {'Name':<16} {'City':<10} {'Education':<10} "
          f"{'Exp':>3} {'Edu':>3} {'Skill':>5}  Source")
    print("-" * 80)
    for r in results:
        print(
            f"{r['id']:>4}  {_s(r.get('name'), 16):<16} "
            f"{_s(r.get('city'), 10):<10} "
            f"{_s(r.get('education_level'), 10):<10} "
            f"{r.get('exp_count', 0):>3} "
            f"{r.get('edu_count', 0):>3} "
            f"{r.get('skill_count', 0):>5}  "
            f"{_s(r.get('source_file'), 20)}"
        )


# ── Output Helpers ────────────────────────────────────────────────

def _s(value, max_len: int = 0) -> str:
    """Safe string conversion with optional truncation"""
    s = str(value) if value else "-"
    if max_len and len(s) > max_len:
        s = s[: max_len - 2] + ".."
    return s


def _print_candidate_summary(r: dict):
    """Print one-line candidate summary"""
    cid = r.get("id", "?")
    name = r.get("name", "?")
    city = r.get("city", "-")
    edu = r.get("education_level", "-")
    phone = r.get("phone", "-")
    source = r.get("source_file", "-")
    print(f"  [{cid}] {name} | {city} | {edu} | {phone} | src: {source}")


def _print_candidate_detail(c: dict):
    """Print full candidate detail"""
    print("=" * 60)
    print(f"  ID: {c['id']}  Name: {c.get('name', '?')}")
    print(f"  Gender: {c.get('gender', '-')}  Age: {c.get('age', '-')}")
    print(f"  Phone: {c.get('phone', '-')}  Email: {c.get('email', '-')}")
    print(f"  City: {c.get('city', '-')}  Education: {c.get('education_level', '-')}")
    print(f"  Source: {c.get('source_file', '-')}")
    print(f"  Created: {c.get('created_at', '-')}")

    # Experiences
    exps = c.get("experiences", [])
    if exps:
        print(f"\n  -- Experiences ({len(exps)}) --")
        for e in exps:
            duration = f" ({e['duration_months']}mo)" if e.get("duration_months") else ""
            print(
                f"     {e.get('company', '?')} | {e.get('title', '?')} | "
                f"{e.get('start_date', '?')} ~ {e.get('end_date', '?')}{duration}"
            )
            if e.get("description"):
                # Truncate long descriptions
                desc = e["description"]
                if len(desc) > 80:
                    desc = desc[:77] + "..."
                print(f"       {desc}")

    # Education
    edus = c.get("educations", [])
    if edus:
        print(f"\n  -- Education ({len(edus)}) --")
        for e in edus:
            gpa = f" GPA:{e['gpa']}" if e.get("gpa") else ""
            print(
                f"     {e.get('school', '?')} | {e.get('major', '?')} | "
                f"{e.get('degree', '?')}{gpa}"
            )

    # Skills
    skills = c.get("skills", [])
    if skills:
        print(f"\n  -- Skills ({len(skills)}) --")
        skill_strs = []
        for s in skills:
            parts = [s["name"]]
            if s.get("level"):
                parts.append(f"[{s['level']}]")
            if s.get("years"):
                parts.append(f"{s['years']}yr")
            skill_strs.append(" ".join(parts))
        # Print in rows of 4
        for i in range(0, len(skill_strs), 4):
            chunk = skill_strs[i : i + 4]
            print(f"     {' | '.join(chunk)}")

    # Certifications
    certs = c.get("certifications", [])
    if certs:
        print(f"\n  -- Certifications ({len(certs)}) --")
        for cert in certs:
            print(
                f"     {cert.get('name', '?')} | {cert.get('issuer', '?')} | "
                f"{cert.get('date', '?')}"
            )

    # Job intentions
    intentions = c.get("job_intentions", [])
    if intentions:
        print(f"\n  -- Job Intentions ({len(intentions)}) --")
        for ji in intentions:
            salary = ""
            if ji.get("salary_min") or ji.get("salary_max"):
                lo = ji.get("salary_min", "?")
                hi = ji.get("salary_max", "?")
                salary = f" | {lo}-{hi}"
            print(
                f"     {ji.get('position', '?')} | {ji.get('city', '?')}{salary}"
            )

    # Self evaluations
    evals = c.get("self_evaluations", [])
    if evals:
        print(f"\n  -- Self Evaluation --")
        for ev in evals:
            text = ev.get("text", "")
            if len(text) > 200:
                text = text[:197] + "..."
            print(f"     {text}")
            if ev.get("traits"):
                traits = ev["traits"]
                if isinstance(traits, str):
                    try:
                        traits = json.loads(traits)
                    except json.JSONDecodeError:
                        traits = [traits]
                if isinstance(traits, list):
                    print(f"     Traits: {', '.join(str(t) for t in traits)}")

    print("=" * 60)


# ── CLI ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Resume Query Tool")
    parser.add_argument(
        "--db",
        default=ResumeDB.DEFAULT_DB_PATH,
        help=f"database path (default: {ResumeDB.DEFAULT_DB_PATH})",
    )
    subparsers = parser.add_subparsers(dest="command", help="available commands")

    # search
    p_search = subparsers.add_parser("search", help="search candidates")
    p_search.add_argument("query", nargs="?", help="natural language query")
    p_search.add_argument("--skill", help="filter by skill name")
    p_search.add_argument("--city", help="filter by city")
    p_search.add_argument("--min-years", type=int, help="minimum years of experience")
    p_search.add_argument("--education", help="filter by education level")

    # stats
    p_stats = subparsers.add_parser("stats", help="show statistics")
    p_stats.add_argument(
        "--by",
        choices=["skill", "education", "city"],
        help="group statistics by dimension",
    )

    # detail
    p_detail = subparsers.add_parser("detail", help="show candidate details")
    p_detail.add_argument("id", type=int, help="candidate ID")

    # list
    p_list = subparsers.add_parser("list", help="list all candidates")
    p_list.add_argument("--limit", type=int, default=50, help="max results")
    p_list.add_argument("--offset", type=int, default=0, help="offset")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    db = ResumeDB(args.db)

    try:
        if args.command == "search":
            if not any([args.query, args.skill, args.city, args.min_years, args.education]):
                print("Error: provide at least one search criterion.", file=sys.stderr)
                sys.exit(1)
            cmd_search(db, args)
        elif args.command == "stats":
            cmd_stats(db, args)
        elif args.command == "detail":
            cmd_detail(db, args)
        elif args.command == "list":
            cmd_list(db, args)
    finally:
        db.close()


if __name__ == "__main__":
    main()
