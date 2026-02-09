"""
Resume Database Storage Layer - SQLite

简历数据库存储层，将 pipeline 输出的 extractions 结构化存入 SQLite。

表结构对应 7 种 HR 提取类型:
- candidates: 候选人基本信息
- experiences: 工作经历
- educations: 教育背景
- skills: 技能库 (全局唯一)
- candidate_skills: 候选人-技能关联
- job_intentions: 求职意向
- self_evaluations: 自我评价
- certifications: 资格证书
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


class ResumeDB:
    """简历数据库管理器"""

    DEFAULT_DB_PATH = "data/resumes.db"

    def __init__(self, db_path: str = None):
        """
        Args:
            db_path: 数据库文件路径，默认 data/resumes.db
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self._ensure_dir()
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def _ensure_dir(self):
        """确保数据库目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _create_tables(self):
        """创建所有表"""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                gender TEXT,
                age INTEGER,
                phone TEXT,
                email TEXT,
                city TEXT,
                education_level TEXT,
                source_file TEXT,
                raw_json TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                company TEXT,
                title TEXT,
                start_date TEXT,
                end_date TEXT,
                duration_months INTEGER,
                description TEXT,
                projects TEXT,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS educations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                school TEXT,
                major TEXT,
                degree TEXT,
                start_date TEXT,
                end_date TEXT,
                gpa TEXT,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                UNIQUE(name, category)
            );

            CREATE TABLE IF NOT EXISTS candidate_skills (
                candidate_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                level TEXT,
                years INTEGER,
                PRIMARY KEY (candidate_id, skill_id),
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS job_intentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                position TEXT,
                industry TEXT,
                city TEXT,
                salary_min INTEGER,
                salary_max INTEGER,
                entry_date TEXT,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS self_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                text TEXT,
                traits TEXT,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS certifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                name TEXT,
                issuer TEXT,
                date TEXT,
                expiry TEXT,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_exp_candidate ON experiences(candidate_id);
            CREATE INDEX IF NOT EXISTS idx_edu_candidate ON educations(candidate_id);
            CREATE INDEX IF NOT EXISTS idx_cs_candidate ON candidate_skills(candidate_id);
            CREATE INDEX IF NOT EXISTS idx_ji_candidate ON job_intentions(candidate_id);
            CREATE INDEX IF NOT EXISTS idx_se_candidate ON self_evaluations(candidate_id);
            CREATE INDEX IF NOT EXISTS idx_cert_candidate ON certifications(candidate_id);
            CREATE INDEX IF NOT EXISTS idx_candidates_city ON candidates(city);
            CREATE INDEX IF NOT EXISTS idx_candidates_edu ON candidates(education_level);
        """)
        self.conn.commit()

    # ── 导入 ──────────────────────────────────────────────────────

    def insert_from_extractions(
        self, extractions: list[dict], source_file: str = ""
    ) -> int:
        """
        从 pipeline 输出的 extractions 导入一份简历

        Args:
            extractions: pipeline 输出的提取项列表
            source_file: 源文件名

        Returns:
            candidate_id (主键)
        """
        # 按类型分组
        by_type = {}
        for ext in extractions:
            ext_type = ext.get("type", "unknown")
            by_type.setdefault(ext_type, []).append(ext)

        # 1. 插入候选人
        candidates = by_type.get("candidate", [])
        if not candidates:
            raise ValueError("extractions must contain at least one 'candidate' type")

        candidate_data = candidates[0]
        candidate_id = self._insert_candidate(candidate_data, source_file)

        # 2. 插入工作经历
        for exp in by_type.get("experience", []):
            self._insert_experience(candidate_id, exp)

        # 3. 插入教育背景
        for edu in by_type.get("education", []):
            self._insert_education(candidate_id, edu)

        # 4. 插入技能
        for skill in by_type.get("skill", []):
            self._insert_skill(candidate_id, skill)

        # 5. 插入自我评价
        for se in by_type.get("self_evaluation", []):
            self._insert_self_evaluation(candidate_id, se)

        # 6. 插入求职意向
        for ji in by_type.get("job_intention", []):
            self._insert_job_intention(candidate_id, ji)

        # 7. 插入证书
        for cert in by_type.get("certification", []):
            self._insert_certification(candidate_id, cert)

        self.conn.commit()
        return candidate_id

    def _insert_candidate(self, ext: dict, source_file: str) -> int:
        """插入候选人记录"""
        attrs = ext.get("attributes", {})
        cursor = self.conn.execute(
            """INSERT INTO candidates
            (name, gender, age, phone, email, city, education_level, source_file, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                attrs.get("name", ext.get("text", "")),
                attrs.get("gender"),
                _safe_int(attrs.get("age")),
                attrs.get("phone"),
                attrs.get("email"),
                attrs.get("city"),
                attrs.get("education_level"),
                source_file,
                json.dumps(ext, ensure_ascii=False),
            ),
        )
        return cursor.lastrowid

    def _insert_experience(self, candidate_id: int, ext: dict):
        """插入工作经历"""
        attrs = ext.get("attributes", {})
        projects = attrs.get("projects")
        projects_json = json.dumps(projects, ensure_ascii=False) if projects else None
        # extraction-types.md 定义为 period_start/period_end, 兼容 start_date/end_date
        start = attrs.get("period_start") or attrs.get("start_date")
        end = attrs.get("period_end") or attrs.get("end_date")
        self.conn.execute(
            """INSERT INTO experiences
            (candidate_id, company, title, start_date, end_date,
             duration_months, description, projects)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate_id,
                attrs.get("company"),
                attrs.get("title"),
                start,
                end,
                _safe_int(attrs.get("duration_months")),
                attrs.get("description"),
                projects_json,
            ),
        )

    def _insert_education(self, candidate_id: int, ext: dict):
        """插入教育背景"""
        attrs = ext.get("attributes", {})
        # extraction-types.md 定义为 period_start/period_end, 兼容 start_date/end_date
        start = attrs.get("period_start") or attrs.get("start_date")
        end = attrs.get("period_end") or attrs.get("end_date")
        self.conn.execute(
            """INSERT INTO educations
            (candidate_id, school, major, degree, start_date, end_date, gpa)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate_id,
                attrs.get("school"),
                attrs.get("major"),
                attrs.get("degree"),
                start,
                end,
                attrs.get("gpa"),
            ),
        )

    def _insert_skill(self, candidate_id: int, ext: dict):
        """插入技能 (全局去重)"""
        attrs = ext.get("attributes", {})
        skill_name = attrs.get("name", ext.get("text", ""))
        category = attrs.get("category")

        if not skill_name:
            return

        # 先尝试获取已有技能
        row = self.conn.execute(
            "SELECT id FROM skills WHERE name = ? AND category IS ?",
            (skill_name, category),
        ).fetchone()

        if row:
            skill_id = row["id"]
        else:
            cursor = self.conn.execute(
                "INSERT INTO skills (name, category) VALUES (?, ?)",
                (skill_name, category),
            )
            skill_id = cursor.lastrowid

        # 关联候选人和技能
        self.conn.execute(
            """INSERT OR IGNORE INTO candidate_skills
            (candidate_id, skill_id, level, years)
            VALUES (?, ?, ?, ?)""",
            (
                candidate_id,
                skill_id,
                attrs.get("level"),
                _safe_int(attrs.get("years")),
            ),
        )

    def _insert_self_evaluation(self, candidate_id: int, ext: dict):
        """插入自我评价"""
        attrs = ext.get("attributes", {})
        traits = attrs.get("traits")
        traits_json = json.dumps(traits, ensure_ascii=False) if traits else None
        self.conn.execute(
            "INSERT INTO self_evaluations (candidate_id, text, traits) VALUES (?, ?, ?)",
            (
                candidate_id,
                attrs.get("text", ext.get("text", "")),
                traits_json,
            ),
        )

    def _insert_job_intention(self, candidate_id: int, ext: dict):
        """插入求职意向"""
        attrs = ext.get("attributes", {})
        self.conn.execute(
            """INSERT INTO job_intentions
            (candidate_id, position, industry, city,
             salary_min, salary_max, entry_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate_id,
                attrs.get("position"),
                attrs.get("industry"),
                attrs.get("city"),
                _safe_int(attrs.get("salary_min")),
                _safe_int(attrs.get("salary_max")),
                attrs.get("entry_date"),
            ),
        )

    def _insert_certification(self, candidate_id: int, ext: dict):
        """插入证书"""
        attrs = ext.get("attributes", {})
        self.conn.execute(
            """INSERT INTO certifications
            (candidate_id, name, issuer, date, expiry)
            VALUES (?, ?, ?, ?, ?)""",
            (
                candidate_id,
                attrs.get("name", ext.get("text", "")),
                attrs.get("issuer"),
                attrs.get("date"),
                attrs.get("expiry"),
            ),
        )

    # ── 查询 ──────────────────────────────────────────────────────

    def search(
        self,
        query: str = None,
        skill: str = None,
        city: str = None,
        min_years: int = None,
        education: str = None,
    ) -> list[dict]:
        """
        搜索候选人

        支持多维度组合查询。自然语言 query 会被拆分为关键词，
        分别匹配 name/city/skill/education 字段。

        Args:
            query: 自然语言查询 (可选)
            skill: 技能筛选 (可选)
            city: 城市筛选 (可选)
            min_years: 最低工作年限 (可选)
            education: 学历筛选 (可选)

        Returns:
            候选人摘要列表
        """
        conditions = []
        params = []

        # 基础查询: 从 candidates 出发
        base_sql = """
            SELECT DISTINCT c.id, c.name, c.gender, c.age,
                   c.phone, c.city, c.education_level, c.source_file
            FROM candidates c
        """
        joins = []

        # 技能筛选
        if skill:
            joins.append("""
                JOIN candidate_skills cs_filter ON c.id = cs_filter.candidate_id
                JOIN skills s_filter ON cs_filter.skill_id = s_filter.id
            """)
            conditions.append("s_filter.name LIKE ?")
            params.append(f"%{skill}%")

        # 城市筛选
        if city:
            conditions.append("c.city LIKE ?")
            params.append(f"%{city}%")

        # 学历筛选
        if education:
            conditions.append("c.education_level LIKE ?")
            params.append(f"%{education}%")

        # 最低工作年限 (通过经历的 duration_months 总和估算)
        if min_years is not None:
            joins.append("""
                LEFT JOIN (
                    SELECT candidate_id, SUM(duration_months) as total_months
                    FROM experiences
                    GROUP BY candidate_id
                ) exp_sum ON c.id = exp_sum.candidate_id
            """)
            conditions.append("COALESCE(exp_sum.total_months, 0) >= ?")
            params.append(min_years * 12)

        # 自然语言查询: 拆分为关键词逐个 LIKE 匹配
        if query:
            keywords = _parse_query_keywords(query)
            for kw in keywords:
                # 尝试匹配 name / city / skill / education_level
                conditions.append("""(
                    c.name LIKE ? OR c.city LIKE ?
                    OR c.education_level LIKE ?
                    OR c.id IN (
                        SELECT cs2.candidate_id FROM candidate_skills cs2
                        JOIN skills s2 ON cs2.skill_id = s2.id
                        WHERE s2.name LIKE ?
                    )
                )""")
                like_kw = f"%{kw}%"
                params.extend([like_kw, like_kw, like_kw, like_kw])

        # 组装 SQL
        sql = base_sql + " ".join(joins)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY c.id DESC"

        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_candidate(self, candidate_id: int) -> Optional[dict]:
        """
        获取候选人完整详情

        Args:
            candidate_id: 候选人 ID

        Returns:
            包含所有关联数据的字典，不存在返回 None
        """
        # 基本信息
        row = self.conn.execute(
            "SELECT * FROM candidates WHERE id = ?", (candidate_id,)
        ).fetchone()

        if not row:
            return None

        result = dict(row)

        # 工作经历
        exps = self.conn.execute(
            "SELECT * FROM experiences WHERE candidate_id = ? ORDER BY start_date DESC",
            (candidate_id,),
        ).fetchall()
        result["experiences"] = [dict(e) for e in exps]

        # 教育背景
        edus = self.conn.execute(
            "SELECT * FROM educations WHERE candidate_id = ? ORDER BY start_date DESC",
            (candidate_id,),
        ).fetchall()
        result["educations"] = [dict(e) for e in edus]

        # 技能
        skills = self.conn.execute(
            """SELECT s.name, s.category, cs.level, cs.years
            FROM candidate_skills cs
            JOIN skills s ON cs.skill_id = s.id
            WHERE cs.candidate_id = ?
            ORDER BY s.name""",
            (candidate_id,),
        ).fetchall()
        result["skills"] = [dict(s) for s in skills]

        # 求职意向
        intentions = self.conn.execute(
            "SELECT * FROM job_intentions WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchall()
        result["job_intentions"] = [dict(i) for i in intentions]

        # 自我评价
        evals = self.conn.execute(
            "SELECT * FROM self_evaluations WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchall()
        result["self_evaluations"] = [dict(e) for e in evals]

        # 证书
        certs = self.conn.execute(
            "SELECT * FROM certifications WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchall()
        result["certifications"] = [dict(c) for c in certs]

        return result

    def list_candidates(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """
        列出所有候选人摘要

        Args:
            limit: 最大返回数量
            offset: 偏移量

        Returns:
            候选人摘要列表
        """
        rows = self.conn.execute(
            """SELECT c.id, c.name, c.city, c.education_level, c.source_file,
                      c.created_at,
                      COUNT(DISTINCT e.id) as exp_count,
                      COUNT(DISTINCT ed.id) as edu_count,
                      COUNT(DISTINCT cs.skill_id) as skill_count
               FROM candidates c
               LEFT JOIN experiences e ON c.id = e.candidate_id
               LEFT JOIN educations ed ON c.id = ed.candidate_id
               LEFT JOIN candidate_skills cs ON c.id = cs.candidate_id
               GROUP BY c.id
               ORDER BY c.id DESC
               LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]

    def stats(self, group_by: str = None) -> dict:
        """
        统计分析

        Args:
            group_by: 分组维度 (skill / education / city / None)

        Returns:
            统计结果字典
        """
        result = {}

        # 总数
        total = self.conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        result["total_candidates"] = total

        if group_by == "skill":
            rows = self.conn.execute(
                """SELECT s.name, s.category, COUNT(cs.candidate_id) as count
                FROM skills s
                JOIN candidate_skills cs ON s.id = cs.skill_id
                GROUP BY s.id
                ORDER BY count DESC"""
            ).fetchall()
            result["by_skill"] = [dict(r) for r in rows]

        elif group_by == "education":
            rows = self.conn.execute(
                """SELECT education_level, COUNT(*) as count
                FROM candidates
                WHERE education_level IS NOT NULL
                GROUP BY education_level
                ORDER BY count DESC"""
            ).fetchall()
            result["by_education"] = [dict(r) for r in rows]

        elif group_by == "city":
            rows = self.conn.execute(
                """SELECT city, COUNT(*) as count
                FROM candidates
                WHERE city IS NOT NULL
                GROUP BY city
                ORDER BY count DESC"""
            ).fetchall()
            result["by_city"] = [dict(r) for r in rows]

        else:
            # 综合统计
            result["total_experiences"] = self.conn.execute(
                "SELECT COUNT(*) FROM experiences"
            ).fetchone()[0]
            result["total_educations"] = self.conn.execute(
                "SELECT COUNT(*) FROM educations"
            ).fetchone()[0]
            result["total_skills"] = self.conn.execute(
                "SELECT COUNT(*) FROM skills"
            ).fetchone()[0]
            result["total_certifications"] = self.conn.execute(
                "SELECT COUNT(*) FROM certifications"
            ).fetchone()[0]

            # 平均经历数
            avg_row = self.conn.execute(
                """SELECT AVG(cnt) FROM (
                    SELECT COUNT(*) as cnt FROM experiences
                    GROUP BY candidate_id
                )"""
            ).fetchone()
            result["avg_experiences_per_candidate"] = (
                round(avg_row[0], 1) if avg_row[0] else 0
            )

        return result

    def delete_candidate(self, candidate_id: int) -> bool:
        """
        删除候选人及所有关联数据

        Args:
            candidate_id: 候选人 ID

        Returns:
            是否成功删除
        """
        cursor = self.conn.execute(
            "DELETE FROM candidates WHERE id = ?", (candidate_id,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def close(self):
        """关闭数据库连接"""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ── 工具函数 ──────────────────────────────────────────────────────

def _safe_int(value) -> Optional[int]:
    """安全转换整数，失败返回 None"""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_query_keywords(query: str) -> list[str]:
    """
    从自然语言查询中提取关键词

    过滤掉常见虚词和数字单位词。

    Args:
        query: 原始查询字符串

    Returns:
        关键词列表
    """
    # 常见虚词/停用词
    stop_words = {
        "year", "years", "the", "a", "an", "in", "at", "of", "and", "or",
        "with", "to", "for", "is", "are",
    }

    tokens = query.replace(",", " ").replace("/", " ").split()
    keywords = []

    for token in tokens:
        token = token.strip()
        if not token:
            continue
        # 跳过纯数字（可能是年限，但没有上下文不好用）
        if token.isdigit():
            continue
        if token.lower() in stop_words:
            continue
        keywords.append(token)

    return keywords


if __name__ == "__main__":
    # 快速测试
    import tempfile
    import os

    db_path = os.path.join(tempfile.gettempdir(), "test_resume.db")

    with ResumeDB(db_path) as db:
        # 模拟 pipeline 输出
        extractions = [
            {
                "type": "candidate",
                "text": "Zhang San",
                "attributes": {
                    "name": "Zhang San",
                    "phone": "13800138000",
                    "city": "Beijing",
                    "education_level": "Bachelor",
                },
            },
            {
                "type": "experience",
                "attributes": {
                    "company": "ByteDance",
                    "title": "Senior Developer",
                    "start_date": "2020-01",
                    "end_date": "2023-06",
                    "duration_months": 42,
                },
            },
            {
                "type": "skill",
                "text": "Python",
                "attributes": {"name": "Python", "category": "programming"},
            },
        ]

        cid = db.insert_from_extractions(extractions, "test.pdf")
        print(f"Inserted candidate ID: {cid}")

        detail = db.get_candidate(cid)
        print(f"Name: {detail['name']}, Skills: {len(detail['skills'])}")

        results = db.search(skill="Python")
        print(f"Search 'Python': {len(results)} results")

        print(f"Stats: {db.stats()}")

    os.unlink(db_path)
    print("Test passed.")
