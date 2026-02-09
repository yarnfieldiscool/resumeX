"""
Source Grounding Module

三级匹配策略将LLM提取的文本片段对齐到原始源文件的精确位置：
1. 精确子串匹配 (exact)
2. 去空白规范化匹配 (normalized)
3. difflib序列相似度模糊对齐 (fuzzy)

每个提取项会被标注 char_start, char_end, line, match_type, confidence。
"""

import difflib
import re


class SourceGrounder:
    """将提取文本对齐到源文件精确位置"""

    def __init__(self, source_text: str):
        """
        Args:
            source_text: 原始源文件完整文本
        """
        self.source_text = source_text
        self.lines = source_text.split('\n')

        # 预计算规范化版本 (用于策略2)
        self.normalized = self._normalize(source_text)

        # 构建规范化位置到原始位置的映射
        self._build_offset_map()

    def _normalize(self, text: str) -> str:
        """去除空白字符，保留所有非空白内容"""
        return re.sub(r'\s+', '', text)

    def _build_offset_map(self):
        """构建规范化offset到原始offset的映射"""
        self.norm_to_real = []
        norm_pos = 0

        for real_pos, char in enumerate(self.source_text):
            if not char.isspace():
                self.norm_to_real.append(real_pos)
                norm_pos += 1

    def _normalized_to_real_offset(self, norm_offset: int) -> int:
        """将规范化文本中的offset转换为原始文本offset"""
        if norm_offset < 0:
            return 0
        if norm_offset >= len(self.norm_to_real):
            return len(self.source_text)
        return self.norm_to_real[norm_offset]

    def process(self, extractions: list[dict]) -> list[dict]:
        """
        为每个提取项添加源位置信息

        Args:
            extractions: LLM提取的原始列表，每项需包含 'text' 字段

        Returns:
            添加了 source_location 字段的提取列表
        """
        result = []

        for ext in extractions:
            text = ext.get('text', '')
            if not text:
                # 无文本内容，跳过
                result.append(ext)
                continue

            # 尝试对齐
            location = self._align(text)

            # 添加位置信息
            ext_copy = ext.copy()
            ext_copy['source_location'] = location
            result.append(ext_copy)

        return result

    def _align(self, query: str) -> dict:
        """
        三级对齐策略

        Args:
            query: 待对齐的文本片段

        Returns:
            包含 char_start, char_end, line, match_type, confidence 的字典
        """
        # 策略1: 精确匹配
        pos = self.source_text.find(query)
        if pos != -1:
            return self._make_loc(pos, pos + len(query), "exact", 1.0)

        # 策略2: 规范化匹配
        norm_query = self._normalize(query)
        norm_pos = self.normalized.find(norm_query)
        if norm_pos != -1:
            real_start = self._normalized_to_real_offset(norm_pos)
            real_end = self._normalized_to_real_offset(norm_pos + len(norm_query))
            return self._make_loc(real_start, real_end, "normalized", 0.85)

        # 策略3: 模糊对齐 (使用 SequenceMatcher)
        matcher = difflib.SequenceMatcher(None, query, self.source_text)
        match = matcher.find_longest_match(0, len(query), 0, len(self.source_text))

        if match.size > 0:
            ratio = match.size / len(query)
            if ratio >= 0.3:  # 至少30%匹配
                start = match.b
                end = match.b + match.size
                return self._make_loc(start, end, "fuzzy", ratio * 0.8)

        # 无匹配
        return {
            "char_start": None,
            "char_end": None,
            "line": None,
            "match_type": "none",
            "confidence": 0.1
        }

    def _make_loc(self, start: int, end: int, match_type: str, confidence: float) -> dict:
        """构造位置信息字典"""
        # 计算行号
        line = self.source_text[:start].count('\n') + 1

        return {
            "char_start": start,
            "char_end": end,
            "char_interval": (start, end),
            "line": line,
            "match_type": match_type,
            "confidence": confidence
        }


if __name__ == "__main__":
    # 测试示例
    source = """class MLevel:
    def initialize(self):
        self.actors = []

    def update(self):
        for actor in self.actors:
            actor.tick()
"""

    extractions = [
        {"type": "entity", "text": "class MLevel"},
        {"type": "entity", "text": "self.actors=[]"},  # 规范化匹配
        {"type": "entity", "text": "for actor in actors"},  # 模糊匹配
    ]

    grounder = SourceGrounder(source)
    result = grounder.process(extractions)

    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
