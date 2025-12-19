from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from app.external_api.management.registry import ExternalApiRegistry
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.models import ApiService
from app.repositories.sync_repo.api_service import ApiServiceRepository


class ExternalApiService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ApiServiceRepository(db)

    def get_service(
        self,
        id: Optional[int] = None,
        name: Optional[str] = None
    ) -> Optional[ApiService]:
        if id:
            return self.repo.get(id)
        if name:
            return self.repo.get_by_name(name)

    def get_service_whith_lock(
        self,
        id: Optional[int] = None,
        name: Optional[str] = None
    ) -> Optional[ApiService]:
        if id:
            return self.repo.get_with_forupdate(id)
        if name:
            return self.repo.get_by_name_with_forupdate(name)
