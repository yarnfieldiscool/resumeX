# Post-Processing Pipeline

> 6 步后处理管道算法说明，调试管道问题时参考

## 管道总览

```
Claude 原始提取 (JSON)
    |
    v
1. Source Grounding -----> 填充 location (char_start/end, line, match_type)
    |
    v
2. Overlap Dedup --------> 移除位置重叠的重复提取
    |
    v
3. Confidence Scoring ---> 4维度加权评分, 覆写 confidence
    |
    v
4. Entity Resolution ----> 合并同义实体 (可选)
    |
    v
5. Relation Inference ---> 推断提取项间关系 (可选)
    |
    v
6. KG Injection ---------> 转换并注入知识图谱 (可选)
```

---

## 1. Source Grounding (文本对齐定位)

**脚本**: `scripts/source_grounding.py`

**目的**: 将 Claude 提取的 `text` 片段精确定位到原文中的字符位置

**三级匹配策略**:

| 级别 | 方法 | 条件 | 置信度 |
|------|------|------|--------|
| L1 精确 | `str.find()` | 原文包含完全相同子串 | 1.0 |
| L2 规范化 | 忽略空白后 `find()` | 去除多余空白后匹配 | 0.85 |
| L3 模糊 | `difflib.SequenceMatcher` | token 级别最长公共子序列 | ratio * 0.8 |

**L3 详细说明**:
- 将 query 和 source 都按空白分词
- 使用 `SequenceMatcher(None, q_tokens, s_tokens, autojunk=False)`
- `find_longest_match()` 找最长连续匹配段
- ratio = 匹配 token 数 / query token 数
- 要求 ratio >= 0.5 才算有效匹配

**输出**: 每个 extraction 的 `location` 字段被填充

---

## 2. Overlap Dedup (重叠去重)

**脚本**: `scripts/overlap_dedup.py`

**目的**: 移除位置重叠的重复提取，保留更完整的一个

**算法**:
1. 按 `char_start` 排序所有有位置信息的 extraction
2. 对每对提取计算重叠比例:
   ```
   overlap_len = min(a.end, b.end) - max(a.start, b.start)
   overlap_ratio = overlap_len / min(len_a, len_b)
   ```
3. 重叠比例 > 50% 时，保留范围更大的（非 first-win）
4. 无位置信息的 extraction 不参与去重，直接保留

**与 LangExtract 的区别**:
- LangExtract 使用 first-win 策略（先到先得）
- 本实现使用 best-win 策略（保留更完整的提取）

---

## 3. Confidence Scoring (置信度评分)

**脚本**: `scripts/confidence_scorer.py`

**目的**: 为每个提取项计算综合质量分

**4 维度加权**:

| 维度 | 权重 | 评分逻辑 |
|------|------|---------|
| 匹配质量 match_quality | 0.35 | exact=1.0, normalized=0.85, fuzzy=0.6, none=0.1 |
| 属性完整度 attr_completeness | 0.25 | (属性数 + 有summary) / 3, 最大1.0 |
| 文本具体性 text_specificity | 0.20 | 10-200字符=1.0, 过短/过长递减 |
| 类型一致性 type_consistency | 0.20 | 默认 0.9 (type 字段合法时) |

**评分公式**:
```
confidence = sum(weight_i * score_i) for i in 4 dimensions
```

**典型分数范围**:
- 高质量: >= 0.7 (精确匹配 + 完整属性)
- 中等: 0.4 ~ 0.7 (模糊匹配 or 属性不完整)
- 低质量: < 0.4 (未匹配 or 缺失关键信息)

---

## 4. Entity Resolution (实体消歧)

**脚本**: `scripts/entity_resolver.py`

**目的**: 合并同义实体（如 "MLevel" 和 "MMultiGateLevel" 指向同一实体）

**算法**:
1. 筛选 type=entity 的提取
2. 计算所有实体对之间的相似度:
   - **包含关系**: a 包含 b 或 b 包含 a → 0.9
   - **编辑距离**: `SequenceMatcher.ratio()` (不区分大小写)
