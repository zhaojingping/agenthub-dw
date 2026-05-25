import hashlib
import json
from datetime import datetime
from typing import Optional

import httpx

from src.services.base_collector import BaseCollector, CollectedItem


class NewsCollector(BaseCollector):
    """新闻网站数据采集器"""

    @property
    def source_type(self) -> str:
        return "news"

    async def collect(
        self,
        keywords: list[str],
        topics: list[str] | None = None,
        competitors: list[str] | None = None,
        since: datetime | None = None,
    ) -> list[CollectedItem]:
        """从新闻网站采集数据"""
        items = []
        all_keywords = keywords + (topics or []) + (competitors or [])

        # TODO: 接入实际新闻 API（如 NewsAPI、百度新闻等）
        # 这里先实现框架，返回模拟数据
        for keyword in all_keywords[:5]:  # 限制每次采集数量
            item = CollectedItem(
                title=f"[模拟] 关于{keyword}的最新报道",
                content=f"这是一条关于{keyword}的模拟新闻内容，实际接入时需要调用真实 API。",
                url=f"https://example.com/news/{hashlib.md5(keyword.encode()).hexdigest()[:8]}",
                author="模拟记者",
                publish_time=datetime.utcnow(),
                source_name="news_demo",
                metadata={"keyword": keyword},
            )
            items.append(item)

        return items

    async def health_check(self) -> bool:
        """检查新闻 API 是否可用"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # TODO: 替换为实际 API 健康检查
                return True
        except Exception:
            return False


class WeiboCollector(BaseCollector):
    """微博数据采集器"""

    @property
    def source_type(self) -> str:
        return "weibo"

    async def collect(
        self,
        keywords: list[str],
        topics: list[str] | None = None,
        competitors: list[str] | None = None,
        since: datetime | None = None,
    ) -> list[CollectedItem]:
        """从微博采集数据"""
        items = []
        all_keywords = keywords + (topics or []) + (competitors or [])

        # TODO: 接入微博开放平台 API
        for keyword in all_keywords[:5]:
            item = CollectedItem(
                title=f"[模拟] 微博热议：{keyword}",
                content=f"微博上关于{keyword}的讨论正在升温，实际接入时需要调用微博 API。",
                url=f"https://weibo.com/search?q={keyword}",
                author="微博用户",
                publish_time=datetime.utcnow(),
                source_name="weibo_demo",
                metadata={"keyword": keyword, "platform": "weibo"},
            )
            items.append(item)

        return items

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                return True
        except Exception:
            return False


# 采集器注册表
COLLECTOR_REGISTRY: dict[str, type[BaseCollector]] = {
    "news": NewsCollector,
    "weibo": WeiboCollector,
}


def get_collector(source_type: str) -> BaseCollector:
    """获取指定类型的采集器"""
    collector_cls = COLLECTOR_REGISTRY.get(source_type)
    if not collector_cls:
        raise ValueError(f"Unsupported data source: {source_type}")
    return collector_cls()


def register_collector(source_type: str, collector_cls: type[BaseCollector]):
    """注册新的采集器插件"""
    COLLECTOR_REGISTRY[source_type] = collector_cls
