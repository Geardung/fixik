from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, buckets, health, share

app = FastAPI(title="ae API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ae.tedeshi.ru", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router)
app.include_router(buckets.router)
app.include_router(share.router)
