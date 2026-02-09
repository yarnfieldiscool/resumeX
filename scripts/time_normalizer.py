"""
Time Normalizer

标准化简历提取结果中的时间格式。
在 Pipeline 中作为 Step 0.5 (Source Grounding 之前) 执行。

规则:
  - "2025 年"     -> "2025.01"  (仅年份补 .01)
  - "2025.9"      -> "2025.09"  (单位月份补零)
  - "Jul 2020"    -> "2020.07"  (英文月份转数字)
  - "2019年7月"   -> "2019.07"  (中文年月转数字)
  - "2020/07"     -> "2020.07"  (斜杠转点号)
  - "至今"/"present" -> 保留原文
"""

import re

# 英文月份映射
MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    "january": "01", "february": "02", "march": "03", "april": "04",
    "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}

# 保留原文的特殊值
PASSTHROUGH = {"至今", "present", "至今在职", "在职", "now", "current"}

# 时间字段名列表
TIME_FIELDS = ("period_start", "period_end", "date", "expiry")


class TimeNormalizer:
    """时间格式标准化器"""

    def normalize(self, value: str) -> str:
        """标准化单个时间值。

        Args:
            value: 原始时间字符串

        Returns:
            标准化后的 YYYY.MM 格式字符串，或原文保留
        """
        if not value or not isinstance(value, str):
            return value

        v = value.strip()

        # 特殊值直接保留
        if v.lower() in {s.lower() for s in PASSTHROUGH}:
            return v

        # 已经是标准格式 YYYY.MM
        if re.match(r"^\d{4}\.\d{2}$", v):
            return v

        # "2025.9" -> "2025.09" (单位月份补零)
        m = re.match(r"^(\d{4})\.(\d)$", v)
        if m:
            return f"{m.group(1)}.{m.group(2).zfill(2)}"

        # "2025 年" 或 "2025年" (仅年份)
        m = re.match(r"^(\d{4})\s*年?$", v)
        if m:
            return f"{m.group(1)}.01"

        # "2019年7月" 或 "2019 年 7 月"
        m = re.match(r"^(\d{4})\s*年\s*(\d{1,2})\s*月?$", v)
        if m:
            return f"{m.group(1)}.{m.group(2).zfill(2)}"

        # "2020/07" or "2020/7"
        m = re.match(r"^(\d{4})/(\d{1,2})$", v)
        if m:
            return f"{m.group(1)}.{m.group(2).zfill(2)}"

        # "Jul 2020" or "July 2020"
        m = re.match(r"^([A-Za-z]+)\s+(\d{4})$", v)
        if m:
            month_str = m.group(1).lower()
            if month_str in MONTH_MAP:
                return f"{m.group(2)}.{MONTH_MAP[month_str]}"

        # "2020-07" (dash separator)
        m = re.match(r"^(\d{4})-(\d{1,2})$", v)
        if m:
            return f"{m.group(1)}.{m.group(2).zfill(2)}"

        # 无法识别则返回原值
        return v

    def process(self, extractions: list[dict]) -> list[dict]:
        """批量标准化提取列表中的时间字段。

        Args:
            extractions: 提取项列表

        Returns:
            时间字段已标准化的提取项列表
        """
        for ext in extractions:
            attrs = ext.get("attributes", {})
            for field in TIME_FIELDS:
                if field in attrs and isinstance(attrs[field], str):
                    attrs[field] = self.normalize(attrs[field])
        return extractions
