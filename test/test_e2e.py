"""
End-to-End Test Suite

Tests the complete flow: raw text -> mock AI extraction -> pipeline -> SQLite import -> query -> JD match.

Since there is no actual LLM call, the AI extraction step uses pre-built JSON fixtures
that simulate Claude's output for each sample resume.

Usage:
    pytest test/test_e2e.py -v
    python test/test_e2e.py          # standalone mode (no pytest required)
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# ── Path setup ───────────────────────────────────────────────────
_TEST_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _TEST_DIR.parent
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from pipeline import ExtractionPipeline
from storage import ResumeDB
from match import JDMatcher, parse_jd_text

# ── Sample paths ─────────────────────────────────────────────────
SAMPLE_DIR = _TEST_DIR / "sample_resumes"
EXTRACTIONS_DIR = _TEST_DIR / "sample_extractions"
JD_PATH = _TEST_DIR / "sample_jd.txt"


# ══════════════════════════════════════════════════════════════════
# Mock Extraction Fixtures
# ══════════════════════════════════════════════════════════════════
# text fields are exact substrings from the Chinese .md files
# so that Source Grounding can locate them.


def _load_tech_senior_raw() -> list:
    """Load pre-built tech_senior_raw.json from sample_extractions/."""
    path = EXTRACTIONS_DIR / "tech_senior_raw.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _mock_extractions_tech_senior() -> list:
    """Mock extractions for tech_senior.md (Chinese)."""
    return _load_tech_senior_raw()


def _mock_extractions_manager() -> list:
    """Mock extractions for manager.md (Chinese)."""
    return [
        {
            "type": "candidate",
            "text": "陈芳\n女 | 35岁 | 上海\n手机: 139-0021-3000 | 邮箱: chenfang@bizmail.com",
            "summary_cn": "工程经理陈芳，女，35岁，上海",
            "attributes": {
                "name": "陈芳",
                "gender": "女",
                "age": 35,
                "phone": "139-0021-3000",
                "email": "chenfang@bizmail.com",
                "city": "上海",
                "education_level": "Master",
            },
        },
        {
            "type": "experience",
            "text": "2022.01 - 至今  云创科技有限公司  工程经理",
            "summary_cn": "云创科技工程经理 2022至今",
            "attributes": {
                "company": "云创科技有限公司",
                "title": "工程经理",
                "start_date": "2022-01",
                "end_date": "至今",
                "duration_months": 24,
                "description": "管理25人团队，SaaS平台从0到1，CI/CD文化建设",
            },
        },
        {
            "type": "experience",
            "text": "2019.06 - 2021.12  巨软科技  团队负责人",
            "summary_cn": "巨软科技团队负责人 2019-2021",
            "attributes": {
                "company": "巨软科技",
                "title": "团队负责人",
                "start_date": "2019-06",
                "end_date": "2021-12",
                "duration_months": 30,
                "description": "支付平台，12支付渠道，99.99%可用性",
            },
        },
        {
            "type": "experience",
            "text": "2016.03 - 2019.05  创业孵化器  全栈开发工程师",
            "summary_cn": "创业孵化器全栈开发 2016-2019",
            "attributes": {
                "company": "创业孵化器",
                "title": "全栈开发工程师",
                "start_date": "2016-03",
                "end_date": "2019-05",
                "duration_months": 38,
                "description": "React和Node.js全栈开发，实时数据分析仪表盘",
            },
        },
        {
            "type": "education",
            "text": "2013.09 - 2016.03  复旦大学  软件工程  硕士",
            "summary_cn": "复旦大学软件工程硕士",
            "attributes": {
                "school": "复旦大学",
                "major": "软件工程",
                "degree": "硕士",
                "start_date": "2013-09",
                "end_date": "2016-03",
            },
        },
        {
            "type": "education",
            "text": "2009.09 - 2013.06  浙江大学  信息工程  本科  GPA: 3.6/4.0",
            "summary_cn": "浙江大学信息工程本科",
            "attributes": {
                "school": "浙江大学",
                "major": "信息工程",
                "degree": "本科",
                "start_date": "2009-09",
                "end_date": "2013-06",
                "gpa": "3.6/4.0",
            },
        },
        {
            "type": "skill",
            "text": "Python (熟练, 8年)",
            "attributes": {"name": "Python", "category": "语言", "level": "熟练", "years": 8},
        },
        {
            "type": "skill",
            "text": "Java (熟练, 7年)",
            "attributes": {"name": "Java", "category": "语言", "level": "熟练", "years": 7},
        },
        {
            "type": "skill",
            "text": "项目管理 (精通, 6年)",
            "attributes": {"name": "项目管理", "category": "软技能", "level": "精通", "years": 6},
        },
        {
            "type": "skill",
            "text": "AWS/Azure (熟练, 5年)",
            "attributes": {"name": "AWS/Azure", "category": "工具", "level": "熟练", "years": 5},
        },
        {
            "type": "certification",
            "text": "PMP 项目管理专业人士 (PMI, 2020.06)",
            "attributes": {"name": "PMP", "issuer": "PMI", "date": "2020-06"},
        },
        {
            "type": "job_intention",
            "text": "求职意向: 技术总监 | 期望薪资: 50K-70K | 到岗时间: 需商议",
            "attributes": {
                "position": "技术总监",
                "salary_min": 50000,
                "salary_max": 70000,
                "city": "上海",
                "entry_date": "需商议",
            },
        },
        {
            "type": "self_evaluation",
            "text": "10年从个人贡献者到工程经理的渐进式成长经验。",
            "attributes": {
                "text": "10年从个人贡献者到工程经理的渐进式成长经验。具备卓越的领导力和成功组建、扩展工程团队的实战记录。",
                "traits": ["领导力", "系统架构", "敏捷管理", "跨职能沟通"],
            },
        },
    ]


def _mock_extractions_fresh_graduate() -> list:
    """Mock extractions for fresh_graduate.md (Chinese)."""
    return [
        {
            "type": "candidate",
            "text": "王小明\n男 | 23岁 | 成都\n手机: 177-0028-1234 | 邮箱: wxm_dev@campus.com",
            "summary_cn": "应届生王小明，男，23岁，成都",
            "attributes": {
                "name": "王小明",
                "gender": "男",
                "age": 23,
                "phone": "177-0028-1234",
                "email": "wxm_dev@campus.com",
                "city": "成都",
                "education_level": "Bachelor",
            },
        },
        {
            "type": "experience",
            "text": "2023.07 - 2023.12  TechVibe公司  后端开发实习生",
            "summary_cn": "TechVibe后端实习 2023",
            "attributes": {
                "company": "TechVibe公司",
                "title": "后端开发实习生",
                "start_date": "2023-07",
                "end_date": "2023-12",
                "duration_months": 6,
                "description": "Spring Boot API开发，单元测试",
            },
        },
        {
            "type": "education",
            "text": "2020.09 - 2024.06  电子科技大学  软件工程  本科  GPA: 3.5/4.0",
            "summary_cn": "电子科技大学软件工程本科",
            "attributes": {
                "school": "电子科技大学",
                "major": "软件工程",
                "degree": "本科",
                "start_date": "2020-09",
                "end_date": "2024-06",
                "gpa": "3.5/4.0",
            },
        },
        {
            "type": "skill",
            "text": "Java (掌握, 2年)",
            "attributes": {"name": "Java", "category": "语言", "level": "掌握", "years": 2},
        },
        {
            "type": "skill",
            "text": "Python (掌握, 2年)",
            "attributes": {"name": "Python", "category": "语言", "level": "掌握", "years": 2},
        },
        {
            "type": "skill",
            "text": "MySQL (掌握, 2年)",
            "attributes": {"name": "MySQL", "category": "数据库", "level": "掌握", "years": 2},
        },
        {
            "type": "skill",
            "text": "Docker (了解, 1年)",
            "attributes": {"name": "Docker", "category": "工具", "level": "了解", "years": 1},
        },
        {
            "type": "job_intention",
            "text": "求职意向: 初级后端开发工程师 | 期望薪资: 12K-18K | 到岗时间: 随时到岗",
            "attributes": {
                "position": "初级后端开发工程师",
                "salary_min": 12000,
                "salary_max": 18000,
                "city": "成都/深圳",
                "entry_date": "随时到岗",
            },
        },
        {
            "type": "self_evaluation",
            "text": "计算机科学基础扎实的应届毕业生，通过实习和开源贡献积累了实践经验。",
            "attributes": {
                "text": "计算机科学基础扎实的应届毕业生，通过实习和开源贡献积累了实践经验。学习能力强，热爱后端开发。",
                "traits": ["学习能力强", "问题解决", "后端开发"],
            },
        },
    ]


# ══════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════

def _read_sample(filename: str) -> str:
    """Read a sample resume markdown file."""
    path = SAMPLE_DIR / filename
    return path.read_text(encoding="utf-8")


def _create_temp_db() -> str:
    """Create a temporary database file path."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_resume_")
    os.close(fd)
    return path


