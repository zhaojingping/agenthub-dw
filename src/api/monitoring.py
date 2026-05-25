from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.db.session import get_db
from src.models.monitoring import (
    MonitorTask,
    MonitorTaskStatus,
    Mention,
    Alert,
    SentimentType,
    DataSourceType,
    AlertStatus,
)
from src.services.collectors import get_collector, COLLECTOR_REGISTRY
from src.services.sentiment import sentiment_analyzer
from src.services.smart_filter import SmartFilter
from src.services.scheduler import scheduler

router = APIRouter()


# ==================== Request/Response Models ====================

class MonitorTaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
    keywords: list[str] = []
    topics: list[str] = []
    competitors: list[str] = []
    data_sources: list[str] = []
    interval_seconds: int = 300


class MonitorTaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[list[str]] = None
    topics: Optional[list[str]] = None
    competitors: Optional[list[str]] = None
    data_sources: Optional[list[str]] = None
    interval_seconds: Optional[int] = None
    status: Optional[MonitorTaskStatus] = None


class MonitorTaskResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    keywords: list[str]
    topics: list[str]
    competitors: list[str]
    data_sources: list[str]
    status: MonitorTaskStatus
    interval_seconds: int
    created_at: datetime

    class Config:
        from_attributes = True


class MentionResponse(BaseModel):
    """舆情列表项 - 匹配设计稿展示"""
    id: int
    task_id: int
    title: str
    source: str  # 显示用，如 "微博"
    publish_time: Optional[datetime]
    sentiment: str  # "正面" / "负面" / "中性"
    view_count: int  # 阅读量，显示如 "1.2万"
    has_action: bool  # 是否需要处理（负面且高优先级）

    class Config:
        from_attributes = True

    @classmethod
    def from_mention(cls, m: Mention):
        sentiment_map = {"positive": "正面", "negative": "负面", "neutral": "中性"}
        source_map = {
            "weibo": "微博", "news": "新闻", "wechat": "微信",
            "zhihu": "知乎", "douyin": "抖音", "xiaohongshu": "小红书",
        }
        return cls(
            id=m.id,
            task_id=m.task_id,
            title=m.title,
            source=source_map.get(m.source_type.value, m.source_name),
            publish_time=m.publish_time or m.collected_at,
            sentiment=sentiment_map.get(m.sentiment.value if m.sentiment else "", "中性"),
            view_count=m.view_count,
            has_action=m.sentiment == SentimentType.NEGATIVE and (m.priority_score or 0) > 0.6,
        )


class MentionDetailResponse(BaseModel):
    """舆情详情"""
    id: int
    task_id: int
    source_type: str
    source_name: str
    title: str
    content: str
    url: Optional[str]
    author: Optional[str]
    publish_time: Optional[datetime]
    collected_at: datetime
    sentiment: Optional[str]
    sentiment_score: Optional[float]
    sentiment_confidence: Optional[float]
    view_count: int
    comment_count: int
    share_count: int
    like_count: int
    keywords: list[str]
    category: Optional[str]
    priority_score: Optional[float]

    class Config:
        from_attributes = True


class CollectRequest(BaseModel):
    task_id: int


class CollectResponse(BaseModel):
    collected: int
    filtered: int
    stored: int


class AlertResponse(BaseModel):
    id: int
    task_id: int
    title: str
    severity: str
    status: AlertStatus
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Dashboard (工作台) ====================

