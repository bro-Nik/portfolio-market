from typing import Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy import (
    String, Float, Integer, DateTime, Text, Boolean, JSON,
    ForeignKey, BigInteger, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Ticker(Base):
    """Тикеры (криптовалюты, акции, валюты)"""
    __tablename__ = "ticker"

    id: Mapped[str] = mapped_column(String(256), primary_key=True, comment="Уникальный идентификатор")
    name: Mapped[str] = mapped_column(String(1024), nullable=False, comment="Название тикера")
    symbol: Mapped[str] = mapped_column(String(124), nullable=False, index=True, comment="Символ тикера")
    image: Mapped[Optional[str]] = mapped_column(String(1024), comment="URL изображения")
    market_cap_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Ранг по капитализации")
    price: Mapped[float] = mapped_column(Float, default=0.0, comment="Текущая цена")
    market: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="Рынок")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="Время последнего обновления")

    __table_args__ = (
        Index('idx_ticker_symbol_market', 'symbol', 'market'),
    )


class ApiService(Base):
    """Внешние API сервисы"""
    __tablename__ = "api_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True, comment="Название сервиса")
    display_name: Mapped[Optional[str]] = mapped_column(String(200), comment="Отображаемое имя")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="Описание сервиса")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="Базовый URL API")
    api_key: Mapped[Optional[str]] = mapped_column(String(500), comment="API ключ")
    api_key_encrypted: Mapped[bool] = mapped_column(Boolean, default=False, comment="Зашифрован ли ключ")

    # Лимиты запросов
    requests_per_minute: Mapped[Optional[int]] = mapped_column(Integer, comment="Лимит запросов в минуту")
    requests_per_hour: Mapped[Optional[int]] = mapped_column(Integer, comment="Лимит запросов в час")
    requests_per_day: Mapped[Optional[int]] = mapped_column(Integer, comment="Лимит запросов в день")
    requests_per_month: Mapped[Optional[int]] = mapped_column(Integer, comment="Лимит запросов в месяц")

    # Текущие счетчики
    minute_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Счетчик за минуту")
    hour_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Счетчик за час")
    day_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Счетчик за день")
    month_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Счетчик за месяц")

    # Время сброса счетчиков
    last_minute_reset: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="Время сброса минутного счетчика")
    last_hour_reset: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="Время сброса часового счетчика")
    last_day_reset: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="Время сброса дневного счетчика")
    last_month_reset: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="Время сброса месячного счетчика")

    # Настройки
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True, comment="Активен ли сервис")
    retry_delay: Mapped[int] = mapped_column(Integer, default=60, nullable=False, comment="Задержка повтора (сек)")
    timeout: Mapped[int] = mapped_column(Integer, default=30, nullable=False, comment="Таймаут запроса (сек)")
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False, comment="Максимальное количество попыток")
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False, comment="Приоритет сервиса (0-10)")

    # Метрики
    total_requests: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False, comment="Общее количество запросов")
    successful_requests: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False, comment="Успешные запросы")
    failed_requests: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False, comment="Неудачные запросы")
    avg_response_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, comment="Среднее время ответа (мс)")

    # Системные поля
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, comment="Дата создания")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, onupdate=lambda: datetime.now(timezone.utc), comment="Дата обновления")

    # Связи
    request_logs: Mapped[list["ApiRequestLog"]] = relationship(back_populates="service", cascade="all, delete-orphan")
    tasks: Mapped[list["ScheduledTask"]] = relationship(back_populates="api_service", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_api_services_status', 'is_active', 'priority'),
        Index('idx_api_services_usage', 'minute_counter', 'hour_counter', 'day_counter'),
        {'comment': 'Внешние API сервисы с rate limiting'}
    )


