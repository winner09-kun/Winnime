import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.database import Base, engine
from .core.config import config
from .api import router
from .wajik import router as wajik_router

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(message)s')

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield

app = FastAPI(title='WINNIME API', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.allowed_origins, allow_methods=['GET','POST','PATCH','DELETE'], allow_headers=['Content-Type'])
app.include_router(router)
app.include_router(wajik_router)
