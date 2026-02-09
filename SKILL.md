---
name: resume-extractor
description: "HR 简历结构化提取专家。Use when: 需要从简历 (PDF/DOCX/TXT) 中提取
  候选人信息、工作经历、教育背景、技能、自我评价、求职意向、资质证书。
  适用于: 简历解析、人才数据库构建、候选人搜索、JD匹配、招聘数据分析。
  基于 Google LangExtract 算法层重构，针对 HR 场景深度优化。
  提供: (1) 7种HR提取类型分类框架 (2) 中文简历Few-shot模板库
  (3) 7步后处理管道 (时间标准化/Source Grounding/去重/评分/消歧/关系推断/KG转换)
  (4) PDF/DOCX文档解析器 (5) SQLite人才数据库+导入/查询/匹配CLI
  (6) JD-候选人智能匹配 (5维加权评分)。
  仅需 PyMuPDF + python-docx，无需外部 API。"
---

# Resume Extractor

> 简历结构化提取 | 7 种 HR 类型 | PDF/DOCX 解析 | 7 步管道 | SQLite 人才库 | JD 匹配

## 核心禁令 (CRITICAL)

1. **禁止跳过 Few-shot** - 提取时必须按 `references/few-shot-templates.md` 中的模板输出
2. **禁止自由格式输出** - 必须严格遵循 `references/output-schema.md` 定义的 JSON Schema
3. **禁止跳过后处理** - 原始提取必须经过 `scripts/pipeline.py` 处理后才算完成
4. **禁止低质量输出** - confidence < 0.3 的提取必须过滤

## 快速决策树

```
我需要处理简历?
    |
    +-- 输入格式是什么?
    |   +-- .pdf       --> python parse.py --input resume.pdf --output resume.md
    |   +-- .docx/.doc --> python parse.py --input resume.docx --output resume.md
    |   +-- .txt/.md   --> 直接使用，无需解析
    |
    +-- Step 1: 解析为纯文本 (parse.py)
    |
    +-- Step 2: 选择预设 (resume.json)
    |
    +-- Step 3: Claude 提取 (7种HR类型，按 Few-shot 模板)
    |
    +-- Step 4: 运行后处理管道 (pipeline.py)
    |
    +-- Step 5: 导入数据库 (import_resume.py)
    |   +-- 单文件: --input result.json
    |   +-- 批量:   --input-dir ./results/
    |
    +-- Step 6: 查询 / 匹配
        +-- 搜索:  python query.py search "Python 北京"
        +-- 统计:  python query.py stats --by skill
        +-- 详情:  python query.py detail 1
        +-- JD匹配: python match.py --jd jd.txt --top 10
```

## 工作流

### Step 1: 文档解析 + 噪音清理

将 PDF/DOCX 简历解析为 Markdown 纯文本，自动清理招聘平台水印/追踪码:

```bash
# 单文件
python scripts/parse.py --input resume.pdf --output resume.md

# 批量模式
python scripts/parse.py --input-dir ./resumes/ --output-dir ./parsed/
```

**v1.1**: 自动清理 BOSS直聘/猎聘等平台嵌入的 base64-like 追踪码行

**支持的格式**:

| 格式 | 解析器 | 依赖 | 特殊能力 |
|------|--------|------|---------|
| `.pdf` | PdfParser (PyMuPDF) | `pip install PyMuPDF` | 单栏/双栏自动检测 + 水印清理 |
| `.docx` | DocxParser (python-docx) | `pip install python-docx` | 标题/粗体/表格保留 |
| `.doc` | DocxParser (有限支持) | 同上 | 兼容模式 |
| `.txt/.md` | 无需解析 | - | 直接使用 |

### Step 1.5: 文件名元数据提取 (可选)

招聘平台文件名通常包含岗位/城市/薪资等元数据，可提取为 context_hints:

```bash
python scripts/filename_parser.py "【高级Web后端开发工程师_成都 18-25K】唐双 6年.pdf"
# 输出: {"position": "高级Web后端开发工程师", "city": "成都", "salary_min": 18000, ...}
```

