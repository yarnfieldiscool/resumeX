"""
PDF Parser

使用 PyMuPDF (fitz) 将 PDF 简历转换为 Markdown 格式文本。

支持：
- 单栏/双栏布局自动检测
- 中文编码
- 逐页提取，保留段落结构
"""

import re
from pathlib import Path
from typing import List, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


class PdfParser:
    """PDF 文档解析器"""

    # 页面宽度中点比例阈值 - 用于判断是否为双栏布局
    DUAL_COLUMN_THRESHOLD = 0.4

    # 双栏布局中，左右栏 block 数量最小比例
    MIN_COLUMN_RATIO = 0.25

    def __init__(self, prefer_blocks: bool = True):
        """
        Args:
            prefer_blocks: 是否优先使用 block 级别提取（更好处理双栏布局）。
                          设为 False 则始终使用简单文本提取。
        """
        self._prefer_blocks = prefer_blocks

    def parse(self, file_path: str) -> str:
        """解析 PDF 文件，返回 Markdown 格式文本。

        Args:
            file_path: PDF 文件路径。

        Returns:
            Markdown 格式的纯文本内容。

        Raises:
            ImportError: 未安装 PyMuPDF。
            FileNotFoundError: 文件不存在。
            ValueError: 文件不是有效的 PDF。
        """
        if fitz is None:
            raise ImportError(
                "PyMuPDF is required for PDF parsing. "
                "Install it with: pip install PyMuPDF"
            )

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Not a PDF file: {file_path}")

        doc = fitz.open(str(path))
        try:
            pages: List[str] = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                if self._prefer_blocks:
                    text = self._extract_with_blocks(page)
                else:
                    text = self._extract_simple(page)
                if text.strip():
                    pages.append(text)

            raw = "\n\n---\n\n".join(pages) if len(pages) > 1 else (pages[0] if pages else "")
            return self._clean_text(raw)
        finally:
            doc.close()

    def _extract_simple(self, page) -> str:
        """简单文本提取 - 直接获取页面全文。"""
        return page.get_text("text")

    def _extract_with_blocks(self, page) -> str:
        """Block 级别提取 - 处理双栏布局。

        通过分析 text block 的 x 坐标分布，判断是否为双栏布局。
        如果是双栏，先按列分组，再按行排序，确保阅读顺序正确。
        """
        blocks = page.get_text("blocks")
        if not blocks:
            return ""

        # blocks 格式: (x0, y0, x1, y1, text, block_no, block_type)
        # block_type: 0 = text, 1 = image
        text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
        if not text_blocks:
            return ""

        page_width = page.rect.width
        is_dual = self._detect_dual_column(text_blocks, page_width)

        if is_dual:
            return self._merge_dual_column(text_blocks, page_width)
        else:
            # 单栏：按 y 坐标排序
            text_blocks.sort(key=lambda b: (b[1], b[0]))
            return "\n\n".join(b[4].strip() for b in text_blocks)

    def _detect_dual_column(self, blocks: list, page_width: float) -> bool:
        """检测页面是否为双栏布局。

        策略：统计 block 中心点在页面左半部分和右半部分的分布。
        如果两侧都有足够数量的 block，判定为双栏。
        """
        if len(blocks) < 4:
            return False

        mid_x = page_width * 0.5
        left_blocks = [b for b in blocks if (b[0] + b[2]) / 2 < mid_x]
        right_blocks = [b for b in blocks if (b[0] + b[2]) / 2 >= mid_x]

        if not left_blocks or not right_blocks:
            return False

        total = len(blocks)
        left_ratio = len(left_blocks) / total
        right_ratio = len(right_blocks) / total

        return (left_ratio >= self.MIN_COLUMN_RATIO
                and right_ratio >= self.MIN_COLUMN_RATIO)

    def _merge_dual_column(self, blocks: list, page_width: float) -> str:
        """合并双栏布局的文本块。

        先输出左栏内容，再输出右栏内容。
        每栏内部按 y 坐标排序。
        """
        mid_x = page_width * 0.5

        left_blocks = sorted(
            [b for b in blocks if (b[0] + b[2]) / 2 < mid_x],
            key=lambda b: (b[1], b[0])
        )
        right_blocks = sorted(
            [b for b in blocks if (b[0] + b[2]) / 2 >= mid_x],
            key=lambda b: (b[1], b[0])
        )

        parts: List[str] = []
        for b in left_blocks:
            text = b[4].strip()
            if text:
                parts.append(text)

        if left_blocks and right_blocks:
            parts.append("")  # 栏间空行分隔

        for b in right_blocks:
            text = b[4].strip()
            if text:
                parts.append(text)

        return "\n\n".join(parts)

    def _clean_text(self, text: str) -> str:
        """清理提取后的文本。

        - 合并连续空行为最多两个换行
        - 移除行尾空白
        - 修剪首尾空白
        """
        # 移除行尾空白
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
        # 合并 3+ 连续空行为 2 个
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
