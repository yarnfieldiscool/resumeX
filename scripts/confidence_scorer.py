"""
Confidence Scoring Module

四维度加权评分系统：
1. match_quality (35%): 匹配质量 (exact/normalized/fuzzy/none)
2. attr_completeness (25%): 属性完整性
3. text_specificity (20%): 文本长度适中性 (10-200字符最佳)
4. type_consistency (20%): 类型一致性
"""


class ConfidenceScorer:
    """置信度评分器"""

    # 权重配置
    WEIGHTS = {
        "match_quality": 0.35,
        "attr_completeness": 0.25,
        "text_specificity": 0.20,
        "type_consistency": 0.20,
    }

    # 匹配类型得分
    MATCH_SCORES = {
        "exact": 1.0,
        "normalized": 0.85,
        "fuzzy": 0.6,
        "none": 0.1,
    }

    def process(self, extractions: list[dict]) -> list[dict]:
        """
        为每个提取项计算综合置信度

        Args:
            extractions: 提取项列表

        Returns:
            添加了 'confidence' 字段的提取列表
        """
        result = []

        for ext in extractions:
            score = self._score(ext)

            ext_copy = ext.copy()
            ext_copy['confidence'] = round(score, 3)
            result.append(ext_copy)

        return result

    def _score(self, ext: dict) -> float:
        """
        计算单个提取项的置信度

        Args:
            ext: 提取项

        Returns:
            综合置信度 [0, 1]
        """
        # 1. 匹配质量
        match_type = ext.get('source_location', {}).get('match_type', 'none')
        match_quality = self.MATCH_SCORES.get(match_type, 0.1)

        # 2. 属性完整性
        attr_completeness = self._calc_attr_completeness(ext)

        # 3. 文本长度适中性
        text_specificity = self._calc_text_specificity(ext)

        # 4. 类型一致性（默认较高）
        type_consistency = self._calc_type_consistency(ext)

        # 加权求和
        score = (
            self.WEIGHTS["match_quality"] * match_quality +
            self.WEIGHTS["attr_completeness"] * attr_completeness +
            self.WEIGHTS["text_specificity"] * text_specificity +
            self.WEIGHTS["type_consistency"] * type_consistency
        )

        return min(1.0, max(0.0, score))

    def _calc_attr_completeness(self, ext: dict) -> float:
        """
        属性完整性评分

        Args:
            ext: 提取项

        Returns:
            完整性得分 [0, 1]
        """
        # 统计关键属性
        key_attrs = ['summary_cn', 'trigger_context', 'consequence', 'reason', 'related_entities']
        has_summary = 1 if ext.get('summary_cn') else 0
        other_attrs = sum(1 for attr in key_attrs[1:] if ext.get(attr))

        # 理想情况: summary + 2个其他属性
        total = has_summary + other_attrs
        return min(1.0, total / 3.0)

    def _calc_text_specificity(self, ext: dict) -> float:
        """
        文本长度适中性评分

        10-200 字符为最佳范围，过短或过长都扣分

        Args:
            ext: 提取项

        Returns:
            适中性得分 [0, 1]
        """
        text = ext.get('text', '')
        length = len(text)

        if length == 0:
            return 0.0

        if 10 <= length <= 200:
            # 最佳范围
            return 1.0
        elif length < 10:
            # 过短，线性扣分
            return length / 10.0
        else:
            # 过长，递减扣分
            # 200 → 1.0, 400 → 0.7, 600 → 0.5, 1000 → 0.3
            return max(0.3, 1.0 - (length - 200) / 800.0)

    def _calc_type_consistency(self, ext: dict) -> float:
        """
        类型一致性评分

        当前简化实现：只要有 type 字段就给高分

        Args:
            ext: 提取项

        Returns:
            一致性得分 [0, 1]
        """
        ext_type = ext.get('type')

        if not ext_type:
            return 0.5

        # 标准类型
        standard_types = ['entity', 'rule', 'constraint', 'event', 'state', 'relation']

        if ext_type in standard_types:
            return 0.9

        # 非标准但有类型
        return 0.7


if __name__ == "__main__":
    # 测试示例
    extractions = [
        {
            "type": "entity",
            "text": "class MLevel",
            "summary_cn": "关卡类",
            "source_location": {"match_type": "exact"},
        },
        {
            "type": "rule",
            "text": "禁止修改 Solver/ 目录下任何文件",
            "summary_cn": "Solver只读保护",
            "trigger_context": "修改 Solver/ 时",
            "consequence": "破坏解算器稳定性",
            "source_location": {"match_type": "normalized"},
        },
        {
            "type": "entity",
            "text": "x",  # 过短
            "source_location": {"match_type": "fuzzy"},
        },
        {
            "type": "entity",
            "text": "a" * 500,  # 过长
            "source_location": {"match_type": "exact"},
        },
    ]

    scorer = ConfidenceScorer()
    result = scorer.process(extractions)

    import json
    for item in result:
        print(f"Type: {item['type']}, Confidence: {item['confidence']:.3f}")
        print(f"  Text: {item['text'][:50]}...")
        print()
