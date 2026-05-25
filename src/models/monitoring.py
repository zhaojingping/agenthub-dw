import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, Enum as SAEnum, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base


class SentimentType(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class MonitorTaskStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


class DataSourceType(str, enum.Enum):
    NEWS = "news"
    WEIBO = "weibo"
    WECHAT = "wechat"
    DOUYIN = "douyin"
    XIAOHONGSHU = "xiaohongshu"
    ZHIHU = "zhihu"
    OTHER = "other"


class AlertStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class MonitorTask(Base):
    """舆情监测任务配置"""
    __tablename__ = "monitor_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    competitors: Mapped[list[str]] = mapped_column(JSON, default=list)
    data_sources: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[MonitorTaskStatus] = mapped_column(
        SAEnum(MonitorTaskStatus), default=MonitorTaskStatus.ACTIVE
    )
    interval_seconds: Mapped[int] = mapped_column(Integer, default=300)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    mentions: Mapped[list["Mention"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class Mention(Base):
    """舆情提及记录"""
    __tablename__ = "mentions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("monitor_tasks.id"), nullable=False)
    source_type: Mapped[DataSourceType] = mapped_column(SAEnum(DataSourceType), nullable=False)
    source_name: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(String(1000))
    author: Mapped[Optional[str]] = mapped_column(String(200))
    publish_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Engagement metrics (for display like "1.2万")
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)

    # AI analysis results
    sentiment: Mapped[Optional[SentimentType]] = mapped_column(SAEnum(SentimentType), index=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float)
    sentiment_confidence: Mapped[Optional[float]] = mapped_column(Float)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    priority_score: Mapped[Optional[float]] = mapped_column(Float)

    # Deduplication
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    # Metadata
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    task: Mapped["MonitorTask"] = relationship(back_populates="mentions")

    __table_args__ = (
        Index("idx_mention_sentiment_collected", "sentiment", "collected_at"),
    )


class Alert(Base):
    """舆情预警记录"""
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("monitor_tasks.id"), nullable=False)
    mention_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mentions.id"))
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))  # low / medium / high / critical
    status: Mapped[AlertStatus] = mapped_column(SAEnum(AlertStatus), default=AlertStatus.PENDING, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    task: Mapped["MonitorTask"] = relationship(back_populates="alerts")
