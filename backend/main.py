from fastapi import FastAPI
from routers import auth, tasks, files
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import database

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Sunucu başlıyor... Veritabanı kontrol ediliyor...")
    database.init_db()
    yield
    print("Sunucu kapanıyor...")

app=FastAPI(title="Task Manager API", docs_url = "/docs", lifespan=lifespan)

origins= [
    "http://localhost",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    
]

app.add_middleware(
    CORSMiddleware,
    allow_origins= origins,
    allow_credentials=True,
    allow_methods= ["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(files.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Task Management API"}