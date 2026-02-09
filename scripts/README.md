# Structured Extractor - Post-processing Scripts

后处理管道脚本集合，用于处理 LLM 提取的结构化信息。

## 脚本列表

### 1. source_grounding.py
**功能**: 三级文本对齐策略，将提取文本定位到源文件精确位置

**策略**:
- Level 1: 精确子串匹配 (`str.find()`) → confidence=1.0
- Level 2: 去空白规范化匹配 → confidence=0.85
- Level 3: 模糊匹配 (`difflib.SequenceMatcher`) → confidence=ratio*0.8

**输出**: 为每个提取项添加 `source_location` 字段
```json
{
  "char_start": 42,
  "char_end": 60,
  "char_interval": [42, 60],
  "line": 8,
  "match_type": "exact",
  "confidence": 1.0
}
```

**独立运行示例**:
```python
from source_grounding import SourceGrounder

grounder = SourceGrounder(source_text)
result = grounder.process(extractions)
```

---

### 2. overlap_dedup.py
**功能**: 检测并去除重叠提取项

**规则**:
- 字符区间重叠 > 50% → 保留更完整的（属性更多 + 文本更长）

**独立运行示例**:
```python
from overlap_dedup import OverlapDeduplicator

dedup = OverlapDeduplicator(overlap_threshold=0.5)
result = dedup.process(extractions)
```

---

### 3. confidence_scorer.py
**功能**: 四维度加权置信度评分

**评分维度** (权重):
- match_quality (35%): 匹配质量
- attr_completeness (25%): 属性完整性
- text_specificity (20%): 文本长度适中性 (10-200字符最佳)
- type_consistency (20%): 类型一致性

**输出**: 为每个提取项添加 `confidence` 字段 [0, 1]

**独立运行示例**:
```python
from confidence_scorer import ConfidenceScorer

scorer = ConfidenceScorer()
result = scorer.process(extractions)
```

---

### 4. entity_resolver.py
**功能**: 实体消歧和别名合并

**相似度计算**:
- 包含关系: "MLevel" in "MMultiGateLevel" → 0.9 * (shorter/longer)
- 编辑距离: `difflib.SequenceMatcher.ratio()`

**合并策略**:
- 贪心聚类，选最长名称为标准名
- 更新所有 relation 中的 from/to 引用

**独立运行示例**:
```python
from entity_resolver import EntityResolver

resolver = EntityResolver(threshold=0.7)
result = resolver.process(extractions)
```

---

### 5. relation_inferrer.py
**功能**: 基于规则表推断实体间关系

**Scope 划分**: 按 (source_file, line_group_50) 分组

**推断规则表**:
```python
(rule, entity) → governs
(constraint, entity) → validates
(event, entity) → subscribes_to
(state, entity) → transitions
(entity, entity) → relates_to
```

**输出**: 返回 (原始extractions, 新推断的relations列表)

**独立运行示例**:
```python
from relation_inferrer import RelationInferrer

inferrer = RelationInferrer(scope_window=50)
extractions, inferred_relations = inferrer.process(extractions)
```

---

### 6. kg_injector.py
**功能**: 转换为知识图谱注入格式

**转换规则**:
- 只转换 confidence >= threshold 的项
- entity name: summary_cn[:50] 或 text[:50]
- observations: [summary_cn, "Source: file:line", "Confidence: score", ...]

**输出格式**:
```json
{
  "entities": [
    {
      "name": "倍增门解算器",
      "entityType": "entity",
      "observations": [
        "倍增门解算器核心类",
        "Source: MGMultiGate.cs:42",
        "Confidence: 0.85"
      ]
    }
  ],
  "relations": [
    {
      "from": "倍增门解算器",
      "to": "NativeArray只读保护",
      "relationType": "governed_by"
    }
  ]
}
```

**独立运行示例**:
```python
from kg_injector import KGInjector

injector = KGInjector(confidence_threshold=0.3)
kg_format = injector.convert(extractions, relations)
```

---

### 7. pipeline.py (主管道)
**功能**: 串联所有算法 + CLI 入口

**执行顺序**:
1. Source Grounding
2. Overlap Deduplication
3. Confidence Scoring
4. Entity Resolution (可选)
5. Relation Inference (可选)
6. KG Injection (可选)

