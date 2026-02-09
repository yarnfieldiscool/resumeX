"""
Knowledge Graph Injection Module

将提取结果转换为知识图谱注入格式：
- entity → {name, entityType, observations}
- relation → {from, to, relationType}
- 只转换 confidence >= threshold 的项
"""


class KGInjector:
    """知识图谱注入格式转换器"""

    def __init__(self, confidence_threshold: float = 0.3):
        """
        Args:
            confidence_threshold: 最低置信度阈值
        """
        self.confidence_threshold = confidence_threshold

    def convert(self, extractions: list[dict], relations: list[dict] = None) -> dict:
        """
        转换为 KG 注入格式

        Args:
            extractions: 提取项列表
            relations: 关系列表（可选）

        Returns:
            {entities: [...], relations: [...]}
        """
        # 过滤低置信度项
        high_conf_extractions = [
            e for e in extractions
            if e.get('confidence', 0) >= self.confidence_threshold
        ]

        # 转换实体
        entities = []
        for ext in high_conf_extractions:
            if ext.get('type') in ['entity', 'rule', 'constraint', 'event', 'state']:
                entity = self._convert_entity(ext)
                entities.append(entity)

        # 转换关系
        kg_relations = []

        # 从 extractions 中提取显式关系
        for ext in high_conf_extractions:
            if ext.get('type') == 'relation':
                relation = self._convert_relation(ext)
                kg_relations.append(relation)

        # 添加推断关系
        if relations:
            for rel in relations:
                if rel.get('confidence', 0) >= self.confidence_threshold:
                    relation = self._convert_relation(rel)
                    kg_relations.append(relation)

        return {
            "entities": entities,
            "relations": kg_relations,
        }

    def _convert_entity(self, ext: dict) -> dict:
        """
        转换单个实体

        Args:
            ext: 提取项

        Returns:
            {name, entityType, observations}
        """
        # 生成实体名称
        name = self._make_name(ext)

        # 实体类型
        entity_type = ext.get('type', 'entity')

        # 构建 observations
        observations = []

        # 1. 中文摘要
        summary_cn = ext.get('summary_cn')
        if summary_cn:
            observations.append(summary_cn)

        # 2. 源位置
        loc = ext.get('source_location', {})
        source_file = ext.get('source_file', 'unknown')
        line = loc.get('line')
        if line:
            observations.append(f"Source: {source_file}:{line}")

        # 3. 置信度
        confidence = ext.get('confidence')
        if confidence is not None:
            observations.append(f"Confidence: {confidence:.2f}")

        # 4. 特定属性
        for key in ['trigger_context', 'consequence', 'reason']:
            value = ext.get(key)
            if value:
                observations.append(f"{key}: {value}")

        # 5. 原始文本 (如果没有摘要)
        if not summary_cn:
            text = ext.get('text', '')[:100]
            if text:
                observations.append(f"Text: {text}")

        return {
            "name": name,
            "entityType": entity_type,
            "observations": observations,
        }

    def _convert_relation(self, rel: dict) -> dict:
        """
        转换关系

        Args:
            rel: 关系项

        Returns:
            {from, to, relationType}
        """
        return {
            "from": rel.get('from', ''),
            "to": rel.get('to', ''),
            "relationType": rel.get('relation_type', 'relates_to'),
        }

    def _make_name(self, ext: dict) -> str:
        """
        生成实体名称

        优先级:
        1. summary_cn 前50字符
        2. text 前50字符

        Args:
            ext: 提取项

        Returns:
            实体名称
        """
        summary_cn = ext.get('summary_cn', '')
        if summary_cn:
            return summary_cn[:50]

        text = ext.get('text', '')
        if text:
            # 去除换行和多余空白
            cleaned = ' '.join(text.split())
            return cleaned[:50]

        # 兜底
        return f"Entity_{id(ext)}"


if __name__ == "__main__":
    # 测试示例
    extractions = [
        {
            "type": "entity",
            "text": "MGMultiGateSolver",
            "summary_cn": "倍增门解算器",
            "confidence": 0.85,
            "source_file": "MGMultiGate.cs",
            "source_location": {"line": 42}
        },
        {
            "type": "rule",
            "text": "禁止直接修改 NativeArray",
            "summary_cn": "NativeArray 只读保护",
            "trigger_context": "修改解算器数据时",
            "consequence": "崩溃或数据损坏",
            "confidence": 0.92,
            "source_file": "solver-readonly.md",
            "source_location": {"line": 15}
        },
        {
            "type": "entity",
            "text": "LowConfidenceEntity",
            "confidence": 0.2,  # 低于阈值，不会被转换
        },
    ]

    relations = [
        {
            "from": "倍增门解算器",
            "to": "NativeArray 只读保护",
            "relation_type": "governed_by",
            "confidence": 0.6,
        }
    ]

    injector = KGInjector(confidence_threshold=0.3)
    result = injector.convert(extractions, relations)

    import json
    print(f"转换了 {len(result['entities'])} 个实体, {len(result['relations'])} 条关系")
    print(json.dumps(result, indent=2, ensure_ascii=False))