def _run_pipeline(filename: str, mock_fn) -> dict:
    """Run pipeline on a sample resume with mock extractions."""
    source_text = _read_sample(filename)
    extractions = mock_fn()
    pipeline = ExtractionPipeline(source_text=source_text, source_file=filename)
    return pipeline.process(extractions)


def _setup_full_db() -> tuple:
    """Create temp DB, import all 3 resumes. Returns (db_path, candidate_ids dict)."""
    db_path = _create_temp_db()
    test_cases = [
        ("tech_senior.md", _mock_extractions_tech_senior),
        ("manager.md", _mock_extractions_manager),
        ("fresh_graduate.md", _mock_extractions_fresh_graduate),
    ]
    db = ResumeDB(db_path)
    candidate_ids = {}
    for filename, mock_fn in test_cases:
        result = _run_pipeline(filename, mock_fn)
        cid = db.insert_from_extractions(result["extractions"], filename)
        candidate_ids[filename] = cid
    db.close()
    return db_path, candidate_ids


# ══════════════════════════════════════════════════════════════════
# Test: Pipeline Processing
# ══════════════════════════════════════════════════════════════════

class TestPipeline:
    """Test pipeline processes mock extractions correctly."""

    def test_tech_senior_pipeline(self):
        """Pipeline should process tech_senior extractions."""
        result = _run_pipeline("tech_senior.md", _mock_extractions_tech_senior)

        assert "extractions" in result
        assert "stats" in result
        assert len(result["extractions"]) > 0
        assert result["stats"]["total_extractions"] > 0
        assert result["stats"]["avg_confidence"] > 0

    def test_manager_pipeline(self):
        """Pipeline should process manager extractions."""
        result = _run_pipeline("manager.md", _mock_extractions_manager)
        assert len(result["extractions"]) > 0
        assert result["stats"]["total_extractions"] > 0

    def test_fresh_graduate_pipeline(self):
        """Pipeline should process fresh_graduate extractions."""
        result = _run_pipeline("fresh_graduate.md", _mock_extractions_fresh_graduate)
        assert len(result["extractions"]) > 0
        assert result["stats"]["total_extractions"] >= 5

    def test_pipeline_output_has_confidence(self):
        """Every extraction should have a confidence score after pipeline."""
        result = _run_pipeline("tech_senior.md", _mock_extractions_tech_senior)
        for ext in result["extractions"]:
            assert "confidence" in ext, f"Missing confidence in: {ext.get('type')}"
            assert isinstance(ext["confidence"], (int, float))

    def test_pipeline_output_has_source_location(self):
        """At least some extractions should get source_location via Source Grounding."""
        result = _run_pipeline("tech_senior.md", _mock_extractions_tech_senior)
        matched = sum(
            1 for ext in result["extractions"]
            if ext.get("source_location", {}).get("match_type") in ("exact", "normalized", "fuzzy")
        )
        assert matched > 0, "No extractions matched via Source Grounding"

    def test_pipeline_type_distribution(self):
        """Pipeline stats should count extraction types."""
        result = _run_pipeline("tech_senior.md", _mock_extractions_tech_senior)
        by_type = result["stats"]["by_type"]
        assert "candidate" in by_type
        assert "experience" in by_type
        assert "skill" in by_type

    def test_load_from_json_file(self):
        """tech_senior_raw.json should load and pipeline correctly."""
        raw = _load_tech_senior_raw()
        assert len(raw) == 14  # 7 types, 14 items total
        assert raw[0]["type"] == "candidate"
        assert raw[0]["attributes"]["name"] == "张三"


