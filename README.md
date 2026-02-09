# resumeX

```
                                   __  __
  _ __ ___  ___ _   _ _ __ ___   ___\ \/ /
 | '__/ _ \/ __| | | | '_ ` _ \ / _ \\  /
 | | |  __/\__ \ |_| | | | | | |  __//  \
 |_|  \___||___/\__,_|_| |_| |_|\___/_/\_\
```

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)
![License MIT](https://img.shields.io/badge/License-MIT-green)
![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-purple)
![Cursor](https://img.shields.io/badge/Cursor-Rule-orange)

**[English](#english)** | **[中文](#中文)** | **[日本語](#日本語)**

---

<a id="english"></a>

## English

### What is resumeX?

**AI-powered resume structured extraction tool** -- a Claude Code Skill / Cursor Rule that extracts 7 types of HR data (candidate info, work experience, education, skills, etc.) from PDF/DOCX resumes, builds a searchable SQLite talent database, and supports JD smart matching.

Built on [Google LangExtract](https://github.com/google/langextract)'s Source Grounding algorithm, deeply optimized for HR scenarios.

From resume files to talent database, no external API keys required.

### Key Features

| Feature | Description |
|---------|-------------|
| 7 Extraction Types | candidate, experience, education, skill, self_evaluation, job_intention, certification |
| PDF/DOCX Parsing | PyMuPDF (single/dual-column auto-detection), python-docx (heading/bold/table preservation) |
| 6-Step Pipeline | Source grounding / overlap dedup / confidence scoring / entity resolution / relation inference / KG conversion |
| SQLite Talent DB | 8 normalized tables, multi-dimension search, group statistics |
| JD Smart Matching | Auto-extract requirements from JD text, 5-dimension weighted scoring |
| 6 CLI Tools | parse.py, pipeline.py, import_resume.py, query.py, match.py |
| Zero External API | Only PyMuPDF + python-docx required |

### Architecture

```
Resume Files (PDF/DOCX/TXT)
    |
    v
+-------------------+     +----------------+     +-------------------+
|  parse.py         | MD  |  Claude AI     | JSON|  pipeline.py      |
|  Document Parser  +---->+  Structured    +---->+  6-Step Pipeline  |
|  (PyMuPDF/docx)   |     |  Extraction    |     |  (Ground/Dedup/   |
+-------------------+     |  (7 HR Types)  |     |   Score)          |
                          +----------------+     +--------+----------+
                                                          | JSON
                                                          v
+-------------------+     +----------------+     +-------------------+
|  match.py         | <-- |  query.py      | <-- |  import_resume.py |
|  JD Matching      |     |  Search/Stats  |     |  Import to DB     |
|  (5-dim scoring)  |     |  (4 commands)  |     |  (single/batch)   |
+-------------------+     +----------------+     +-------------------+
```

### Quick Start

#### 1. Install Dependencies

```bash
pip install PyMuPDF python-docx
```

Everything else uses Python standard library (sqlite3, difflib, json, argparse).

#### 2. Install as Claude Code Skill

```bash
# Copy to your project's Claude Code skills directory
cp -r resumeX/ your-project/.claude/skills/resume-extractor/
```

Claude Code will auto-detect and load this Skill via `SKILL.md`.

#### 3. Install as Cursor Rule

```bash
# Clone to .cursor/skills/
cd your-project
git clone https://github.com/sputnicyoji/resumeX .cursor/skills/resumex

# Run install script
# Windows PowerShell:
.cursor/skills/resumex/install.ps1

# macOS / Linux:
bash .cursor/skills/resumex/install.sh
```

#### 4. End-to-End Example

```bash
# Step 1: Parse resume
python scripts/parse.py --input resume.pdf --output resume.md

# Step 2: Claude extracts structured data (auto-triggered in Claude Code)
# -> outputs raw.json

# Step 3: Run post-processing pipeline
python scripts/pipeline.py \
  --input raw.json \
  --source resume.md \
  --config assets/presets/resume.json \
  --output result.json

# Step 4: Import to database
python scripts/import_resume.py --input result.json

# Step 5: Query candidates
python scripts/query.py search "Python Beijing"
python scripts/query.py list

