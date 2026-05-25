from typing import Optional

from src.core.config import get_settings
from src.services.base_collector import CollectedItem


settings = get_settings()


class SentimentAnalyzer:
    """情感分析服务 - AI 驱动"""

    async def analyze(self, text: str) -> dict:
        """
        分析文本情感

        Returns:
            {
                "sentiment": "positive" | "negative" | "neutral",
                "score": float,  # -1.0 to 1.0
                "confidence": float,  # 0.0 to 1.0
                "keywords": list[str],
            }
        """
        # TODO: 接入实际 AI 模型（Qwen / 文心 / OpenAI）
        # 这里先返回模拟结果

        # 简单的关键词启发式分析（临时方案）
        negative_words = ["危机", "负面", "投诉", "问题", "失败", "糟糕", "失望"]
        positive_words = ["好评", "优秀", "成功", "赞", "推荐", "喜欢", "满意"]

        score = 0.0
        for word in negative_words:
            if word in text:
                score -= 0.3
        for word in positive_words:
            if word in text:
                score += 0.3

        # 限制范围
        score = max(-1.0, min(1.0, score))

        if score > 0.2:
            sentiment = "positive"
        elif score < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "score": score,
            "confidence": 0.7,  # 临时固定值
            "keywords": [],
        }

    async def analyze_item(self, item: CollectedItem) -> dict:
        """分析采集到的数据项"""
        text = f"{item.title} {item.content}"
        return await self.analyze(text)


# 全局单例
sentiment_analyzer = SentimentAnalyzer()
