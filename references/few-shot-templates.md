# Few-shot Templates

> HR 简历结构化提取的 Few-shot 示例，Claude 提取时参考

## resume 场景 (中文简历)

### 完整简历样本

以下 Few-shot 示例基于此简历片段：

```
张三
男 | 28岁 | 北京
手机: 138-0000-0000 | 邮箱: zhangsan@email.com

求职意向: Python 高级开发工程师 | 期望薪资: 25K-35K | 到岗时间: 一个月内

工作经历:
2020.07 - 至今  ABC科技有限公司  高级后端工程师
- 负责核心交易系统的架构设计和开发
- 主导微服务改造项目，将单体应用拆分为12个微服务
- 项目: 智能风控平台 (2022.03-2022.12)
  角色: 技术负责人
  描述: 基于机器学习的实时风控系统，日处理交易500万笔

2018.07 - 2020.06  DEF互联网公司  后端开发工程师
- 参与电商平台订单系统开发
- 优化数据库查询性能，接口响应时间降低60%

教育背景:
2016.09 - 2020.06  北京大学  计算机科学与技术  本科  GPA: 3.8/4.0
- 国家奖学金 (2018)

技能:
- Python (精通, 8年)
- Java (熟练, 5年)
- Docker/K8s (熟练, 3年)
- MySQL/Redis (熟练)
- 英语 CET-6

自我评价:
8年后端开发经验，擅长高并发系统设计，有良好的团队协作能力和沟通能力。

证书:
- AWS Solutions Architect Professional (2023.06, 有效期至2026.06)
- PMP 项目管理专业人士 (PMI, 2022.01)
```

---

### candidate 示例

**输入文本**:
```
张三
男 | 28岁 | 北京
手机: 138-0000-0000 | 邮箱: zhangsan@email.com
```

**提取输出**:
```json
{
  "id": "ext_001",
  "type": "candidate",
  "text": "张三\n男 | 28岁 | 北京\n手机: 138-0000-0000 | 邮箱: zhangsan@email.com",
  "summary_cn": "候选人张三，男，28岁，现居北京",
  "attributes": {
    "name": "张三",
    "gender": "男",
    "age": 28,
    "city": "北京",
    "phone": "138-0000-0000",
    "email": "zhangsan@email.com"
  },
  "source_file": "张三_简历.pdf"
}
```

---

### experience 示例 (含嵌套项目)

**输入文本**:
```
2020.07 - 至今  ABC科技有限公司  高级后端工程师
- 负责核心交易系统的架构设计和开发
- 主导微服务改造项目，将单体应用拆分为12个微服务
- 项目: 智能风控平台 (2022.03-2022.12)
  角色: 技术负责人
  描述: 基于机器学习的实时风控系统，日处理交易500万笔
```

**提取输出**:
```json
{
  "id": "ext_002",
  "type": "experience",
  "text": "2020.07 - 至今  ABC科技有限公司  高级后端工程师\n- 负责核心交易系统的架构设计和开发\n- 主导微服务改造项目，将单体应用拆分为12个微服务",
  "summary_cn": "在ABC科技任高级后端工程师，负责交易系统架构和微服务改造",
  "attributes": {
    "company": "ABC科技有限公司",
    "title": "高级后端工程师",
    "period_start": "2020.07",
    "period_end": "至今",
    "description": "负责核心交易系统的架构设计和开发；主导微服务改造项目，将单体应用拆分为12个微服务",
    "projects": [
      {
        "name": "智能风控平台",
        "role": "技术负责人",
        "period": "2022.03-2022.12",
        "description": "基于机器学习的实时风控系统，日处理交易500万笔"
      }
    ]
  },
  "source_file": "张三_简历.pdf"
}
```

---

### experience 示例 (简短经历)

**输入文本**:
```
2018.07 - 2020.06  DEF互联网公司  后端开发工程师
- 参与电商平台订单系统开发
- 优化数据库查询性能，接口响应时间降低60%
```

**提取输出**:
```json
{
  "id": "ext_003",
  "type": "experience",
  "text": "2018.07 - 2020.06  DEF互联网公司  后端开发工程师\n- 参与电商平台订单系统开发\n- 优化数据库查询性能，接口响应时间降低60%",
  "summary_cn": "在DEF互联网公司任后端开发工程师，参与电商订单系统开发和性能优化",
  "attributes": {
    "company": "DEF互联网公司",
    "title": "后端开发工程师",
    "period_start": "2018.07",
    "period_end": "2020.06",
    "duration_months": 24,
    "description": "参与电商平台订单系统开发；优化数据库查询性能，接口响应时间降低60%"
  },
  "source_file": "张三_简历.pdf"
}
```