# ══════════════════════════════════════════════════════════════════
# Test: SQLite Import
# ══════════════════════════════════════════════════════════════════

class TestImport:
    """Test pipeline output imports correctly into SQLite."""

    def test_import_tech_senior(self):
        """Import tech_senior and verify candidate record."""
        db_path = _create_temp_db()
        try:
            result = _run_pipeline("tech_senior.md", _mock_extractions_tech_senior)
            with ResumeDB(db_path) as db:
                cid = db.insert_from_extractions(result["extractions"], "tech_senior.md")
                assert cid > 0

                candidate = db.get_candidate(cid)
                assert candidate is not None
                assert candidate["name"] == "张三"
                assert candidate["city"] == "北京"
        finally:
            os.unlink(db_path)

    def test_import_experiences(self):
        """Imported tech_senior should have 2 work experiences."""
        db_path = _create_temp_db()
        try:
            result = _run_pipeline("tech_senior.md", _mock_extractions_tech_senior)
            with ResumeDB(db_path) as db:
                cid = db.insert_from_extractions(result["extractions"], "tech_senior.md")
                candidate = db.get_candidate(cid)

                assert len(candidate["experiences"]) == 2
                companies = {e["company"] for e in candidate["experiences"]}
                assert "ABC科技有限公司" in companies
                assert "XYZ互联网公司" in companies
        finally:
            os.unlink(db_path)

    def test_import_skills(self):
        """Imported tech_senior should have skills including Python and Java."""
        db_path = _create_temp_db()
        try:
            result = _run_pipeline("tech_senior.md", _mock_extractions_tech_senior)
            with ResumeDB(db_path) as db:
                cid = db.insert_from_extractions(result["extractions"], "tech_senior.md")
                candidate = db.get_candidate(cid)
                skill_names = {s["name"] for s in candidate["skills"]}
                assert "Python" in skill_names
                assert "Java" in skill_names
                assert "MySQL" in skill_names
        finally:
            os.unlink(db_path)

    def test_import_certifications(self):
        """Imported tech_senior should have AWS certification."""
        db_path = _create_temp_db()
        try:
            result = _run_pipeline("tech_senior.md", _mock_extractions_tech_senior)
            with ResumeDB(db_path) as db:
                cid = db.insert_from_extractions(result["extractions"], "tech_senior.md")
                candidate = db.get_candidate(cid)
                cert_names = {c["name"] for c in candidate["certifications"]}
                assert "AWS Solutions Architect Professional" in cert_names
        finally:
            os.unlink(db_path)

    def test_import_all_three_resumes(self):
        """All three resumes should import into the same database."""
        db_path, candidate_ids = _setup_full_db()
        try:
            assert len(set(candidate_ids.values())) == 3
            with ResumeDB(db_path) as db:
                all_candidates = db.list_candidates()
                assert len(all_candidates) == 3
        finally:
            os.unlink(db_path)


