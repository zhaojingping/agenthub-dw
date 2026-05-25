import hashlib
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.monitoring import Mention
from src.services.base_collector import CollectedItem


class SmartFilter:
    """智能过滤服务 - AI 驱动的去重、分类、优先级排序"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def compute_content_hash(self, content: str) -> str:
        """计算内容哈希用于去重"""
        # 使用 SimHash 或 MinHash 可以实现模糊去重
        # 这里先用简单哈希
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    async def is_duplicate(self, content_hash: str, threshold_hours: int = 24) -> bool:
        """检查是否为重复内容"""
        stmt = select(func.count(Mention.id)).where(
            Mention.content_hash == content_hash
        )
        result = await self.db.execute(stmt)
        count = result.scalar()
        return count > 0

    async def compute_priority_score(
        self,
        sentiment_score: float,
        content: str,
        source_type: str,
    ) -> float:
        """
        计算优先级分数

        负面内容、高影响力来源、敏感关键词会获得更高优先级
        """
        score = 0.5  # 基础分

        # 负面内容优先级更高
        if sentiment_score < -0.5:
            score += 0.3
        elif sentiment_score < -0.2:
            score += 0.15

        # 敏感关键词
        sensitive_words = ["危机", "曝光", "投诉", "维权", "违法", "违规"]
        for word in sensitive_words:
            if word in content:
                score += 0.1

        # 限制范围
        return min(1.0, score)

    async def filter_and_score(
        self,
        items: list[CollectedItem],
        sentiment_results: list[dict],
    ) -> list[dict]:
        """
        过滤并评分采集到的数据

        Returns:
            过滤后的数据列表，包含优先级分数
        """
        results = []
        for item, sentiment in zip(items, sentiment_results):
            content_hash = self.compute_content_hash(item.content)

            # 去重检查
            if await self.is_duplicate(content_hash):
                continue

            # 计算优先级
            priority = await self.compute_priority_score(
                sentiment["score"],
                item.content,
                item.source_name,
            )

            results.append({
                "item": item,
                "sentiment": sentiment,
                "content_hash": content_hash,
                "priority_score": priority,
            })

        # 按优先级排序
        results.sort(key=lambda x: x["priority_score"], reverse=True)
        return results