---

### education 示例

**输入文本**:
```
2016.09 - 2020.06  北京大学  计算机科学与技术  本科  GPA: 3.8/4.0
- 国家奖学金 (2018)
```

**提取输出**:
```json
{
  "id": "ext_004",
  "type": "education",
  "text": "2016.09 - 2020.06  北京大学  计算机科学与技术  本科  GPA: 3.8/4.0",
  "summary_cn": "北京大学计算机科学与技术本科，GPA 3.8/4.0",
  "attributes": {
    "school": "北京大学",
    "major": "计算机科学与技术",
    "degree": "本科",
    "period_start": "2016.09",
    "period_end": "2020.06",
    "gpa": "3.8/4.0",
    "honors": ["国家奖学金 (2018)"]
  },
  "source_file": "张三_简历.pdf"
}
```

---

### skill 示例 (多技能批量提取)

**输入文本**:
```
- Python (精通, 8年)
- Java (熟练, 5年)
- Docker/K8s (熟练, 3年)
- MySQL/Redis (熟练)
- 英语 CET-6
```

**提取输出**:
```json
[
  {
    "id": "ext_005",
    "type": "skill",
    "text": "Python (精通, 8年)",
    "summary_cn": "Python 精通，8年经验",
    "attributes": {
      "name": "Python",
      "category": "语言",
      "level": "精通",
      "years": 8
    },
    "source_file": "张三_简历.pdf"
  },
  {
    "id": "ext_006",
    "type": "skill",
    "text": "Java (熟练, 5年)",
    "summary_cn": "Java 熟练，5年经验",
    "attributes": {
      "name": "Java",
      "category": "语言",
      "level": "熟练",
      "years": 5
    },
    "source_file": "张三_简历.pdf"
  },
  {
    "id": "ext_007",
    "type": "skill",
    "text": "Docker/K8s (熟练, 3年)",
    "summary_cn": "Docker/K8s 容器化技术，熟练，3年经验",
    "attributes": {
      "name": "Docker/K8s",
      "category": "工具",
      "level": "熟练",
      "years": 3
    },
    "source_file": "张三_简历.pdf"
  },
  {
    "id": "ext_008",
    "type": "skill",
    "text": "MySQL/Redis (熟练)",
    "summary_cn": "MySQL/Redis 数据库技术，熟练",
    "attributes": {
      "name": "MySQL/Redis",
      "category": "数据库",
      "level": "熟练"
    },
    "source_file": "张三_简历.pdf"
  },
  {
    "id": "ext_009",
    "type": "skill",
    "text": "英语 CET-6",
    "summary_cn": "英语通过大学六级",
    "attributes": {
      "name": "英语 CET-6",
      "category": "外语",
      "level": "熟练"
    },
    "source_file": "张三_简历.pdf"
  }
]
```

---

### self_evaluation 示例

**输入文本**:
```
8年后端开发经验，擅长高并发系统设计，有良好的团队协作能力和沟通能力。
```

**提取输出**:
```json
{
  "id": "ext_010",
  "type": "self_evaluation",
  "text": "8年后端开发经验，擅长高并发系统设计，有良好的团队协作能力和沟通能力。",
  "summary_cn": "资深后端工程师，擅长高并发，具备团队协作和沟通能力",
  "attributes": {
    "text": "8年后端开发经验，擅长高并发系统设计，有良好的团队协作能力和沟通能力。",
    "traits": ["后端开发", "高并发系统设计", "团队协作", "沟通能力"]
  },
  "source_file": "张三_简历.pdf"
}
```

---

### job_intention 示例

**输入文本**:
```
求职意向: Python 高级开发工程师 | 期望薪资: 25K-35K | 到岗时间: 一个月内
```

**提取输出**:
```json
{
  "id": "ext_011",
  "type": "job_intention",
  "text": "求职意向: Python 高级开发工程师 | 期望薪资: 25K-35K | 到岗时间: 一个月内",
  "summary_cn": "求职 Python 高级开发工程师，期望月薪 25K-35K，一个月内到岗",
  "attributes": {
    "position": "Python 高级开发工程师",
    "salary_min": 25000,
    "salary_max": 35000,
    "salary_unit": "K/月",
    "entry_date": "一个月内"
  },
  "source_file": "张三_简历.pdf"
}
```

---

### certification 示例 (多证书)

**输入文本**:
```
- AWS Solutions Architect Professional (2023.06, 有效期至2026.06)
- PMP 项目管理专业人士 (PMI, 2022.01)
```