# ══════════════════════════════════════════════════════════════════
# Test: Query Layer
# ══════════════════════════════════════════════════════════════════

class TestQuery:
    """Test queries return correct results after import."""

    def test_search_by_skill_python(self):
        """Searching for 'Python' should return multiple candidates."""
        db_path, _ = _setup_full_db()
        try:
            with ResumeDB(db_path) as db:
                results = db.search(skill="Python")
                assert len(results) >= 2, f"Expected >=2 Python candidates, got {len(results)}"
        finally:
            os.unlink(db_path)

    def test_search_by_city_beijing(self):
        """Searching by city should return the correct candidate."""
        db_path, _ = _setup_full_db()
        try:
            with ResumeDB(db_path) as db:
                results = db.search(city="北京")
                names = {r["name"] for r in results}
                assert "张三" in names
        finally:
            os.unlink(db_path)

    def test_search_by_education_master(self):
        """Searching by education 'Master' should return 陈芳."""
        db_path, _ = _setup_full_db()
        try:
            with ResumeDB(db_path) as db:
                results = db.search(education="Master")
                names = {r["name"] for r in results}
                assert "陈芳" in names
        finally:
            os.unlink(db_path)

    def test_get_candidate_detail(self):
        """Getting candidate detail should return all related records."""
        db_path, candidate_ids = _setup_full_db()
        try:
            with ResumeDB(db_path) as db:
                tech_id = candidate_ids["tech_senior.md"]
                detail = db.get_candidate(tech_id)

                assert detail is not None
                assert detail["name"] == "张三"
                assert len(detail["experiences"]) == 2
                assert len(detail["educations"]) == 1
                assert len(detail["skills"]) >= 4
                assert len(detail["certifications"]) >= 1
                assert len(detail["job_intentions"]) >= 1
                assert len(detail["self_evaluations"]) >= 1
        finally:
            os.unlink(db_path)

    def test_stats_overview(self):
        """Stats should return correct aggregate counts."""
        db_path, _ = _setup_full_db()
        try:
            with ResumeDB(db_path) as db:
                stats = db.stats()
                assert stats["total_candidates"] == 3
                assert stats["total_experiences"] >= 5
                assert stats["total_educations"] >= 3
                assert stats["total_skills"] >= 5
        finally:
            os.unlink(db_path)

    def test_stats_by_skill(self):
        """Stats grouped by skill should show Python with multiple candidates."""
        db_path, _ = _setup_full_db()
        try:
            with ResumeDB(db_path) as db:
                stats = db.stats(group_by="skill")
                assert "by_skill" in stats
                python_entry = next(
                    (s for s in stats["by_skill"] if s["name"] == "Python"),
                    None,
                )
                assert python_entry is not None, "Python skill not found in stats"
                assert python_entry["count"] >= 2
        finally:
            os.unlink(db_path)

    def test_list_candidates(self):
        """list_candidates should return all 3 with summary info."""
        db_path, _ = _setup_full_db()
        try:
            with ResumeDB(db_path) as db:
                candidates = db.list_candidates()
                assert len(candidates) == 3
                for c in candidates:
                    assert "id" in c
                    assert "name" in c
                    assert "skill_count" in c
        finally:
            os.unlink(db_path)

    def test_delete_candidate(self):
        """Deleting a candidate should remove it and its related data."""
        db_path, candidate_ids = _setup_full_db()
        try:
            with ResumeDB(db_path) as db:
                tech_id = candidate_ids["tech_senior.md"]
                success = db.delete_candidate(tech_id)
                assert success is True
                assert db.get_candidate(tech_id) is None
                assert len(db.list_candidates()) == 2
        finally:
            os.unlink(db_path)


