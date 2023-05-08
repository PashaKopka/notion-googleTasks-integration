import datetime
import os
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import (
    GOOGLE_CLIENT_SECRET_FILE, GOOGLE_API_NAME,
    GOOGLE_API_VERSION, GOOGLE_API_SCOPES, GOOGLE_TASK_LIST_ID
)
from google_tasks.google_utils import GoogleTaskStatus


class GoogleTaskList:
    GOOGLE_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

    def __init__(
        self,
        task_list_id: str,
        secret_file_path: str = GOOGLE_CLIENT_SECRET_FILE,
        api_name: str = GOOGLE_API_NAME,
        api_version: str = GOOGLE_API_VERSION,
        scopes: list[str] = GOOGLE_API_SCOPES,
    ) -> None:
        if not os.path.exists(secret_file_path):
            raise FileNotFoundError(f'File {secret_file_path} not found')

        self._secret_file_path = secret_file_path
        self._api_name = api_name
        self._api_version = api_version
        self._scopes = scopes
        self._cred = None
        self._pickle_file = f'token_{self._api_name}_{self._api_version}.pickle'
        self._list_id = task_list_id
        self._notion_ids = []

        self._create_google_connect()

    def _update_notion_ids(func):  # TODO remove this!
        def wrapper(self, *args, **kwargs):
            self._notion_ids = self.get_notion_ids()
            result = func(self, *args, **kwargs)
            return result
        return wrapper

    def _create_google_connect(self) -> None:
        # TODO finish it
        if os.path.exists(self._pickle_file):
            with open(self._pickle_file, 'rb') as token:
                self._cred = pickle.load(token)

        if not self._cred or not self._cred.valid:
            if self._cred and self._cred.expired and self._cred.refresh_token:
                self._cred.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._secret_file_path, self._scopes
                )
                self._cred = flow.run_local_server()
            print(self._pickle_file)
            with open(self._pickle_file, 'wb') as token:
                pickle.dump(self._cred, token)

        try:
            self.connect = build(
                self._api_name, self._api_version, credentials=self._cred)
        except Exception as e:
            print(f'Failed to create service instance for {self._api_name}')
            os.remove(self._pickle_file)
            raise e

    def get_all_tasks(self, with_completed: bool = True, show_hidden: bool = True):
        data = self.connect.tasks().list(
            tasklist=self._list_id,
            showCompleted=with_completed,
            showHidden=show_hidden
        ).execute()['items']

        res = {}
        for task in data:
            res[task['id']] = self._parse_task_data(task)

        return res

    def get_task(self, task_id: str):
        task = self.connect.tasks().get(
            tasklist=self._list_id,
            task=task_id
        ).execute()
        return self._parse_task_data(task)

    def _parse_task_data(self, task: dict) -> dict:
        return {
            'id': task['id'],
            'title': task['title'],
            'notes': task.get('notes'),
            'updated': datetime.datetime.strptime(task['updated'], self.GOOGLE_TIME_FORMAT),
            'status': GoogleTaskStatus(task['status']),
            'due': datetime.datetime.strptime(task['due'], self.GOOGLE_TIME_FORMAT) if 'due' in task else '',
        }

    def update_task(self, task_id: str, data: dict) -> None:
        self.connect.tasks().update(
            tasklist=self._list_id,
            task=task_id,
            body=data
        ).execute()

    def add_task(self, data: dict) -> str:
        res = self.connect.tasks().insert(
            tasklist=self._list_id,
            body=data
        ).execute()
        return res['id']

    def __getitem__(self, task_id):
        return self.get_task(task_id)

    def get_not_synced_tasks(self):
        tasks = self.get_all_tasks()
        return {task_id: task for task_id, task in tasks.items() if not task['notes']}


if __name__ == '__main__':
    g_tasks = GoogleTaskList(
        GOOGLE_TASK_LIST_ID,
        GOOGLE_CLIENT_SECRET_FILE,
        GOOGLE_API_NAME,
        GOOGLE_API_VERSION,
        GOOGLE_API_SCOPES
    )
    data = g_tasks.get_tasks()
    print(data)
