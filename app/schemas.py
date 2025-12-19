from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, validator


class ApiServiceCreate(BaseModel):
    name: str = Field(..., description="Название сервиса (coingecko, binance, etc)")
    base_url: str = Field(..., description="Базовый URL API")
    api_key: Optional[str] = Field(None, description="API ключ")
    requests_per_minute: int = Field(default=30, description="Лимит запросов в минуту")
    requests_per_hour: int = Field(default=1000, description="Лимит запросов в час")
    requests_per_day: int = Field(default=10000, description="Лимит запросов в день")
    requests_per_month: int = Field(default=30000, description="Лимит запросов в месяц")
    retry_delay: int = Field(default=60, description="Задержка повтора при ошибке (сек)")
    timeout: int = Field(default=30, description="Таймаут запроса (сек)")
    is_active: bool = Field(default=True, description="Активен ли сервис")

    @validator('name')
    def validate_name(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Название сервиса может содержать только буквы, цифры, _ и -')
        return v.lower()

    @validator('base_url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL должен начинаться с http:// или https://')
        return v


class ApiServiceUpdate(BaseModel):
    api_key: Optional[str] = None
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    requests_per_day: Optional[int] = None
    requests_per_month: Optional[int] = None
    retry_delay: Optional[int] = None
    timeout: Optional[int] = None
    is_active: Optional[bool] = None


class ApiServiceResponse(BaseModel):
    id: int
    name: str
    base_url: str
    api_key: Optional[str] = None
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    requests_per_day: Optional[int] = None
    requests_per_month: Optional[int] = None
    retry_delay: int
    timeout: int
    is_active: bool
    
    # Текущие счетчики
    minute_counter: int
    hour_counter: int
    day_counter: int
    month_counter: int
    
    # Время последнего сброса
    last_minute_reset: datetime
    last_hour_reset: datetime
    last_day_reset: datetime
    last_month_reset: datetime
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApiServiceStats(BaseModel):
    service_name: str
    requests_today: int
    successful_today: int
    failed_today: int
    avg_response_time: Optional[float]
    minute_counter: int
    minute_limit: int
    hour_counter: int
    hour_limit: int
    day_counter: int
    day_limit: int
    month_counter: int
    month_limit: int
    pending_in_queue: int
    utilization_percent: Dict[str, float]


class TaskCreate(BaseModel):
    name: str
    api_service_id: int
    task_type: str
    schedule: str  # cron выражение, например "0 * * * *" (каждый час)
    is_active: bool = True
    parameters: Dict[str, Any] = {}


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    schedule: Optional[str] = None
    is_active: Optional[bool] = None
    parameters: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    task_type: str
    api_service_id: Optional[int]
    api_service_name: Optional[str] = ''
    schedule: str
    is_active: bool
    parameters: Dict[str, Any]
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class TaskScheduleRequest(BaseModel):
    task_name: str
    schedule: str
    args: Optional[List] = []
    kwargs: Optional[Dict] = {}


class TaskRunRequest(BaseModel):
    task_name: str
    task_id: int
    args: Optional[List] = []
    kwargs: Optional[Dict] = {}


class PriceRequest(BaseModel):
    coin_ids: List[str] = ["bitcoin", "ethereum"]
    currencies: List[str] = ["usd", "eur", "rub"]
