from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ScheduledTask
from app.dependencies import get_sync_db
from app.services.task_sync import get_next_run_time


class TaskService:
    def get_task(self, db: Session, task_id: int) -> Optional[ScheduledTask]:
        return db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()

    def task_started(self, task_id: int) -> None:
        with get_sync_db() as db:
            task = self.get_task(db, task_id)
            if task:
                self.update_last_run(task)

    def task_completed(self, task_id: int):
        with get_sync_db() as db:
            task = self.get_task(db, task_id)
            if task:
                self.update_next_run(task)

    def update_last_run(self, task: ScheduledTask) -> None:
        if task:
            task.last_run = datetime.now(timezone.utc)

    def update_next_run(self, task: ScheduledTask) -> None:
        if task and task.schedule:
            next_run = get_next_run_time(task.schedule)
            if next_run:
                task.next_run = next_run
                task.updated_at = datetime.now(timezone.utc)