**v1.1**: 生成的 context_hints 可在 Claude 提取时补充候选人城市等缺失信息

### Step 2: 选择预设

使用简历预设配置:

```
预设文件: assets/presets/resume.json
  - 重点: 全部 7 种 HR 类型
  - 管道: 7 步全开 (含时间标准化+实体消歧+关系推断)
```

### Step 3: Claude 提取

按以下规则从简历文本中提取结构化信息:

**7 种提取类型** (详见 `references/extraction-types.md`):

| 类型 | 识别特征 | 典型数量 |
|------|---------|---------|
| `candidate` | 姓名、性别、年龄、手机、邮箱、城市 | 1 |
| `experience` | 公司、职位、时间段、职责、嵌套项目 | 2-5 |
| `education` | 学校、专业、学位、GPA、荣誉 | 1-3 |
| `skill` | 技能名、类别、熟练度、年限 | 5-15 |
| `self_evaluation` | 自我评价原文、关键特质标签 | 0-1 |
| `job_intention` | 期望职位、薪资、城市、到岗时间 | 0-1 |
| `certification` | 证书名、颁发机构、日期、有效期 | 0-5 |

**输出格式** (每个提取项):

```json
{
  "id": "ext_001",
  "type": "candidate",
  "text": "张三\n男 | 28岁 | 北京\n手机: 138-0000-0000",
  "summary_cn": "候选人张三，男，28岁，现居北京",
  "attributes": {
    "name": "张三",
    "gender": "男",
    "age": 28,
    "city": "北京",
    "phone": "138-0000-0000"
  },
  "source_file": "张三_简历.pdf"
}
```

**Few-shot 模板**: 见 `references/few-shot-templates.md`

### Step 4: 运行后处理管道

```bash
# 使用简历预设 (推荐)
python scripts/pipeline.py --input raw.json --source resume.md \
  --config assets/presets/resume.json --output result.json
```

**管道步骤** (详见 `references/post-processing.md`):

```
1. Time Normalization --> 时间格式标准化 (v1.1 新增)
2. Source Grounding   --> 精确定位 (char_start/end + line)
3. Overlap Dedup      --> 去除重复提取
4. Confidence Score   --> 4维度质量评分
5. Entity Resolution  --> 同名候选人合并 (HR默认开启)
6. Relation Inference --> 人-公司-技能关系推断 (HR默认开启)
7. KG Injection       --> 知识图谱格式转换 (可选)
```

### Step 5: 导入数据库

将 Pipeline 输出导入 SQLite 人才数据库:

```bash
# 单文件导入
python scripts/import_resume.py --input result.json

# 批量导入
python scripts/import_resume.py --input-dir ./results/

# 显示详情
python scripts/import_resume.py --input result.json --verbose

# 指定数据库路径
python scripts/import_resume.py --input result.json --db data/resumes.db
```

### Step 6: 查询与匹配

```bash
# 搜索候选人 (自然语言)
python scripts/query.py search "Python 北京"

# 搜索候选人 (精确筛选)
python scripts/query.py search --skill Python --city 北京 --min-years 3 --education 本科

# 查看候选人详情
python scripts/query.py detail 1

# 列出所有候选人
python scripts/query.py list --limit 20

# 统计分析
python scripts/query.py stats
python scripts/query.py stats --by skill
python scripts/query.py stats --by education
python scripts/query.py stats --by city

# JD 匹配 (从文本文件自动提取需求)
python scripts/match.py --jd jd.txt --top 10

# JD 匹配 (从 JSON 需求文件)
python scripts/match.py --jd-json requirements.json --top 10 --verbose
```

**JD JSON 格式**:

```json
{
  "skills": ["Python", "Django", "Redis"],
  "min_years": 3,
  "education": "Bachelor",
  "city": "Beijing",
  "salary_range": [20000, 35000]
}
```

**匹配评分维度**: skill(40%) + experience(20%) + education(15%) + city(15%) + salary(10%)