# Step 6: JD matching
python scripts/match.py --jd jd.txt --top 10
```

### CLI Tools

| Tool | Description | Usage |
|------|-------------|-------|
| `parse.py` | PDF/DOCX to Markdown | `python scripts/parse.py --input resume.pdf` |
| `pipeline.py` | 6-step post-processing | `python scripts/pipeline.py --input raw.json --source resume.md` |
| `import_resume.py` | Import to SQLite | `python scripts/import_resume.py --input result.json` |
| `query.py` | Search/stats/detail/list | `python scripts/query.py search "Python"` |
| `match.py` | JD smart matching | `python scripts/match.py --jd jd.txt --top 10` |

### JD Matching Dimensions

| Dimension | Weight | Algorithm |
|-----------|--------|-----------|
| Skill | 40% | JD required skills hit rate (exact + contains) |
| Experience | 20% | Actual years / required years |
| Education | 15% | Degree level comparison (5 levels) |
| City | 15% | City name contains match |
| Salary | 10% | Overlap between JD range and candidate expectation |

### Claude Code vs Cursor

| Feature | Claude Code (SKILL.md) | Cursor (.mdc) |
|---------|------------------------|---------------|
| Skill location | `.claude/skills/resume-extractor/` | `.cursor/skills/resumex/` |
| Rule file | `SKILL.md` (auto-detected) | `.cursor/rules/resumex.mdc` |
| Pipeline | Same `scripts/pipeline.py` | Same `scripts/pipeline.py` |
| Database | Same `scripts/storage.py` | Same `scripts/storage.py` |

---

<a id="中文"></a>

## 中文

### resumeX 是什么?

**AI 驱动的简历结构化提取工具** -- Claude Code Skill / Cursor Rule，从 PDF/DOCX 简历中提取候选人信息、工作经历、教育背景、技能等 7 种 HR 数据，构建可搜索的 SQLite 人才数据库，支持 JD 智能匹配。

基于 [Google LangExtract](https://github.com/google/langextract) 的 Source Grounding 算法重构，针对 HR 场景深度优化。

从简历文件到人才数据库，无需外部 API 密钥。

### 核心特性

| 特性 | 说明 |
|------|------|
| 7 种提取类型 | candidate, experience, education, skill, self_evaluation, job_intention, certification |
| PDF/DOCX 解析 | PyMuPDF (单栏/双栏自动检测), python-docx (标题/粗体/表格保留) |
| 6 步处理管道 | 源码定位 / 重叠去重 / 置信度评分 / 实体消歧 / 关系推断 / KG 转换 |
| SQLite 人才库 | 8 张规范化表, 多维度搜索, 分组统计 |
| JD 智能匹配 | 从 JD 文本自动提取需求, 5 维加权评分排序 |
| 6 个 CLI 工具 | parse.py, pipeline.py, import_resume.py, query.py, match.py |
| 零外部 API | 仅需 PyMuPDF + python-docx |

### 架构

```
简历文件 (PDF/DOCX/TXT)
    |
    v
+-------------------+     +----------------+     +-------------------+
|  parse.py         | MD  |  Claude AI     | JSON|  pipeline.py      |
|  文档解析          +---->+  结构化提取     +---->+  6步后处理管道     |
|  (PyMuPDF/docx)   |     |  (7种HR类型)   |     |  (定位/去重/评分)  |
+-------------------+     +----------------+     +--------+----------+
                                                          | JSON
                                                          v
+-------------------+     +----------------+     +-------------------+
|  match.py         | <-- |  query.py      | <-- |  import_resume.py |
|  JD 智能匹配      |     |  搜索/统计/详情 |     |  导入人才数据库    |
|  (5维加权评分)     |     |  (4个子命令)   |     |  (单文件/批量)     |
+-------------------+     +----------------+     +-------------------+
```

### 快速开始

#### 1. 安装依赖

```bash
pip install PyMuPDF python-docx
```

其他全部使用 Python 标准库 (sqlite3, difflib, json, argparse)。

#### 2. 安装为 Claude Code Skill

```bash
# 复制到项目的 Claude Code skills 目录
cp -r resumeX/ your-project/.claude/skills/resume-extractor/
```

Claude Code 会通过 `SKILL.md` 自动检测并加载此 Skill。

#### 3. 安装为 Cursor Rule

```bash
# 克隆到 .cursor/skills/
cd your-project
git clone https://github.com/sputnicyoji/resumeX .cursor/skills/resumex

# 运行安装脚本
# Windows PowerShell:
.cursor/skills/resumex/install.ps1

# macOS / Linux:
bash .cursor/skills/resumex/install.sh
```

#### 4. 端到端示例

```bash
# Step 1: 解析简历
python scripts/parse.py --input resume.pdf --output resume.md

# Step 2: Claude 提取结构化数据 (在 Claude Code 中自动触发)
# -> 输出 raw.json

# Step 3: 运行后处理管道
python scripts/pipeline.py \
  --input raw.json \
  --source resume.md \
  --config assets/presets/resume.json \
  --output result.json

# Step 4: 导入数据库
python scripts/import_resume.py --input result.json

# Step 5: 查询候选人
python scripts/query.py search "Python Beijing"
python scripts/query.py list

