from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api.admin import admin_router
from app.api.user import user_router


app = FastAPI(
    title="Portfolios Market API",
    description="API for tickers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# Подключаем роутеры
app.include_router(user_router)
app.include_router(admin_router)


# Статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")


# Добавляем headers для кэширования
@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=31536000"  # 1 год
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