## 预设配置快速参考

| 预设 | 重点类型 | 默认后处理 |
|------|---------|-----------|
| `resume` | 全部 7 种 HR 类型 | 7 步全开 (含时间标准化+实体消歧+关系推断) |

## 核心原则

1. **Few-shot 驱动** - 提取质量的关键在于 Few-shot 模板，不是自由发挥
2. **Pipeline 后处理** - 原始提取必须经过 Python 管道处理才算完成
3. **text 必须来自原文** - 提取的 text 字段是简历原文精确片段，不是改写或翻译
4. **技能单独提取** - 每个技能是独立记录，不合并到一条
5. **时间格式统一** - period_start/period_end 统一为 YYYY.MM 格式（仅年份补 .01，"至今" 保留原文）
6. **隐式技能提取** - 不仅从"技能"栏提取，还要从工作经历/项目描述中识别算法、领域知识、方法论等隐式技能 (v1.1)
7. **技能分类 8 类** - 语言/框架/工具/数据库/外语/算法/领域/方法论 + 软技能/证书相关/其他 (v1.1)

---

## Red Flags

看到这些信号时立即检查:

| 红旗信号 | 正确做法 |
|----------|----------|
| "直接从 PDF 提取 JSON" | 必须先 parse.py 转文本，再 Claude 提取 |
| "不需要 Few-shot" | 必须按模板格式输出，否则后处理会失败 |
| "text 字段我翻译/总结了一下" | text 必须是原文精确子串，summary_cn 才是总结 |
| "不需要运行 pipeline.py" | 原始提取缺少 location 和 confidence，必须后处理 |
| "手动写 location 字段" | location 由 Source Grounding 算法填充 |
| "把所有技能合成一条记录" | 每个技能必须单独提取为一条 skill 记录 |
| "薪资保留原始文本格式" | salary_min/max 必须转为数值 (元) |
| "直接存数据库跳过 pipeline" | 必须先 pipeline 后处理再导入 |

---

## Anti-Rationalization

| 借口 | 反驳 | 正确做法 |
|------|------|----------|
| "简历很短不需要后处理" | 短简历也需要 Source Grounding 定位 | 运行 pipeline |
| "只有 3 个技能不需要去重" | 去重是自动的，不增加成本 | 运行 pipeline |
| "用户只要候选人信息" | 先提取全部 7 类，用户可按需过滤 | 完整提取 |
| "PDF 解析太麻烦直接截图" | parse.py 支持单栏/双栏自动检测 | 使用 parse.py |
| "不需要 JD 匹配" | match.py 是可选步骤，但先确认用户需求 | 询问用户 |
| "pipeline.py 报错了就跳过" | 修复错误而非跳过后处理 | 调试 pipeline |

---

## Common Mistakes

| 错误 | 症状 | 预防 |
|------|------|------|
| text 字段改写原文 | Source Grounding 全部 match_type=none | 确保 text 是原文子串 |
| 忘记指定 source_file | pipeline 无法分组去重 | 每个提取项必须有 source_file |
| experience 的 projects 不是数组 | import_resume.py 导入失败 | projects 必须是对象数组 |
| 薪资未数值化 | match.py 匹配分异常 | 25K -> salary_min: 25000 |
| 技能合并为一条 | query.py 技能统计不准 | 每个技能独立提取 |
| 未先解析 PDF/DOCX | 提取质量极差 | 先 parse.py 转 Markdown |
| attributes 缺少必填字段 | confidence 评分偏低 | 按 extraction-types.md 的必填属性 |

---

## 详细参考

| 文件 | 内容 | 何时读取 |
|------|------|---------|
| `references/extraction-types.md` | 7种HR类型详细定义和识别规则 | 提取前必读 |
| `references/few-shot-templates.md` | 中文简历的 Few-shot 示例 | 提取时参考 |
| `references/output-schema.md` | 完整 JSON Schema | 验证输出时 |
| `references/post-processing.md` | 后处理算法详细说明 | 调试管道时 |
