import asyncio
import json
from collections import defaultdict

import google_auth_oauthlib
import requests
from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates

from config import (
    FRONT_END_HOST,
    GOOGLE_API_SCOPES,
    GOOGLE_CLIENT_SECRET_FILE,
    HOST,
    NOTION_AUTHORIZATION_URL,
    NOTION_OAUTH_CLIENT_ID,
    NOTION_OAUTH_CLIENT_SECRET,
    NOTION_TITLE_PROP_NAME,
    NOTION_TOKEN_URL,
)
from models.models import SyncingServices, create_tables
from services.google_tasks.google_tasks import GTasksList
from services.google_tasks.google_tasks_profiler import GTasksProfiler
from services.notion.notion_db import NotionDB
from services.notion.notion_profiler import NotionProfiler
from synchronizer import NotionTasksSynchronizer
from utils.request_crypt import encode, generate_access_token, validate_token
from utils.user_utils import (
    User,
    get_user,
    get_user_by_session_state,
    set_user_by_session_state,
)

app = FastAPI()

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


templates = Jinja2Templates(directory="templates")

SESSION = defaultdict(dict)

get_user_from_session = get_user_by_session_state(SESSION)
set_user_to_session = set_user_by_session_state(SESSION)

redirect_to_home = RedirectResponse(FRONT_END_HOST)


def get_notion_data(code: str):
    encoded_credentials = encode(
        f"{NOTION_OAUTH_CLIENT_ID}:{NOTION_OAUTH_CLIENT_SECRET}"
    )
    response = requests.post(
        NOTION_TOKEN_URL,
        data={
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": f"{HOST}/notion/",
        },
        headers={
            "Authorization": f"Basic {encoded_credentials}",
        },
    )
    return response.json()


def get_google_task_data(credentials):
    return json.loads(credentials.to_json())


def absolute_url_for(url_name: str, base_url: str = HOST):
    redirect_path = app.url_path_for(url_name)
    return redirect_path.make_absolute_url(base_url=base_url)


async def start_sync_notion_google_tasks(
    syncing_service_id: str, notion_data: dict, google_data: dict
):
    notion_db = NotionDB(
        syncing_service_id=syncing_service_id,
        database_id=notion_data["duplicated_template_id"],
        token=notion_data["access_token"],
        title_prop_name="Name",  # TODO add some kinda of config for user to choose
    )
    google_tasks = GTasksList(
        syncing_service_id=syncing_service_id,
        client_config=google_data,
        tasks_list_id="YTBIeks1amJKQUJLdnVqcg",
    )
    syncer = NotionTasksSynchronizer(
        notion_service=notion_db,
        google_tasks_service=google_tasks,
    )
    while True:
        await syncer.sync()
        await asyncio.sleep(10)


@app.get("/test")
async def test_():
    services = SyncingServices.get_ready_services()
    for service in services:
        notion_data = service.service_notion_data
        google_data = service.service_google_tasks_data
        asyncio.create_task(
            start_sync_notion_google_tasks(
                syncing_service_id=service.id,
                notion_data=notion_data,
                google_data=google_data,
            )
        )

    return {}


@app.get("/user_data")
def get_user_data(user: User = Depends(validate_token)):
    syncing_service = SyncingServices.get_service_by_user_id(user.id)
    notion_profiler = NotionProfiler(
        syncing_service.service_notion_data["access_token"],
    )
    google_tasks_profiler = GTasksProfiler(
        syncing_service.service_google_tasks_data,
    )
    lists = google_tasks_profiler.get_lists()
    dbs = notion_profiler.get_lists()
    return {
        "username": user.email,
        "is_syncing_service_ready": syncing_service.ready,
        "options": {
            "notion": {
                "is_connected": syncing_service.service_notion_data is not None,
                "chosed_list": syncing_service.service_notion_data[
                    "duplicated_template_id"
                ],
                "title_prop_name": syncing_service.service_notion_data.get(
                    "title_prop_name"
                ),
                "available_lists": dbs,
            },
            "google_tasks": {
                "is_connected": syncing_service.service_google_tasks_data is not None,
                "available_lists": lists,
                "chosed_list": syncing_service.service_google_tasks_data.get(
                    "tasks_list_id"
                ),
            },
        },
    }


@app.post("/user_data")
def save_user_data(
    request: Request,
    user: User = Depends(validate_token),
    google_tasks_list_id: str = Body(None),
    notion_list_id: str = Body(None),
    notion_title_prop_name: str = Body(None),
):
    syncing_service = SyncingServices.get_service_by_user_id(user.id)
    if google_tasks_list_id:
        syncing_service.service_google_tasks_data["tasks_list_id"] = (
            google_tasks_list_id
        )
    if notion_list_id:
        syncing_service.service_notion_data["duplicated_template_id"] = notion_list_id
    if notion_title_prop_name:
        syncing_service.service_notion_data["title_prop_name"] = notion_title_prop_name

    syncing_service.update()

    return {"status": "ok"}


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(email=form_data.username)
    if not user or form_data.password != user.password:
        # TODO change to hashed password
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token, expired_in = generate_access_token(user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expired_in": expired_in,
    }


@app.get("/notion/")
async def save_notion_connection(
    code: str, user: User = Depends(get_user_from_session)
):
    notion_data = get_notion_data(code)
    notion_data["title_prop_name"] = NOTION_TITLE_PROP_NAME
    services = SyncingServices(
        user_id=user.id,
        service_notion_data=notion_data,
    )
    services.save()
    return redirect_to_home


@app.get("/notion/connect")
def connect_notion(user: User = Depends(validate_token)):
    state = set_user_to_session(user)
    return {f"{NOTION_AUTHORIZATION_URL}&state={state}"}


@app.get("/google_tasks/")
async def save_google_connection(
    state: str,
    code: str,
    scope: str,
    request: Request,
    user: User = Depends(get_user_from_session),
):
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRET_FILE, scopes=[scope], state=state
    )
    redirect_path = app.url_path_for("save_google_connection")
    flow.redirect_uri = str(redirect_path.make_absolute_url(base_url=HOST))
    authorization_response = "https://" + str(request.url)[7:]
    flow.fetch_token(authorization_response=authorization_response)
    credentials = get_google_task_data(flow.credentials)

    services = SyncingServices(
        user_id=user.id,
        service_google_tasks_data=credentials,
    )
    services.save()
    return redirect_to_home


@app.get("/google_tasks/connect")
async def connect_google_tasks(user: User = Depends(validate_token)):
    state = set_user_to_session(user)

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRET_FILE, scopes=GOOGLE_API_SCOPES, state=state
    )
    flow.redirect_uri = absolute_url_for("save_google_connection")

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
    )
    return {authorization_url}


if __name__ == "__main__":
    create_tables()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
