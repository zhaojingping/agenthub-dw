from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CollectedItem:
    """采集到的单条数据"""
    title: str
    content: str
    url: Optional[str] = None
    author: Optional[str] = None
    publish_time: Optional[datetime] = None
    source_name: str = ""
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseCollector(ABC):
    """数据采集器基类 - 插件化架构"""

    @property
    @abstractmethod
    def source_type(self) -> str:
        """数据源类型标识"""
        pass

    @abstractmethod
    async def collect(
        self,
        keywords: list[str],
        topics: list[str] | None = None,
        competitors: list[str] | None = None,
        since: datetime | None = None,
    ) -> list[CollectedItem]:
        """
        采集数据

        Args:
            keywords: 关键词列表
            topics: 话题列表
            competitors: 竞品列表
            since: 只采集此时间之后的数据

        Returns:
            采集到的数据列表
        """
        pass

    async def health_check(self) -> bool:
        """检查数据源是否可用"""
        return True