**提取输出**:
```json
[
  {
    "id": "ext_012",
    "type": "certification",
    "text": "AWS Solutions Architect Professional (2023.06, 有效期至2026.06)",
    "summary_cn": "AWS 解决方案架构师专业级认证，2026年6月前有效",
    "attributes": {
      "name": "AWS Solutions Architect Professional",
      "issuer": "Amazon Web Services",
      "date": "2023.06",
      "expiry": "2026.06"
    },
    "source_file": "张三_简历.pdf"
  },
  {
    "id": "ext_013",
    "type": "certification",
    "text": "PMP 项目管理专业人士 (PMI, 2022.01)",
    "summary_cn": "PMP 项目管理认证",
    "attributes": {
      "name": "PMP 项目管理专业人士",
      "issuer": "PMI",
      "date": "2022.01"
    },
    "source_file": "张三_简历.pdf"
  }
]
```

---

### skill 示例 (隐式技能 - 从工作经历推断)

> **v1.1 新增**: 不仅从"技能"栏提取，还要从工作经历/项目描述中识别隐式技能

**输入文本** (来自 experience 描述):
```
2025 年 图灵深视 | 算法工程师
- 基于 YOLO v5 的目标检测模型训练与部署
- 使用 GAN 进行数据增强，提升小样本场景下的检测精度
- 搭建模型训练流水线，集成 MLflow 实验追踪
```

**提取输出** (从描述中推断的隐式技能):
```json
[
  {
    "id": "ext_020",
    "type": "skill",
    "text": "基于 YOLO v5 的目标检测模型训练与部署",
    "summary_cn": "掌握 YOLO 目标检测算法",
    "attributes": {
      "name": "YOLO",
      "category": "算法",
      "level": "熟练"
    },
    "source_file": "简历.pdf"
  },
  {
    "id": "ext_021",
    "type": "skill",
    "text": "使用 GAN 进行数据增强",
    "summary_cn": "掌握 GAN 数据增强技术",
    "attributes": {
      "name": "GAN",
      "category": "算法"
    },
    "source_file": "简历.pdf"
  },
  {
    "id": "ext_022",
    "type": "skill",
    "text": "集成 MLflow 实验追踪",
    "summary_cn": "掌握 MLflow 实验管理工具",
    "attributes": {
      "name": "MLflow",
      "category": "工具"
    },
    "source_file": "简历.pdf"
  }
]
```

**提取原则**: 从经历描述中识别技术关键词时，`text` 字段是包含该技能的**原文片段**（不是技能名本身）。`name` 是提炼后的技能名。

---

### skill 示例 (领域知识 + 方法论)

**输入文本** (来自 experience 描述):
```
2023.03 - 2025.02  北京华亿创新  软件开发工程师
- 负责医疗信息化平台的后端架构设计
- 主导 CI/CD 流水线搭建，实现自动化部署
- 使用 Scrum 敏捷开发模式管理迭代
```

**提取输出**:
```json
[
  {
    "id": "ext_030",
    "type": "skill",
    "text": "负责医疗信息化平台的后端架构设计",
    "summary_cn": "具备医疗信息化领域经验",
    "attributes": {
      "name": "医疗信息化",
      "category": "领域"
    },
    "source_file": "简历.pdf"
  },
  {
    "id": "ext_031",
    "type": "skill",
    "text": "主导 CI/CD 流水线搭建，实现自动化部署",
    "summary_cn": "掌握 CI/CD 持续集成/交付",
    "attributes": {
      "name": "CI/CD",
      "category": "方法论"
    },
    "source_file": "简历.pdf"
  },
  {
    "id": "ext_032",
    "type": "skill",
    "text": "使用 Scrum 敏捷开发模式管理迭代",
    "summary_cn": "掌握 Scrum 敏捷开发方法",
    "attributes": {
      "name": "Scrum",
      "category": "方法论"
    },
    "source_file": "简历.pdf"
  }
]
```

---

### 模糊时间格式处理示例

> **v1.1 新增**: 简历中常见的非标准时间格式及其标准化输出

| 原文时间 | 标准化输出 | 规则 |
|----------|-----------|------|
| `2025 年` | `"period_start": "2025.01"` | 仅年份 → 补 .01 |
| `至今` | `"period_end": "至今"` | 保留原文 |
| `2020.9` | `"period_start": "2020.09"` | 单位月份 → 补零 |
| `Jul 2020` | `"period_start": "2020.07"` | 英文月份 → 数字 |
| `2019年7月` | `"period_start": "2019.07"` | 中文月份 → 数字 |

**输入文本**:
```
2025 年 图灵深视 | 算法工程师
2021 年 无锡森标科技 | 调试工程师
```

