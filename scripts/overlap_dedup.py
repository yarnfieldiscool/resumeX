"""
Overlap Deduplication Module

按 char_interval 检测重叠提取项并去重：
- 两个提取的字符区间重叠 > 50% → 保留更完整的（属性更多 + 文本更长）
- 返回去重后的列表 + 统计信息
"""


class OverlapDeduplicator:
    """重叠提取项去重器"""

    def __init__(self, overlap_threshold: float = 0.5, type_aware: bool = False):
        """
        Args:
            overlap_threshold: 重叠率阈值 (默认0.5 = 50%)
            type_aware: 类型感知模式 (默认False)。
                        开启后，不同类型的项即使位置重叠也不会被去重。
        """
        self.overlap_threshold = overlap_threshold
        self.type_aware = type_aware

    def process(self, extractions: list[dict]) -> list[dict]:
        """
        去除重叠的提取项

        Args:
            extractions: 包含 source_location.char_interval 的提取列表

        Returns:
            去重后的列表
        """
        if not extractions:
            return []

        # 过滤掉没有有效位置信息的项
        valid = []
        invalid = []

        for ext in extractions:
            loc = ext.get('source_location', {})
            interval = loc.get('char_interval')

            if interval and interval[0] is not None and interval[1] is not None:
                valid.append(ext)
            else:
                # 没有位置信息的保留（不参与去重）
                invalid.append(ext)

        if not valid:
            return invalid

        # 按起始位置排序
        sorted_items = sorted(valid, key=lambda x: x['source_location']['char_interval'][0])

        # 贪心去重
        kept = []
        removed_count = 0

        for item in sorted_items:
            should_keep = True

            for kept_item in kept:
                # type_aware 模式: 不同类型不去重
                if self.type_aware and item.get('type') != kept_item.get('type'):
                    continue

                overlap = self._overlap_ratio(item, kept_item)

                if overlap > self.overlap_threshold:
                    # 发生重叠，比较哪个更好
                    if self._is_better(item, kept_item):
                        # 新项更好，移除旧项
                        kept.remove(kept_item)
                        removed_count += 1
                    else:
                        # 旧项更好，不保留新项
                        should_keep = False
                        removed_count += 1
                        break

            if should_keep:
                kept.append(item)

        # 合并无效位置的项
        return kept + invalid

    def _overlap_ratio(self, a: dict, b: dict) -> float:
        """
        计算两个提取项的重叠率

        Args:
            a, b: 包含 source_location.char_interval 的提取项

        Returns:
            重叠率 [0, 1]
        """
        interval_a = a['source_location']['char_interval']
        interval_b = b['source_location']['char_interval']

        start_a, end_a = interval_a
        start_b, end_b = interval_b

        # 计算重叠区间
        overlap_start = max(start_a, start_b)
        overlap_end = min(end_a, end_b)

        if overlap_start >= overlap_end:
            return 0.0  # 无重叠

        overlap_len = overlap_end - overlap_start
        len_a = end_a - start_a
        len_b = end_b - start_b

        # 相对于较短区间的重叠率
        min_len = min(len_a, len_b)
        if min_len == 0:
            return 0.0

        return overlap_len / min_len

    def _is_better(self, a: dict, b: dict) -> bool:
        """
        判断 a 是否比 b 更好

        优先级:
        1. 属性更多（排除内部字段）
        2. 文本更长
        3. 置信度更高

        Args:
            a, b: 提取项

        Returns:
            True 如果 a 更好
        """
        # 统计有效属性数量（排除 text, source_location, type）
        def count_attrs(ext):
            exclude = {'text', 'source_location', 'type', 'confidence'}
            return len([k for k in ext.keys() if k not in exclude and ext[k]])

        count_a = count_attrs(a)
        count_b = count_attrs(b)

        if count_a != count_b:
            return count_a > count_b

        # 文本长度
        len_a = len(a.get('text', ''))
        len_b = len(b.get('text', ''))

        if len_a != len_b:
            return len_a > len_b

        # 置信度
        conf_a = a.get('confidence', 0)
        conf_b = b.get('confidence', 0)

        return conf_a > conf_b


if __name__ == "__main__":
    # 测试示例
    extractions = [
        {
            "type": "entity",
            "text": "class MLevel",
            "source_location": {"char_interval": (0, 12), "line": 1},
            "summary_cn": "关卡类"
        },
        {
            "type": "entity",
            "text": "MLevel",  # 与第一个重叠
            "source_location": {"char_interval": (6, 12), "line": 1}
        },
        {
            "type": "rule",
            "text": "禁止修改",
            "source_location": {"char_interval": (50, 60), "line": 3}
        },
        {
            "type": "rule",
            "text": "禁止修改配置",  # 与上一个重叠但更完整
            "source_location": {"char_interval": (50, 65), "line": 3},
            "summary_cn": "配置修改禁令"
        },
    ]

    dedup = OverlapDeduplicator(overlap_threshold=0.5)
    result = dedup.process(extractions)

    import json
    print(f"原始: {len(extractions)} 项")
    print(f"去重后: {len(result)} 项")
    print(json.dumps(result, indent=2, ensure_ascii=False))
