# Output Schema

> HR 简历提取的完整输出 JSON Schema 定义

## 顶层结构

```json
{
  "metadata": { ... },
  "extractions": [ ... ],
  "relations": [ ... ],
  "stats": { ... }
}
```

## metadata (必填)

```json
{
  "source_file": "string - 简历文件路径",
  "preset": "resume | custom",
  "pipeline_config": {
    "source_grounding": "boolean",
    "overlap_dedup": "boolean",
    "confidence_scoring": "boolean",
    "entity_resolution": "boolean",
    "relation_inference": "boolean",
    "kg_injection": "boolean"
  },
  "generated_at": "string - ISO 8601 时间戳",
  "extractor_version": "1.0.0"
}
```

## extraction 对象 (必填)

```json
{
  "id": "string - ext_001 格式, 顺序递增",
  "type": "candidate | experience | education | skill | self_evaluation | job_intention | certification",
  "text": "string - 简历原文精确片段 (不可改写)",
  "summary_cn": "string - 中文语义总结",
  "attributes": "object - 按 type 定义的属性 (见下方)",
  "source_file": "string - 简历文件名",
  "location": {
    "line": "number - 行号 (1-based)",
    "char_start": "number - 起始字符位置",
    "char_end": "number - 结束字符位置",
    "match_type": "exact | normalized | fuzzy | none",
    "confidence": "number - 0.0~1.0 置信度"
  }
}
```

### location 字段说明

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| `line` | number | 行号 | Source Grounding 填充 |
| `char_start` | number | 起始字符位置 | Source Grounding 填充 |
| `char_end` | number | 结束字符位置 | Source Grounding 填充 |
| `match_type` | string | 匹配类型 | Source Grounding 填充 |
| `confidence` | number | 置信度评分 | Confidence Scoring 覆写 |

**match_type 含义**:

| 值 | 说明 | 典型置信度 |
|----|------|-----------|
| `exact` | 精确子串匹配 | 1.0 |
| `normalized` | 忽略空白后匹配 | 0.85 |
| `fuzzy` | difflib 模糊对齐 | 0.4~0.8 |
| `none` | 未匹配到 | 0.0 |

## attributes 按 type 定义

### type: candidate

```json
{
  "name": "string (必填) - 候选人姓名",
  "gender": "string (可选) - 性别 (男/女)",
  "age": "number (可选) - 年龄",
  "birth_date": "string (可选) - 出生日期 (如 1998年3月、1998.03)",
  "phone": "string (可选) - 手机号",
  "email": "string (可选) - 电子邮箱",
  "city": "string (可选) - 所在城市",
  "education_level": "string (可选) - 最高学历 (博士/硕士/本科/大专/高中)",
  "years_of_experience": "number (可选) - 工作年限",
  "photo_url": "string (可选) - 照片链接或位置标记"
}
```

### type: experience

```json
{
  "company": "string (必填) - 公司名称",
  "title": "string (必填) - 职位名称",
  "period_start": "string (可选) - 入职时间 (YYYY.MM 格式)",
  "period_end": "string (可选) - 离职时间 (YYYY.MM 或 '至今')",
  "duration_months": "number (可选) - 在职月数",
  "description": "string (可选) - 工作职责描述 (多条用分号分隔)",
  "projects": [
    {
      "name": "string - 项目名称",
      "role": "string - 担任角色",
      "period": "string - 项目时间段",
      "description": "string - 项目描述"
    }
  ]
}
```

### type: education

```json
{
  "school": "string (必填) - 学校名称",
  "degree": "string (必填) - 学位 (博士/硕士/本科/大专/高中/其他)",
  "major": "string (可选) - 专业名称",
  "period_start": "string (可选) - 入学时间 (YYYY.MM)",
  "period_end": "string (可选) - 毕业时间 (YYYY.MM)",
  "gpa": "string (可选) - GPA (保留原始格式如 3.8/4.0)",
  "honors": "array<string> (可选) - 荣誉/奖学金列表"
}
```

### type: skill

```json
{
  "name": "string (必填) - 技能名称",
  "category": "语言 | 框架 | 工具 | 数据库 | 外语 | 软技能 | 证书相关 | 其他 (可选)",
  "level": "精通 | 熟练 | 掌握 | 了解 | 其他 (可选)",
  "years": "number (可选) - 使用年限"
}
```

### type: self_evaluation

```json
{
  "text": "string (必填) - 自我评价原文",
  "traits": "array<string> (可选) - AI 提取的关键特质标签"
}
```

### type: job_intention

```json
{
  "position": "string (必填) - 期望职位",
  "industry": "string (可选) - 期望行业",
  "city": "string (可选) - 期望工作城市",
  "salary_min": "number (可选) - 最低期望月薪 (元)",
  "salary_max": "number (可选) - 最高期望月薪 (元)",
  "salary_unit": "K/月 | 万/年 | 面议 (可选) - 薪资单位",
  "entry_date": "string (可选) - 到岗时间 (如 '一个月内'、'随时到岗')"
}
```

### type: certification

```json
{
  "name": "string (必填) - 证书名称",
  "issuer": "string (可选) - 颁发机构",
  "date": "string (可选) - 获得日期",
  "expiry": "string (可选) - 有效期截止日期",
  "cert_id": "string (可选) - 证书编号"
}
```

## relations 数组 (可选, Relation Inference 产生)

```json
{
  "from": "string - extraction ID (ext_xxx)",
  "to": "string - extraction ID (ext_xxx)",
  "type": "worked_at | studied_at | has_skill | certified_by | intends | evaluated_as",
  "scope": "string - 共现范围标识"
}
```

**关系类型说明**:

| 类型 | 含义 | 典型来源组合 |
|------|------|-------------|
| `worked_at` | 候选人在某公司工作 | candidate -> experience |
| `studied_at` | 候选人在某学校就读 | candidate -> education |
| `has_skill` | 候选人具备某技能 | candidate -> skill |
| `certified_by` | 候选人持有某证书 | candidate -> certification |
| `intends` | 候选人的求职意向 | candidate -> job_intention |
| `evaluated_as` | 候选人的自我评价 | candidate -> self_evaluation |
| `skill_used_at` | 技能在某段经历中使用 | skill -> experience |
| `project_at` | 项目属于某段工作经历 | experience -> experience |

## stats (Pipeline 自动生成)

```json
{
  "total": "number - 提取总数",
  "by_type": {
    "candidate": "number",
    "experience": "number",
    "education": "number",
    "skill": "number",
    "self_evaluation": "number",
    "job_intention": "number",
    "certification": "number"
  },
  "avg_confidence": "number - 平均置信度",
  "dedup_removed": "number - 去重移除数",
  "entities_merged": "number - 实体合并数"
}
```

## Claude 提取阶段的输出格式

Claude 在提取阶段只需要输出 `extractions` 数组，不需要包含 `location` 字段（由 Source Grounding 后处理填充）：

```json
[
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
]
```

**Pipeline 后处理后会自动添加**:
- `location` 字段 (Source Grounding)
- `confidence` 评分 (Confidence Scoring)
- 去除重复项 (Overlap Dedup)
- 实体合并 (Entity Resolution, 可选)
- 关系推断 (Relation Inference, 可选)