3. 相似度 >= 阈值 (默认 0.7) 的实体聚为一类
4. 每个聚类选最长名称为标准名
5. 重写所有引用 (attributes 中的 entity 名称)

**贪心聚类**: 遍历实体列表，依次将相似的归入现有聚类

---

## 5. Relation Inference (关系推断)

**脚本**: `scripts/relation_inferrer.py`

**目的**: 基于提取项的位置共现和类型组合推断关系

**推断规则表**:

| from type | to type | 推断关系 |
|-----------|---------|---------|
| rule | entity | governs |
| constraint | entity | validates |
| event | entity | subscribes_to |
| state | entity | transitions |
| entity | entity | relates_to |

**共现分组**: 按 `source_file:行号//50` 分组（约 50 行为一个作用域）

**算法**:
1. 将所有提取按共现范围分组
2. 在每个组内，对所有提取对查询推断规则表
3. 匹配到规则的生成 relation 记录

---

## 6. 输出格式 (Output Formatting)

Pipeline 完成后，支持三种输出格式。**必须询问用户选择**（可多选）:

### 6a. JSON 文件 (始终可用)

Pipeline 的原始输出，保存为 `.json` 文件。这是核心格式，Markdown 和 KG 都从这里转换。

### 6b. Markdown 报告 (始终可用)

由 AI 将 JSON 转换为人类可读的结构化报告，按 extraction type 分组，包含源码位置和置信度。

### 6c. KG Injection (需要 KG 工具)

**脚本**: `scripts/kg_injector.py`

**目的**: 将高质量提取转换为知识图谱格式

**前提**: 用户环境中有知识图谱 MCP 工具 (如 `aim_create_entities`)

**过滤规则**: confidence < 阈值 (默认 0.3) 的提取不注入

**转换规则**:
- extraction → entity: `{name, entityType, observations[]}`
  - name: summary_cn (截取前50字符) 或 text (截取前50字符)
  - entityType: extraction type
  - observations: [summary_cn, source位置, confidence]
- relation → relation: `{from, to, relationType}`

**输出格式** (兼容 aim_create_entities / aim_create_relations):
```json
{
  "entities": [
    {
      "name": "新手引导关卡自动上阵并进入战斗",
      "entityType": "rule",
      "observations": [
        "新手引导关卡自动上阵并进入战斗",
        "Source: AMultiGateLevel.cs:58",
        "Confidence: 0.85"
      ]
    }
  ],
  "relations": [
    {
      "from": "ext_001",
      "to": "ext_003",
      "relationType": "governs"
    }
  ]
}
```

---

## Pipeline 配置

### 默认配置

```json
{
  "source_grounding": true,
  "overlap_dedup": true,
  "confidence_scoring": true,
  "entity_resolution": false,
  "relation_inference": false,
  "kg_injection": false,
  "confidence_threshold": 0.3
}
```

### 按场景配置

| 场景 | grounding | dedup | scoring | entity_res | rel_infer |
|------|-----------|-------|---------|------------|-----------|
| code-logic | on | on | on | off | off |
| doc-structure | on | on | on | on | on |
| log-analysis | on | on | on | off | off |

**输出格式在 pipeline 完成后单独选择** (JSON / Markdown / KG)，不属于 pipeline 配置。

### CLI 用法

```bash
python scripts/pipeline.py \
  --input raw_extractions.json \
  --source original_file.cs \
  --config '{"source_grounding":true,"overlap_dedup":true,"confidence_scoring":true}' \
  --output final_extractions.json
```

---

## 调试指南

| 问题 | 检查点 |
|------|--------|
| 所有 match_type 都是 none | 检查 text 是否来自原文，是否有隐藏字符 |
| 去重过多 | 降低重叠阈值 (默认 50%) |
| 置信度普遍偏低 | 检查 attributes 是否足够完整 |
| 实体合并错误 | 提高 entity_resolver threshold (默认 0.7) |
| 关系推断噪声多 | 缩小共现范围 (默认 50 行) |
| KG 注入过少 | 降低 confidence_threshold (默认 0.3) |