**提取输出**:
```json
[
  {
    "id": "ext_040",
    "type": "experience",
    "text": "2025 年 图灵深视 | 算法工程师",
    "summary_cn": "在图灵深视担任算法工程师",
    "attributes": {
      "company": "图灵深视",
      "title": "算法工程师",
      "period_start": "2025.01"
    },
    "source_file": "简历.pdf"
  },
  {
    "id": "ext_041",
    "type": "experience",
    "text": "2021 年 无锡森标科技 | 调试工程师",
    "summary_cn": "在无锡森标科技担任调试工程师",
    "attributes": {
      "company": "无锡森标科技",
      "title": "调试工程师",
      "period_start": "2021.01"
    },
    "source_file": "简历.pdf"
  }
]
```

---

## 特殊格式简历示例

### 英文简历片段

**输入文本**:
```
John Zhang
Phone: +86 138-0000-0000 | Email: john@email.com
Beijing, China

WORK EXPERIENCE
Senior Backend Engineer | ABC Tech Co., Ltd | Jul 2020 - Present
```

**提取输出**:
```json
[
  {
    "id": "ext_001",
    "type": "candidate",
    "text": "John Zhang\nPhone: +86 138-0000-0000 | Email: john@email.com\nBeijing, China",
    "summary_cn": "候选人 John Zhang，现居北京",
    "attributes": {
      "name": "John Zhang",
      "phone": "+86 138-0000-0000",
      "email": "john@email.com",
      "city": "Beijing"
    },
    "source_file": "JohnZhang_Resume.pdf"
  },
  {
    "id": "ext_002",
    "type": "experience",
    "text": "Senior Backend Engineer | ABC Tech Co., Ltd | Jul 2020 - Present",
    "summary_cn": "在 ABC Tech 任高级后端工程师，2020年7月至今",
    "attributes": {
      "company": "ABC Tech Co., Ltd",
      "title": "Senior Backend Engineer",
      "period_start": "2020.07",
      "period_end": "至今"
    },
    "source_file": "JohnZhang_Resume.pdf"
  }
]
```

### 表格式简历片段

**输入文本**:
```
姓名: 李四        性别: 女        出生年月: 1995年3月
学历: 硕士        专业: 软件工程    毕业院校: 清华大学
联系电话: 139-1111-2222    电子邮箱: lisi@email.com
```

**提取输出**:
```json
[
  {
    "id": "ext_001",
    "type": "candidate",
    "text": "姓名: 李四        性别: 女        出生年月: 1995年3月\n学历: 硕士        专业: 软件工程    毕业院校: 清华大学\n联系电话: 139-1111-2222    电子邮箱: lisi@email.com",
    "summary_cn": "候选人李四，女，1995年3月生，清华大学硕士",
    "attributes": {
      "name": "李四",
      "gender": "女",
      "birth_date": "1995年3月",
      "education_level": "硕士",
      "phone": "139-1111-2222",
      "email": "lisi@email.com"
    },
    "source_file": "李四_简历.docx"
  },
  {
    "id": "ext_002",
    "type": "education",
    "text": "学历: 硕士        专业: 软件工程    毕业院校: 清华大学",
    "summary_cn": "清华大学软件工程硕士",
    "attributes": {
      "school": "清华大学",
      "major": "软件工程",
      "degree": "硕士"
    },
    "source_file": "李四_简历.docx"
  }
]
```

---

## 提取原则

1. **text 必须来自原文** - 不能改写、翻译或总结，必须是简历原文的精确片段
2. **summary_cn 是中文语义总结** - 简洁描述这段信息的核心含义
3. **attributes 遵循类型定义** - 参见 `extraction-types.md` 中的必填/可选属性
4. **一段文本可产生多个提取** - 如表格式简历的个人信息区域同时包含 candidate + education
5. **ID 按顺序递增** - `ext_001`, `ext_002`, ...
6. **时间格式标准化** - 无论原文格式如何 (2020年7月、Jul 2020、2020/07、2025 年)，`period_start`/`period_end` 统一为 `YYYY.MM` 格式。仅年份时补 `.01`，"至今" 保留原文
7. **薪资数值化** - `25K` -> `salary_min: 25000`，`30万/年` -> 按月换算或保留年薪并标注 `salary_unit`
8. **技能拆分** - 每个独立技能单独提取为一条 skill 记录，不合并
9. **隐式技能提取** - 不仅从"技能"栏提取，还要从工作经历/项目描述中识别算法、领域知识、方法论等隐式技能。`text` 为包含该技能的原文片段，`name` 为提炼的技能名