@router.get("/dashboard/overview")
async def get_dashboard_overview(db: AsyncSession = Depends(get_db)):
    """工作台概览数据"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)

    # 今日舆情总数
    today_stmt = select(func.count(Mention.id)).where(Mention.collected_at >= today_start)
    today_result = await db.execute(today_stmt)
    today_total = today_result.scalar() or 0

    # 待处理预警
    pending_stmt = select(func.count(Alert.id)).where(
        Alert.status.in_([AlertStatus.PENDING, AlertStatus.PROCESSING])
    )
    pending_result = await db.execute(pending_stmt)
    pending_alerts = pending_result.scalar() or 0

    # 进行中项目（活跃监测任务）
    active_stmt = select(func.count(MonitorTask.id)).where(
        MonitorTask.status == MonitorTaskStatus.ACTIVE,
        MonitorTask.is_active == True,
    )
    active_result = await db.execute(active_stmt)
    active_projects = active_result.scalar() or 0

    # 本月内容产出
    month_stmt = select(func.count(Mention.id)).where(Mention.collected_at >= month_start)
    month_result = await db.execute(month_stmt)
    month_content = month_result.scalar() or 0

    return {
        "today_total": today_total,
        "pending_alerts": pending_alerts,
        "active_projects": active_projects,
        "month_content": month_content,
    }


@router.get("/dashboard/trend")
async def get_dashboard_trend(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """舆情趋势数据（近 N 天）"""
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    stmt = select(
        func.date(Mention.collected_at).label("date"),
        Mention.sentiment,
        func.count(Mention.id).label("count"),
    ).where(
        Mention.collected_at >= start,
        Mention.collected_at <= end,
    ).group_by(
        func.date(Mention.collected_at),
        Mention.sentiment,
    ).order_by(
        func.date(Mention.collected_at),
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Build trend data
    trend = {}
    for row in rows:
        date_str = row.date.isoformat()
        if date_str not in trend:
            trend[date_str] = {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
        sentiment = row.sentiment.value if row.sentiment else "neutral"
        trend[date_str][sentiment] = row.count
        trend[date_str]["total"] += row.count

    return {"trend": trend}


# ==================== Task CRUD ====================

@router.post("/tasks", response_model=MonitorTaskResponse)
async def create_task(task: MonitorTaskCreate, db: AsyncSession = Depends(get_db)):
    """创建监测任务"""
    for ds in task.data_sources:
        if ds not in COLLECTOR_REGISTRY:
            raise HTTPException(400, f"Unsupported data source: {ds}")

    db_task = MonitorTask(**task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)

    # 加入调度器
    await scheduler.add_task(db_task)
    return db_task


@router.get("/tasks", response_model=list[MonitorTaskResponse])
async def list_tasks(
    status: Optional[MonitorTaskStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    """列出监测任务"""
    stmt = select(MonitorTask)
    if status:
        stmt = stmt.where(MonitorTask.status == status)
    stmt = stmt.order_by(desc(MonitorTask.created_at))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/tasks/{task_id}", response_model=MonitorTaskResponse)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """获取监测任务详情"""
    stmt = select(MonitorTask).where(MonitorTask.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.put("/tasks/{task_id}", response_model=MonitorTaskResponse)
async def update_task(
    task_id: int,
    update: MonitorTaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新监测任务"""
    stmt = select(MonitorTask).where(MonitorTask.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """删除监测任务"""
    stmt = select(MonitorTask).where(MonitorTask.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")
    await db.delete(task)
    await db.commit()
    await scheduler.remove_task(task_id)
    return {"message": "Task deleted"}


# ==================== Mention List (舆情监测列表) ====================

@router.get("/mentions", response_model=list[MentionResponse])
async def list_mentions(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    platform: Optional[DataSourceType] = Query(None, description="平台筛选"),
    sentiment: Optional[SentimentType] = Query(None, description="情感筛选"),
    task_id: Optional[int] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    """
    舆情监测列表 - 匹配设计稿展示
    支持关键词搜索、平台筛选、情感筛选
    """
    stmt = select(Mention)

    if keyword:
        stmt = stmt.where(
            (Mention.title.ilike(f"%{keyword}%")) |
            (Mention.content.ilike(f"%{keyword}%"))
        )
    if platform:
        stmt = stmt.where(Mention.source_type == platform)
    if sentiment:
        stmt = stmt.where(Mention.sentiment == sentiment)
    if task_id:
        stmt = stmt.where(Mention.task_id == task_id)

    stmt = stmt.order_by(desc(Mention.collected_at)).limit(limit).offset(offset)
    result = await db.execute(stmt)
    mentions = result.scalars().all()

    return [MentionResponse.from_mention(m) for m in mentions]


@router.get("/mentions/{mention_id}", response_model=MentionDetailResponse)
async def get_mention_detail(mention_id: int, db: AsyncSession = Depends(get_db)):
    """舆情详情"""
    stmt = select(Mention).where(Mention.id == mention_id)
    result = await db.execute(stmt)
    mention = result.scalar_one_or_none()
    if not mention:
        raise HTTPException(404, "Mention not found")
    return mention


@router.get("/mentions/stats")
async def get_mention_stats(
    task_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """舆情统计（按情感分布）"""
    stmt = select(
        Mention.sentiment,
        func.count(Mention.id).label("count"),
    )
    if task_id:
        stmt = stmt.where(Mention.task_id == task_id)
    stmt = stmt.group_by(Mention.sentiment)
    result = await db.execute(stmt)
    stats = {row.sentiment.value: row.count for row in result if row.sentiment}

    total_stmt = select(func.count(Mention.id))
    if task_id:
        total_stmt = total_stmt.where(Mention.task_id == task_id)
    total_result = await db.execute(total_stmt)
    stats["total"] = total_result.scalar()

    return stats


# ==================== Data Collection ====================

@router.post("/collect", response_model=CollectResponse)
async def trigger_collect(req: CollectRequest, db: AsyncSession = Depends(get_db)):
    """手动触发数据采集"""
    stmt = select(MonitorTask).where(MonitorTask.id == req.task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")

    collected = 0
    stored = 0
    filtered_count = 0

    for source_type in task.data_sources:
        try:
            collector = get_collector(source_type)
            items = await collector.collect(
                keywords=task.keywords,
                topics=task.topics,
                competitors=task.competitors,
            )
            collected += len(items)

            sentiment_results = []
            for item in items:
                sentiment = await sentiment_analyzer.analyze_item(item)
                sentiment_results.append(sentiment)

            smart_filter = SmartFilter(db)
            filtered_items = await smart_filter.filter_and_score(items, sentiment_results)
            filtered_count += len(items) - len(filtered_items)

            for fi in filtered_items:
                item = fi["item"]
                sentiment = fi["sentiment"]
                mention = Mention(
                    task_id=task.id,
                    source_type=DataSourceType(source_type),
                    source_name=item.source_name,
                    title=item.title,
                    content=item.content,
                    url=item.url,
                    author=item.author,
                    publish_time=item.publish_time,
                    sentiment=SentimentType(sentiment["sentiment"]),
                    sentiment_score=sentiment["score"],
                    sentiment_confidence=sentiment["confidence"],
                    keywords=sentiment["keywords"],
                    priority_score=fi["priority_score"],
                    content_hash=fi["content_hash"],
                    metadata=item.metadata,
                    view_count=item.metadata.get("view_count", 0),
                    comment_count=item.metadata.get("comment_count", 0),
                    share_count=item.metadata.get("share_count", 0),
                    like_count=item.metadata.get("like_count", 0),
                )
                db.add(mention)
                stored += 1

                # 自动创建预警（负面高优先级）
                if sentiment["sentiment"] == "negative" and fi["priority_score"] > 0.6:
                    alert = Alert(
                        task_id=task.id,
                        title=item.title,
                        content=item.content,
                        severity="high" if fi["priority_score"] > 0.8 else "medium",
                        status=AlertStatus.PENDING,
                    )
                    db.add(alert)

        except Exception as e:
            print(f"Error collecting from {source_type}: {e}")

    await db.commit()
    return CollectResponse(collected=collected, filtered=filtered_count, stored=stored)


# ==================== Alerts (预警管理) ====================

@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    status: Optional[AlertStatus] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """预警列表"""
    stmt = select(Alert)
    if status:
        stmt = stmt.where(Alert.status == status)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    stmt = stmt.order_by(desc(Alert.created_at)).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    notes: Optional[str] = None,
    resolved_by: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """处理预警"""
    stmt = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")

    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = resolved_by
    alert.notes = notes
    await db.commit()
    return {"message": "Alert resolved"}