# ══════════════════════════════════════════════════════════════════
# Test: JD Matching
# ══════════════════════════════════════════════════════════════════

class TestMatch:
    """Test JD-candidate matching."""

    def test_parse_jd_text(self):
        """parse_jd_text should extract structured requirements from JD text."""
        jd_text = JD_PATH.read_text(encoding="utf-8")
        requirements = parse_jd_text(jd_text)

        assert "skills" in requirements
        skill_set = {s.lower() for s in requirements["skills"]}
        assert "python" in skill_set
        assert "mysql" in skill_set or "redis" in skill_set

        assert requirements.get("min_years") == 3
        assert requirements.get("education") == "Bachelor"
        assert requirements.get("city") == "Beijing"
        assert "salary_range" in requirements

    def test_match_ranking(self):
        """Tech senior (Beijing, Python, 5yr) should rank higher than fresh graduate for this JD."""
        db_path, candidate_ids = _setup_full_db()
        try:
            jd_text = JD_PATH.read_text(encoding="utf-8")
            requirements = parse_jd_text(jd_text)

            with ResumeDB(db_path) as db:
                # Get full details for matching
                candidates = []
                for cid in candidate_ids.values():
                    detail = db.get_candidate(cid)
                    if detail:
                        candidates.append(detail)

                matcher = JDMatcher()
                results = matcher.match(requirements, candidates)

                assert len(results) == 3

                # Results should be sorted by total_score descending
                scores = [r["total_score"] for r in results]
                assert scores == sorted(scores, reverse=True)

                # Zhang San (tech senior, Beijing, Python expert) should score highest
                top_name = results[0]["name"]
                assert top_name == "张三", f"Expected 张三 on top, got {top_name}"

                # All scores should be between 0 and 1
                for r in results:
                    assert 0 <= r["total_score"] <= 1
                    for dim_score in r["scores"].values():
                        assert 0 <= dim_score <= 1
        finally:
            os.unlink(db_path)

    def test_match_scores_dimensions(self):
        """Each match result should have scores for all 5 dimensions."""
        db_path, candidate_ids = _setup_full_db()
        try:
            requirements = {
                "skills": ["Python", "Docker"],
                "min_years": 3,
                "education": "Bachelor",
                "city": "Beijing",
                "salary_range": [25000, 40000],
            }

            with ResumeDB(db_path) as db:
                candidates = []
                for cid in candidate_ids.values():
                    detail = db.get_candidate(cid)
                    if detail:
                        candidates.append(detail)

                matcher = JDMatcher()
                results = matcher.match(requirements, candidates)

                expected_dims = {"skill", "experience", "education", "city", "salary"}
                for r in results:
                    assert set(r["scores"].keys()) == expected_dims
        finally:
            os.unlink(db_path)