class ApiRequestLog(Base):
    """Лог запросов к API"""
    __tablename__ = "api_request_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    service_id: Mapped[int] = mapped_column(Integer, ForeignKey('api_services.id', ondelete='CASCADE'), nullable=False, index=True, comment="ID сервиса")
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False, comment="Endpoint API")
    method: Mapped[str] = mapped_column(String(10), default='GET', nullable=False, comment="HTTP метод")
    status_code: Mapped[Optional[int]] = mapped_column(Integer, comment="HTTP статус код")
    response_time: Mapped[Optional[float]] = mapped_column(Float, comment="Время ответа в секундах")
    response_size: Mapped[Optional[int]] = mapped_column(Integer, comment="Размер ответа в байтах")

    # Статус запроса
    was_successful: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="Успешен ли запрос")
    error_type: Mapped[Optional[str]] = mapped_column(String(100), comment="Тип ошибки")
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="Сообщение об ошибке")
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, comment="Детали ошибки")

    # Данные запроса
    request_url: Mapped[str] = mapped_column(Text, nullable=False, comment="Полный URL запроса")
    request_headers: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, comment="Заголовки запроса")
    request_params: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, comment="Параметры запроса")
    request_body: Mapped[Optional[str]] = mapped_column(Text, comment="Тело запроса")

    # Данные ответа
    response_headers: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, comment="Заголовки ответа")
    response_body_preview: Mapped[Optional[str]] = mapped_column(Text, comment="Препью тела ответа")
    response_content_type: Mapped[Optional[str]] = mapped_column(String(200), comment="Content-Type ответа")

    # Связь с задачами
    task_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, comment="ID задачи Celery")
    scheduled_task_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('scheduled_tasks.id', ondelete='SET NULL'), index=True, comment="ID запланированной задачи")

    # Системные поля
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, comment="Дата создания")

    # Связи
    service: Mapped["ApiService"] = relationship(back_populates="request_logs")
    scheduled_task: Mapped[Optional["ScheduledTask"]] = relationship(back_populates="request_logs")

    __table_args__ = (
        Index('idx_request_logs_service_time', 'service_id', 'created_at'),
        Index('idx_request_logs_success', 'was_successful', 'created_at'),
        {'comment': 'Логи запросов к внешним API'}
    )


class ScheduledTask(Base):
    """Настроенные задачи"""
    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True, comment="Название задачи")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="Описание задачи")

    # Тип и настройки задачи
    task_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="Тип задачи")
    api_service_id: Mapped[int] = mapped_column(Integer, ForeignKey('api_services.id', ondelete='SET NULL'), nullable=False, index=True, comment="Используемый API сервис")

    # Расписание
    schedule: Mapped[str] = mapped_column(String(100), nullable=False, comment="Cron выражение или интервал")
    schedule_type: Mapped[str] = mapped_column(String(20), default='cron', nullable=False, comment="Тип расписания")
    timezone: Mapped[str] = mapped_column(String(50), default='UTC', nullable=False, comment="Часовой пояс")

    # Статус
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True, comment="Активна ли задача")

    # Параметры задачи
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, comment="Параметры задачи")
    task_priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False, comment="Приоритет задачи (0-10)")

    # История выполнения
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="Время последнего запуска")
    last_run_status: Mapped[Optional[str]] = mapped_column(String(50), comment="Статус последнего запуска")
    last_run_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, comment="Результат последнего запуска")
    last_error: Mapped[Optional[str]] = mapped_column(Text, comment="Последняя ошибка")
    total_runs: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False, comment="Всего запусков")
    next_run: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True, comment="Время следующего запуска")

    # Системные поля

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, comment="Дата создания")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, onupdate=lambda: datetime.now(timezone.utc), comment="Дата обновления")
    created_by: Mapped[Optional[str]] = mapped_column(String(100), comment="Создатель")
    updated_by: Mapped[Optional[str]] = mapped_column(String(100), comment="Кто обновил")

    # Связи
    api_service: Mapped[Optional["ApiService"]] = relationship(back_populates="tasks")
    request_logs: Mapped[list["ApiRequestLog"]] = relationship(back_populates="scheduled_task")

    __table_args__ = (
        Index('idx_scheduled_tasks_active', 'is_active', 'next_run'),
        Index('idx_scheduled_tasks_service', 'api_service_id', 'is_active'),
        {'comment': 'Периодические задачи для сбора данных'}
    )
