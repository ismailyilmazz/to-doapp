from fastapi import FastAPI
from routers import auth, tasks
from fastapi.middleware.cors import CORSMiddleware

app=FastAPI(title="Task Manager API", docs_url = "/docs")

origins= [
    "http://localhost",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
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

@app.get("/")
def read_root():
    return {"message": "Welcome to the Task Management API"}