# ══════════════════════════════════════════════════════════════════
# Test: JSON Serialization
# ══════════════════════════════════════════════════════════════════

class TestJsonOutput:
    """Test pipeline output JSON serialization."""

    def test_output_json_serializable(self):
        """Pipeline result should be fully JSON-serializable."""
        result = _run_pipeline("tech_senior.md", _mock_extractions_tech_senior)
        output = {
            "extractions": result["extractions"],
            "inferred_relations": result["inferred_relations"],
            "stats": result["stats"],
        }
        json_str = json.dumps(output, ensure_ascii=False, indent=2)
        assert len(json_str) > 100
        parsed = json.loads(json_str)
        assert len(parsed["extractions"]) == len(result["extractions"])

    def test_output_json_file_roundtrip(self):
        """Write pipeline output to temp file and read it back."""
        result = _run_pipeline("manager.md", _mock_extractions_manager)
        output = {
            "extractions": result["extractions"],
            "inferred_relations": result["inferred_relations"],
            "stats": result["stats"],
        }
        fd, json_path = tempfile.mkstemp(suffix=".json", prefix="test_pipeline_")
        os.close(fd)
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            with open(json_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded["stats"]["total_extractions"] == result["stats"]["total_extractions"]
        finally:
            os.unlink(json_path)


# ══════════════════════════════════════════════════════════════════
# Standalone runner
# ══════════════════════════════════════════════════════════════════

def _run_standalone():
    """Run all tests without pytest."""
    test_classes = [
        TestPipeline,
        TestImport,
        TestQuery,
        TestMatch,
        TestJsonOutput,
    ]

    total = 0
    passed = 0
    failed = 0
    errors = []

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]

        for method_name in sorted(methods):
            total += 1
            test_fn = getattr(instance, method_name)
            label = f"{cls.__name__}.{method_name}"

            try:
                test_fn()
                passed += 1
                print(f"  [PASS] {label}")
            except AssertionError as e:
                failed += 1
                errors.append((label, str(e)))
                print(f"  [FAIL] {label}: {e}")
            except Exception as e:
                failed += 1
                errors.append((label, f"{type(e).__name__}: {e}"))
                print(f"  [ERROR] {label}: {type(e).__name__}: {e}")

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} passed, {failed} failed")

    if errors:
        print(f"\nFailures:")
        for label, msg in errors:
            print(f"  - {label}: {msg}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    print("=" * 60)
    print("  End-to-End Test Suite (standalone mode)")
    print("=" * 60)
    sys.exit(_run_standalone())
