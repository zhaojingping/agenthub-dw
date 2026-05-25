import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import async_session_factory
from src.models.monitoring import MonitorTask, MonitorTaskStatus
from src.services.collectors import get_collector
from src.services.sentiment import sentiment_analyzer
from src.services.smart_filter import SmartFilter

logger = logging.getLogger(__name__)


class MonitorScheduler:
    """7x24 实时监测调度器"""

    def __init__(self):
        self._tasks: dict[int, asyncio.Task] = {}
        self._running = False

    async def start(self):
        """启动调度器"""
        self._running = True
        logger.info("Monitor scheduler started")
        await self._schedule_all_active_tasks()

    async def stop(self):
        """停止调度器"""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
        logger.info("Monitor scheduler stopped")

    async def _schedule_all_active_tasks(self):
        """调度所有活跃任务"""
        async with async_session_factory() as db:
            stmt = select(MonitorTask).where(
                MonitorTask.status == MonitorTaskStatus.ACTIVE,
                MonitorTask.is_active == True,
            )
            result = await db.execute(stmt)
            tasks = result.scalars().all()

        for task in tasks:
            await self._schedule_task(task)

    async def _schedule_task(self, task: MonitorTask):
        """调度单个任务"""
        if task.id in self._tasks:
            self._tasks[task.id].cancel()

        async def run_loop():
            while self._running:
                try:
                    await self._execute_task(task.id)
                except Exception as e:
                    logger.error(f"Error executing task {task.id}: {e}")
                await asyncio.sleep(task.interval_seconds)

        self._tasks[task.id] = asyncio.create_task(run_loop())
        logger.info(f"Scheduled task {task.id} ({task.name}) with interval {task.interval_seconds}s")

    async def _execute_task(self, task_id: int):
        """执行单次采集任务"""
        async with async_session_factory() as db:
            stmt = select(MonitorTask).where(MonitorTask.id == task_id)
            result = await db.execute(stmt)
            task = result.scalar_one_or_none()
            if not task:
                return

            logger.info(f"Executing task {task.id}: {task.name}")

            collected = 0
            stored = 0

            for source_type in task.data_sources:
                try:
                    collector = get_collector(source_type)
                    items = await collector.collect(
                        keywords=task.keywords,
                        topics=task.topics,
                        competitors=task.competitors,
                    )
                    collected += len(items)

                    # Analyze sentiment
                    sentiment_results = []
                    for item in items:
                        sentiment = await sentiment_analyzer.analyze_item(item)
                        sentiment_results.append(sentiment)

                    # Smart filter
                    smart_filter = SmartFilter(db)
                    filtered_items = await smart_filter.filter_and_score(items, sentiment_results)

                    # Store
                    from src.models.monitoring import Mention, SentimentType, DataSourceType
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
                        )
                        db.add(mention)
                        stored += 1

                    await db.commit()
                    logger.info(f"Task {task.id}: collected={collected}, stored={stored}")

                except Exception as e:
                    logger.error(f"Error collecting from {source_type}: {e}")

    async def add_task(self, task: MonitorTask):
        """添加新任务到调度器"""
        await self._schedule_task(task)

    async def remove_task(self, task_id: int):
        """从调度器移除任务"""
        if task_id in self._tasks:
            self._tasks[task_id].cancel()
            del self._tasks[task_id]
            logger.info(f"Removed task {task_id} from scheduler")


# Global scheduler instance
scheduler = MonitorScheduler()