# Step 6: JD 匹配
python scripts/match.py --jd jd.txt --top 10
```

### CLI 工具

| 工具 | 说明 | 用法 |
|------|------|------|
| `parse.py` | PDF/DOCX 转 Markdown | `python scripts/parse.py --input resume.pdf` |
| `pipeline.py` | 6 步后处理管道 | `python scripts/pipeline.py --input raw.json --source resume.md` |
| `import_resume.py` | 导入 SQLite 数据库 | `python scripts/import_resume.py --input result.json` |
| `query.py` | 搜索/统计/详情/列表 | `python scripts/query.py search "Python"` |
| `match.py` | JD 智能匹配 | `python scripts/match.py --jd jd.txt --top 10` |

### 数据库表结构 (8 张规范化表)

| 表 | 说明 |
|----|------|
| `candidates` | 候选人基本信息 (姓名/性别/年龄/手机/邮箱/城市) |
| `experiences` | 工作经历 (公司/职位/时间段/职责/时长) |
| `projects` | 项目经历 (嵌套在 experience 下) |
| `educations` | 教育背景 (学校/专业/学位/GPA) |
| `skills` | 技能字典表 (技能名/类别) |
| `candidate_skills` | 候选人-技能关联 (熟练度/年限) |
| `job_intentions` | 求职意向 (期望职位/薪资/城市/到岗时间) |
| `self_evaluations` | 自我评价 (原文/特质标签) |
| `certifications` | 资质证书 (证书名/机构/日期/有效期) |

### JD 匹配评分维度

| 维度 | 权重 | 算法 |
|------|------|------|
| skill (技能) | 40% | JD 要求技能的命中率 (精确+包含匹配) |
| experience (经验) | 20% | 实际工作年限 / 要求年限 |
| education (学历) | 15% | 学历等级对比 (5 级: 高中~博士) |
| city (城市) | 15% | 城市名称包含匹配 |
| salary (薪资) | 10% | JD 薪资范围与候选人期望的重叠度 |

---

<a id="日本語"></a>

## 日本語

### resumeX とは？

**AI駆動の履歴書構造化抽出ツール** -- Claude Code Skill / Cursor Ruleとして、PDF/DOCX形式の履歴書から候補者情報、職務経歴、学歴、スキルなど7種類のHRデータを抽出し、検索可能なSQLite人材データベースを構築、JDスマートマッチングに対応。

[Google LangExtract](https://github.com/google/langextract)のSource Groundingアルゴリズムをベースに、HRシナリオ向けに最適化。

履歴書ファイルから人材データベースまで、外部APIキー不要。

### 主な機能

| 機能 | 説明 |
|------|------|
| 7種類の抽出タイプ | candidate, experience, education, skill, self_evaluation, job_intention, certification |
| PDF/DOCX解析 | PyMuPDF (単段/2段組自動検出)、python-docx (見出し/太字/表の保持) |
| 6ステップパイプライン | ソース位置特定 / 重複除去 / 信頼度スコアリング / エンティティ解決 / 関係推論 / KG変換 |
| SQLite人材DB | 正規化テーブル8つ、多次元検索、グループ統計 |
| JDスマートマッチング | JDテキストから要件を自動抽出、5次元加重スコアリング |
| 6つのCLIツール | parse.py, pipeline.py, import_resume.py, query.py, match.py |
| 外部API不要 | PyMuPDF + python-docxのみ |

### アーキテクチャ

```
履歴書ファイル (PDF/DOCX/TXT)
    |
    v
+-------------------+     +----------------+     +-------------------+
|  parse.py         | MD  |  Claude AI     | JSON|  pipeline.py      |
|  ドキュメント解析   +---->+  構造化抽出     +---->+  6ステップ        |
|  (PyMuPDF/docx)   |     |  (7種HRタイプ)  |     |  パイプライン      |
+-------------------+     +----------------+     +--------+----------+
                                                          | JSON
                                                          v
+-------------------+     +----------------+     +-------------------+
|  match.py         | <-- |  query.py      | <-- |  import_resume.py |
|  JDマッチング      |     |  検索/統計/詳細  |     |  DB取り込み        |
|  (5次元スコア)     |     |  (4コマンド)    |     |  (単体/一括)       |
+-------------------+     +----------------+     +-------------------+
```

### クイックスタート

#### 1. 依存関係のインストール

```bash
pip install PyMuPDF python-docx
```

その他はすべてPython標準ライブラリ (sqlite3, difflib, json, argparse) を使用。

#### 2. Claude Code Skillとしてインストール

```bash
# プロジェクトのClaude Code skillsディレクトリにコピー
cp -r resumeX/ your-project/.claude/skills/resume-extractor/
```

Claude Codeが `SKILL.md` を通じて自動的にこのSkillを検出・ロード。

#### 3. Cursor Ruleとしてインストール

```bash
# .cursor/skills/ にクローン
cd your-project
git clone https://github.com/sputnicyoji/resumeX .cursor/skills/resumex

