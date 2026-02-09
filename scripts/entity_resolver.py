"""
Entity Resolution Module

实体消歧和合并：
- 检测相似实体名称（包含关系 + 编辑距离）
- 贪心聚类，选择最长名称为标准名
- 更新所有引用（relation 中的 from/to）
"""

import difflib


class EntityResolver:
    """实体消歧合并器"""

    def __init__(self, threshold: float = 0.7):
        """
        Args:
            threshold: 相似度阈值 (默认0.7)
        """
        self.threshold = threshold

    def process(self, extractions: list[dict]) -> list[dict]:
        """
        实体去重和引用重写

        Args:
            extractions: 提取项列表

        Returns:
            实体合并后的提取列表
        """
        # 分离实体和非实体
        entities = [e for e in extractions if e.get('type') == 'entity']
        non_entities = [e for e in extractions if e.get('type') != 'entity']

        if len(entities) <= 1:
            return extractions  # 没有足够的实体需要去重

        # 聚类相似实体
        clusters = self._cluster(entities)

        # 构建别名映射表 (旧名 -> 标准名)
        alias_map = self._build_alias_map(clusters)

        # 合并实体：每个簇保留一个代表
        merged_entities = []
        for cluster in clusters:
            representative = max(cluster, key=lambda e: self._canonical_score(e.get('text', '')))
            merged_entities.append(representative)

        # 重写所有引用（relation 的 from/to）
        updated_extractions = self._rewrite_references(extractions, alias_map)

        # 过滤掉被合并的实体
        canonical_names = {e.get('text') for e in merged_entities}
        result = []

        for ext in updated_extractions:
            if ext.get('type') == 'entity':
                if ext.get('text') in canonical_names:
                    result.append(ext)
            else:
                result.append(ext)

        return result

    def _cluster(self, entities: list[dict]) -> list[list[dict]]:
        """
        贪心聚类相似实体

        Args:
            entities: 实体列表

        Returns:
            实体簇列表
        """
        clusters = []
        assigned = set()

        for i, entity in enumerate(entities):
            if i in assigned:
                continue

            # 创建新簇
            cluster = [entity]
            assigned.add(i)

            name_i = entity.get('text', '')

            # 查找相似实体
            for j, other in enumerate(entities):
                if j in assigned or j <= i:
                    continue

                name_j = other.get('text', '')

                if self._similarity(name_i, name_j) >= self.threshold:
                    cluster.append(other)
                    assigned.add(j)

            clusters.append(cluster)

        return clusters

    def _similarity(self, a: str, b: str) -> float:
        """
        计算两个实体名的相似度

        结合:
        1. 包含关系 (子串)
        2. 编辑距离 (SequenceMatcher)

        Args:
            a, b: 实体名

        Returns:
            相似度 [0, 1]
        """
        if not a or not b:
            return 0.0

        # 完全相同
        if a == b:
            return 1.0

        # 包含关系
        if a in b or b in a:
            # 长度越接近，相似度越高
            shorter = min(len(a), len(b))
            longer = max(len(a), len(b))
            return 0.9 * (shorter / longer)

        # 编辑距离
        ratio = difflib.SequenceMatcher(None, a, b).ratio()
        return ratio

    def _build_alias_map(self, clusters: list[list[dict]]) -> dict:
        """
        构建别名映射表

        Args:
            clusters: 实体簇

        Returns:
            {旧名: 标准名}
        """
        alias_map = {}

        for cluster in clusters:
            # 选择最佳名称为标准名 (CamelCase 优先)
            canonical = max(cluster, key=lambda e: self._canonical_score(e.get('text', '')))
            canonical_name = canonical.get('text', '')

            for entity in cluster:
                name = entity.get('text', '')
                if name != canonical_name:
                    alias_map[name] = canonical_name

        return alias_map

    @staticmethod
    def _canonical_score(name: str) -> tuple:
        """
        计算名称的 canonical 优先级分数

        优先级:
        1. 不含空格 (CamelCase/snake_case) 优先
        2. 更长的名称优先

        Args:
            name: 实体名称

        Returns:
            (no_space_bonus, length) 用于 max() 比较
        """
        no_space = 0 if ' ' in name else 1
        return (no_space, len(name))

    def _rewrite_references(self, extractions: list[dict], alias_map: dict) -> list[dict]:
        """
        重写 relation 中的实体引用

        Args:
            extractions: 提取列表
            alias_map: {旧名: 标准名}

        Returns:
            引用更新后的提取列表
        """
        result = []

        for ext in extractions:
            ext_copy = ext.copy()

            # 重写 relation 类型的 from/to
            if ext.get('type') == 'relation':
                from_entity = ext.get('from')
                to_entity = ext.get('to')

                if from_entity in alias_map:
                    ext_copy['from'] = alias_map[from_entity]

                if to_entity in alias_map:
                    ext_copy['to'] = alias_map[to_entity]

            result.append(ext_copy)

        return result


if __name__ == "__main__":
    # 测试示例
    extractions = [
        {"type": "entity", "text": "MLevel", "summary_cn": "关卡"},
        {"type": "entity", "text": "MMultiGateLevel", "summary_cn": "倍增门关卡"},  # 包含 MLevel
        {"type": "entity", "text": "MGLevel", "summary_cn": "简称"},  # 相似
        {"type": "entity", "text": "Actor", "summary_cn": "角色"},
        {"type": "relation", "from": "MGLevel", "to": "Actor", "relation_type": "contains"},
        {"type": "relation", "from": "MLevel", "to": "Actor", "relation_type": "manages"},
    ]

    resolver = EntityResolver(threshold=0.7)
    result = resolver.process(extractions)

    import json
    print("原始实体数:", sum(1 for e in extractions if e['type'] == 'entity'))
    print("合并后实体数:", sum(1 for e in result if e['type'] == 'entity'))
    print(json.dumps(result, indent=2, ensure_ascii=False))
