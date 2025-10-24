from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app import models, database, tickers


app = FastAPI(
    title="Portfolios Market API",
    description="API for tickers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# Подключаем роутеры
app.include_router(tickers.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