# インストールスクリプトを実行
# Windows PowerShell:
.cursor/skills/resumex/install.ps1

# macOS / Linux:
bash .cursor/skills/resumex/install.sh
```

#### 4. エンドツーエンドの例

```bash
# Step 1: 履歴書を解析
python scripts/parse.py --input resume.pdf --output resume.md

# Step 2: Claudeが構造化データを抽出 (Claude Codeで自動実行)
# -> raw.json を出力

# Step 3: 後処理パイプラインを実行
python scripts/pipeline.py \
  --input raw.json \
  --source resume.md \
  --config assets/presets/resume.json \
  --output result.json

# Step 4: データベースに取り込み
python scripts/import_resume.py --input result.json

# Step 5: 候補者を検索
python scripts/query.py search "Python Tokyo"
python scripts/query.py list

# Step 6: JDマッチング
python scripts/match.py --jd jd.txt --top 10
```

### CLIツール

| ツール | 説明 | 使い方 |
|--------|------|--------|
| `parse.py` | PDF/DOCXをMarkdownに変換 | `python scripts/parse.py --input resume.pdf` |
| `pipeline.py` | 6ステップ後処理 | `python scripts/pipeline.py --input raw.json --source resume.md` |
| `import_resume.py` | SQLiteに取り込み | `python scripts/import_resume.py --input result.json` |
| `query.py` | 検索/統計/詳細/一覧 | `python scripts/query.py search "Python"` |
| `match.py` | JDスマートマッチング | `python scripts/match.py --jd jd.txt --top 10` |

### JDマッチングスコア次元

| 次元 | 重み | アルゴリズム |
|------|------|-------------|
| skill (スキル) | 40% | JD要求スキルのヒット率 (完全一致+部分一致) |
| experience (経験) | 20% | 実務年数 / 要求年数 |
| education (学歴) | 15% | 学歴レベル比較 (5段階) |
| city (都市) | 15% | 都市名の部分一致 |
| salary (給与) | 10% | JD給与範囲と候補者希望の重複度 |

---

## File Structure

```
resumeX/
|
+-- SKILL.md                        # Claude Code Skill definition
+-- README.md                       # This file
|
+-- cursor/                         # Cursor IDE rule
|   +-- resumex.mdc                #   Cursor .mdc rule file
|
+-- install.ps1                     # Cursor install script (Windows)
+-- install.sh                      # Cursor install script (macOS/Linux)
|
+-- assets/presets/                  # Preset configurations
|   +-- resume.json                #   HR resume extraction preset
|
+-- references/                     # Detailed reference docs
|   +-- extraction-types.md        #   7 HR extraction type definitions
|   +-- few-shot-templates.md      #   Chinese resume Few-shot templates
|   +-- output-schema.md           #   JSON Schema output format
|   +-- post-processing.md         #   Pipeline algorithm details
|
+-- scripts/                        # Python pipeline & CLI tools
|   +-- parse.py                   #   Document parser CLI (PDF/DOCX -> Markdown)
|   +-- parsers/                   #   Format parsers
|   |   +-- pdf_parser.py          #     PDF (PyMuPDF, dual-column support)
|   |   +-- docx_parser.py         #     DOCX (python-docx)
|   +-- pipeline.py                #   Post-processing pipeline (6 steps)
|   +-- source_grounding.py        #   Text alignment to source
|   +-- overlap_dedup.py           #   Overlap deduplication
|   +-- confidence_scorer.py       #   4-dimension confidence scoring
|   +-- entity_resolver.py         #   Entity resolution
|   +-- relation_inferrer.py       #   Relation inference
|   +-- kg_injector.py             #   Knowledge graph conversion
|   +-- storage.py                 #   SQLite talent DB (ResumeDB)
|   +-- import_resume.py           #   Database import CLI
|   +-- query.py                   #   Query CLI (search/stats/detail/list)
|   +-- match.py                   #   JD matching CLI (5-dim scoring)
|
+-- test/                           # Integration tests
|   +-- test_e2e.py                #   25 end-to-end test cases
|   +-- sample_resumes/            #   Sample resume files
|   +-- sample_jd.txt              #   Sample job description
```

## Performance

| Metric | Value |
|--------|-------|
| Pipeline: 1000 extractions + 500 lines | < 1s |
| PDF parsing: 10-page resume | < 2s |
| DB query: 10,000 candidates | < 100ms |
| JD matching: 10,000 candidates | < 1s |
| External deps | PyMuPDF + python-docx only |
| Python version | 3.10+ |

## License

MIT License. See [LICENSE](LICENSE).
