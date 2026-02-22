from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models  # noqa: F401 — ensures ORM metadata is registered before create_all
from database import Base, engine
from routers import classroom, containerlab, topologies

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ae3gis v2 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(topologies.router)
app.include_router(containerlab.router)
app.include_router(classroom.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
