import asyncio
from collections import defaultdict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from config import FRONT_END_HOST
from logger import get_logger
from models.models import create_all_tables
from utils.request_utils import get_user_by_session_state, set_user_by_session_state


async def lifespan(the_app):
    logger.info("Starting application")
    await create_all_tables()
    await restart_sync()
    yield
    logger.info("Shutting down application")


app = FastAPI(lifespan=lifespan)
logger = get_logger(__name__)

SESSION = defaultdict(dict)
redirect_to_home = RedirectResponse(FRONT_END_HOST)


from routes.google_auth import router as google_auth_router
from routes.notion_auth import router as notion_auth_router
from routes.sync import restart_sync
from routes.sync import router as sync_router
from routes.user import router as user_router

app.include_router(notion_auth_router, prefix="/notion")
app.include_router(google_auth_router, prefix="/google_tasks")
app.include_router(sync_router, prefix="/sync")
app.include_router(user_router, prefix="/user")

origins = [
    "http://localhost",
    FRONT_END_HOST,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

get_user_from_session = get_user_by_session_state(SESSION)
set_user_to_session = set_user_by_session_state(SESSION)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