**配置项**:
```python
{
  "source_grounding": True,
  "overlap_dedup": True,
  "confidence_scoring": True,
  "entity_resolution": False,  # 默认关闭
  "relation_inference": False, # 默认关闭
  "kg_injection": False,       # 默认关闭
  "confidence_threshold": 0.3,
  "overlap_threshold": 0.5,
  "entity_similarity_threshold": 0.7,
  "scope_window": 50,
}
```

---

## CLI 使用

### 基础用法

```bash
python pipeline.py \
  --input raw_extractions.json \
  --source code.py \
  --output result.json
```

### 启用所有功能

```bash
python pipeline.py \
  --input raw_extractions.json \
  --source code.py \
  --enable-entity-resolution \
  --enable-relation-inference \
  --enable-kg-injection \
  --output result.json
```

### 自定义配置

1. 创建 `config.json`:
```json
{
  "confidence_threshold": 0.5,
  "overlap_threshold": 0.6,
  "entity_similarity_threshold": 0.8,
  "scope_window": 30,
  "entity_resolution": true,
  "relation_inference": true
}
```

2. 运行:
```bash
python pipeline.py \
  --input raw_extractions.json \
  --source code.py \
  --config config.json \
  --output result.json
```

---

## 输入格式

LLM 提取的原始 JSON 格式:

```json
[
  {
    "type": "entity",
    "text": "MGMultiGateSolver",
    "summary_cn": "倍增门解算器"
  },
  {
    "type": "rule",
    "text": "禁止直接修改 NativeArray",
    "summary_cn": "NativeArray只读保护",
    "trigger_context": "修改解算器数据时",
    "consequence": "崩溃或数据损坏"
  },
  {
    "type": "relation",
    "from": "MGMultiGateSolver",
    "to": "AddCommand",
    "relation_type": "uses"
  }
]
```

---

## 输出格式

### 标准输出 (JSON)

```json
{
  "extractions": [...],          // 处理后的提取项
  "inferred_relations": [...],   // 推断的关系
  "kg_format": {...},            // KG 格式 (如果启用)
  "stats": {
    "total_extractions": 10,
    "by_type": {
      "entity": 5,
      "rule": 3,
      "constraint": 2
    },
    "avg_confidence": 0.736,
    "confidence_distribution": {
      "high (>=0.7)": 7,
      "medium (0.3-0.7)": 2,
      "low (<0.3)": 1
    },
    "match_quality": {
      "exact": 8,
      "normalized": 1,
      "fuzzy": 1
    },
    "inferred_relations": 12
  }
}
```

---

## 测试

运行测试数据:

```bash
cd scripts
python pipeline.py \
  --input test_data/sample_input.json \
  --source test_data/sample_source.cs \
  --enable-entity-resolution \
  --enable-relation-inference \
  --output test_data/sample_output.json
```

---

## 依赖

只使用 Python 标准库:
- `difflib` - 序列匹配
- `json` - JSON 解析
- `re` - 正则表达式
- `sys` - 系统
- `argparse` - 命令行参数
- `pathlib` - 路径处理

---

## 设计原则

1. **纯标准库** - 无需安装第三方包
2. **模块化** - 每个算法独立可用
3. **可配置** - 所有参数可调
4. **容错性** - 缺失字段不会崩溃
5. **Windows 兼容** - 避免 Unicode 控制台问题

---

## 常见问题

### Q: 为什么 entity_resolution 默认关闭?

A: 实体消歧可能合并不该合并的实体。建议先运行一次查看结果，确认需要后再启用。

### Q: 为什么 relation_inference 默认关闭?

A: 推断关系可能产生噪音。如果 LLM 已经提取了显式关系，可能不需要推断。

### Q: 如何调整置信度阈值?

A: 通过 `--config` 指定配置文件，或修改 `pipeline.py` 中的 `DEFAULT_CONFIG`。

### Q: 如何扩展推断规则?

A: 修改 `relation_inferrer.py` 中的 `INFERENCE_RULES` 字典。

---

## 性能

- 1000 条提取项 + 500 行源文件: < 1 秒
- 所有算法均为 O(n²) 或更优
- 内存占用: 提取项数量 * ~1KB
