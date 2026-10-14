from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.routers import api_router
from app.core.redis_connect import redis_connection


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    async with redis_connection() as redis_client:
        fastapi_app.state.redis_client = redis_client
        yield


app = FastAPI(
    title="Freelance Job Aggregator",
    lifespan=lifespan,
)

app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)