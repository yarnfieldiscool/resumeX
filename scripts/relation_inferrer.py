"""
Relation Inference Module (HR Resume Version)

推断简历中实体之间的语义关系：
- candidate -> experience: worked_at (在某公司工作)
- candidate -> education: studied_at (在某学校就读)
- candidate -> skill: has_skill (拥有某技能)
- candidate -> certification: certified_by (获得某认证)

与原版的区别：
- 原版基于代码行号共现 (scope window) 推断
- HR 版基于提取类型语义关系推断 (不依赖行号)
"""

from typing import Optional


# HR 关系推断规则: extraction_type -> (relation_type, target_name_field)
# target_name_field: 从 attributes 中提取关系目标名称的字段
HR_RELATION_RULES = {
    "experience": ("worked_at", "company"),
    "education": ("studied_at", "school"),
    "skill": ("has_skill", "name"),
    "certification": ("certified_by", "name"),
}


class RelationInferrer:
    """HR 简历关系推断器"""

    def __init__(self, scope_window: int = 50):
        """
        Args:
            scope_window: 保留参数以兼容 pipeline 初始化，HR 版不使用
        """
        self.scope_window = scope_window

    def process(self, extractions: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        推断简历中的实体关系

        遍历所有提取项，找到 candidate 类型作为关系起点，
        将 experience/education/skill/certification 作为关系终点。

        Args:
            extractions: 提取项列表

        Returns:
            (原始 extractions, 推断的 relations 列表)
        """
        # 找到所有 candidate (通常一份简历只有一个)
        candidates = [
            e for e in extractions if e.get("type") == "candidate"
        ]

        if not candidates:
            return extractions, []

        inferred_relations = []

        for candidate in candidates:
            candidate_id = candidate.get("id", "")
            relations = self._infer_for_candidate(
                candidate_id, extractions
            )
            inferred_relations.extend(relations)

        return extractions, inferred_relations

    def _infer_for_candidate(
        self, candidate_id: str, extractions: list[dict]
    ) -> list[dict]:
        """
        为单个候选人推断所有关系

        Args:
            candidate_id: 候选人的 extraction ID (如 ext_001)
            extractions: 全部提取项

        Returns:
            推断的关系列表
        """
        relations = []

        for ext in extractions:
            ext_type = ext.get("type", "")
            ext_id = ext.get("id", "")

            rule = HR_RELATION_RULES.get(ext_type)
            if rule is None:
                continue

            relation_type, name_field = rule
            target_name = self._get_target_name(ext, name_field)

            relations.append({
                "from": candidate_id,
                "to": ext_id,
                "type": relation_type,
                "target_name": target_name,
                "scope": "resume",
                "confidence": self._compute_confidence(ext),
                "inferred": True,
            })

        return relations

    def _get_target_name(self, extraction: dict, field: str) -> str:
        """
        从提取项的 attributes 中获取目标名称

        优先从 attributes 取，回退到 text 字段。

        Args:
            extraction: 提取项
            field: attributes 中的字段名

        Returns:
            目标名称字符串
        """
        attrs = extraction.get("attributes", {})
        name = attrs.get(field, "")
        if name:
            return name

        # 回退: 从 summary_cn 或 text 取
        return extraction.get("summary_cn", extraction.get("text", ""))

    def _compute_confidence(self, extraction: dict) -> float:
        """
        计算关系置信度

        基于提取项自身的置信度衰减。关系置信度 = 提取项置信度 * 0.85
        (关系是推断出来的，总比直接提取低一些)

        Args:
            extraction: 提取项

        Returns:
            关系置信度 [0, 1]
        """
        ext_confidence = extraction.get("confidence", 0.7)
        return round(ext_confidence * 0.85, 3)


if __name__ == "__main__":
    import json

    # HR 测试示例
    extractions = [
        {
            "id": "ext_001",
            "type": "candidate",
            "text": "Zhang San",
            "summary_cn": "Zhang San, Python developer",
            "attributes": {"name": "Zhang San", "phone": "13800138000"},
            "confidence": 0.95,
        },
        {
            "id": "ext_002",
            "type": "experience",
            "text": "ByteDance 2020-2023",
            "summary_cn": "ByteDance senior developer",
            "attributes": {
                "company": "ByteDance",
                "title": "Senior Developer",
                "start_date": "2020-01",
                "end_date": "2023-06",
            },
            "confidence": 0.9,
        },
        {
            "id": "ext_003",
            "type": "education",
            "text": "Peking University CS",
            "summary_cn": "Peking University CS Bachelor",
            "attributes": {
                "school": "Peking University",
                "major": "Computer Science",
                "degree": "Bachelor",
            },
            "confidence": 0.88,
        },
        {
            "id": "ext_004",
            "type": "skill",
            "text": "Python",
            "summary_cn": "Python programming",
            "attributes": {"name": "Python", "category": "programming", "level": "expert"},
            "confidence": 0.85,
        },
        {
            "id": "ext_005",
            "type": "certification",
            "text": "AWS SAA",
            "summary_cn": "AWS Solutions Architect Associate",
            "attributes": {"name": "AWS SAA", "issuer": "Amazon"},
            "confidence": 0.82,
        },
    ]

    inferrer = RelationInferrer()
    _, inferred = inferrer.process(extractions)

    print(f"Inferred {len(inferred)} relations:")
    print(json.dumps(inferred, indent=2, ensure_ascii=False))
