"""文本分块服务 - 智能分块策略"""

import re
from typing import Optional
from app.config import settings


class TextChunker:
    """将长文本切分为适合向量化的片段"""

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> list[str]:
        """
        分块策略：
        1. 先按段落/标题拆分
        2. 对超长段落用滑动窗口二次拆分
        3. 合并过短的片段
        """
        chunk_size = chunk_size or settings.chunk_size
        chunk_overlap = chunk_overlap or settings.chunk_overlap

        if not text or not text.strip():
            return []

        # 第一步：按段落拆分
        paragraphs = TextChunker._split_by_paragraphs(text)

        # 第二步：对超长段落用滑动窗口拆分
        chunks = []
        for para in paragraphs:
            if len(para) <= chunk_size:
                chunks.append(para)
            else:
                sub_chunks = TextChunker._sliding_window(para, chunk_size, chunk_overlap)
                chunks.extend(sub_chunks)

        # 第三步：合并过短的相邻片段
        merged = TextChunker._merge_short_chunks(chunks, chunk_size)

        return [c.strip() for c in merged if c.strip()]

    @staticmethod
    def _split_by_paragraphs(text: str) -> list[str]:
        """按段落和标题拆分"""
        # 先尝试按 Markdown 标题拆分
        sections = re.split(r'\n(?=#{1,3}\s)', text)
        if len(sections) > 1:
            return [s.strip() for s in sections if s.strip()]

        # 按双换行拆分段落
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]

    @staticmethod
    def _sliding_window(text: str, size: int, overlap: int) -> list[str]:
        """滑动窗口分块"""
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + size
            # 尝试在句子边界处断开
            if end < text_len:
                chunk_text = text[start:end]
                # 找最后一个句子结束符
                for sep in ["。", ".", "！", "!", "？", "?", "\n"]:
                    last_sep = chunk_text.rfind(sep)
                    if last_sep > size * 0.5:
                        end = start + last_sep + 1
                        break
            chunks.append(text[start:end])
            start = end - overlap

        return chunks

    @staticmethod
    def _merge_short_chunks(chunks: list[str], target_size: int) -> list[str]:
        """合并过短的相邻片段"""
        if not chunks:
            return []

        merged = []
        buffer = ""

        for chunk in chunks:
            if not buffer:
                buffer = chunk
            elif len(buffer) + len(chunk) + 2 <= target_size:
                buffer = buffer + "\n\n" + chunk
            else:
                merged.append(buffer)
                buffer = chunk

        if buffer:
            merged.append(buffer)

        return merged
