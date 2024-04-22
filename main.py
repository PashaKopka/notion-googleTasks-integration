from collections import defaultdict

import google_auth_oauthlib
import requests
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates

from config import (
    GOOGLE_API_SCOPES,
    GOOGLE_CLIENT_SECRET_FILE,
    HOST,
    NOTION_AUTHORIZATION_URL,
    NOTION_OAUTH_CLIENT_ID,
    NOTION_OAUTH_CLIENT_SECRET,
    NOTION_TOKEN_URL,
)
from models.models import SyncingServices, create_tables
from utils.request_crypt import encode, generate_access_token, validate_token
from utils.user_utils import (
    User,
    get_user,
    get_user_by_session_state,
    set_user_by_session_state,
)

app = FastAPI()

templates = Jinja2Templates(directory="templates")

SESSION = defaultdict(dict)

get_user_from_session = get_user_by_session_state(SESSION)
set_user_to_session = set_user_by_session_state(SESSION)


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


def absolute_url_for(url_name: str, base_url: str = HOST):
    redirect_path = app.url_path_for(url_name)
    return redirect_path.make_absolute_url(base_url=base_url)


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "notion_connect_url": app.url_path_for("connect_notion"),
        },
    )


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(email=form_data.username)
    if not user or form_data.password != user.password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = generate_access_token(user)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/notion/")
async def save_notion_connection(
    code: str, user: User = Depends(get_user_from_session)
):
    notion_data = get_notion_data(code)
    services = SyncingServices(
        user_id=user.id,
        service_notion_data=notion_data,
    )
    services.save()
    return RedirectResponse(app.url_path_for("root"))


@app.get("/notion/connect")
def connect_notion(user: User = Depends(validate_token)):
    state = set_user_to_session(user)
    return RedirectResponse(
        f"{NOTION_AUTHORIZATION_URL}&state={state}"
    )  # TODO change to app.url_path_for


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
    credentials = flow.credentials.to_json()

    services = SyncingServices(
        user_id=user.id,
        service_google_tasks_data=credentials,
    )
    services.save()
    return RedirectResponse(app.url_path_for("root"))


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
    return RedirectResponse(authorization_url)


if __name__ == "__main__":
    create_tables()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
