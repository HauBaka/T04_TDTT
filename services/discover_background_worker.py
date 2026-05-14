import asyncio
from dataclasses import dataclass

from loguru import logger

from repositories.hotel_repo import hotel_repo
from services.sentiment_service import sentiment_service
from services.summary_service import summary_service
from schemas.discover_schema import DiscoverHotel, WeatherInfo


@dataclass(slots=True)
class DiscoverBackgroundJob:
    hotels: list[DiscoverHotel]
    weather_by_identity: dict[str, list[WeatherInfo]]


class DiscoverBackgroundWorker:
    def __init__(self, max_queue_size: int = 100):
        self._queue: asyncio.Queue[DiscoverBackgroundJob] = asyncio.Queue(maxsize=max_queue_size)
        self._worker_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._started = False

    async def start(self):
        if self._started:
            return

        self._stop_event = asyncio.Event()
        self._worker_task = asyncio.create_task(self._run(), name="discover-background-worker")
        self._started = True
        logger.info("Discover background worker started")

    async def stop(self):
        if not self._started:
            return

        self._stop_event.set()
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        self._worker_task = None
        self._started = False
        logger.info("Discover background worker stopped")

    def enqueue(self, hotels: list[DiscoverHotel], weather_by_identity: dict[str, list[WeatherInfo]]):
        if not self._started:
            logger.warning("Discover background worker is not started; dropping background job")
            return False

        job = DiscoverBackgroundJob(
            hotels=hotels,
            weather_by_identity=weather_by_identity,
        )

        try:
            self._queue.put_nowait(job)
            return True
        except asyncio.QueueFull:
            logger.warning("Discover background queue is full; dropping background job")
            return False

    async def _run(self):
        while True:
            if self._stop_event.is_set() and self._queue.empty():
                break

            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            try:
                await sentiment_service.process_places_real_rating(job.hotels)
                await summary_service.process_places_ai_summary(
                    job.hotels,
                    weather_by_identity=job.weather_by_identity,
                )
                await hotel_repo.sync_hotels_background(job.hotels)
            except Exception as exc:
                logger.error(f"Discover background job failed: {str(exc)}")
            finally:
                self._queue.task_done()


discover_background_worker = DiscoverBackgroundWorker()