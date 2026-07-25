"""本地离线 Embedding 服务 - 基于 sklearn HashingVectorizer"""

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer
import re


class LocalEmbedding:
    """
    使用 sklearn HashingVectorizer 生成文本向量。
    完全离线，无需下载模型，对中文支持良好（字符级 n-gram）。
    """

    def __init__(self, n_features: int = 512, ngram_range=(2, 4)):
        """
        Args:
            n_features: 向量维度（hash 桶数）
            ngram_range: 字符 n-gram 范围，(2,4) 表示 2/3/4-gram
        """
        self.n_features = n_features
        self.vectorizer = HashingVectorizer(
            n_features=n_features,
            analyzer="char_wb",
            ngram_range=ngram_range,
            alternate_sign=False,  # 去掉符号哈希，让余弦相似度更稳定
        )

    @staticmethod
    def _preprocess(text: str) -> str:
        """简单预处理：去除多余空白"""
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def embed_one(self, text: str) -> list[float]:
        """单条文本 → 向量"""
        text = self._preprocess(text)
        vec = self.vectorizer.transform([text])
        arr = vec.toarray()[0].astype(float)
        # L2 归一化，使余弦相似度 = 内积
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量文本 → 向量列表"""
        texts = [self._preprocess(t) for t in texts]
        if not texts:
            return []
        vec = self.vectorizer.transform(texts)
        arr = vec.toarray().astype(float)
        # L2 归一化
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        arr = arr / norms
        return arr.tolist()


# 全局单例
local_embed = LocalEmbedding()
