from sqlalchemy.orm import Session

from app import models, schemas
from .base import BaseRepository


class ApiServiceRepository(BaseRepository[models.ApiService, schemas.ApiServiceCreate, schemas.ApiServiceUpdate]):
    def __init__(self, db: Session):
        super().__init__(models.ApiService, db)
