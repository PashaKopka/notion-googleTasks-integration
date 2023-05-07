import datetime
import os
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import GOOGLE_CLIENT_SECRET_FILE, GOOGLE_API_NAME, GOOGLE_API_VERSION, GOOGLE_API_SCOPES


class GoogleTasks:
    GOOGLE_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
    GOOGLE_TASK_STATUSES = {
        'needsAction': False,
        'completed': True
    }

    def __init__(
        self,
        secret_file_path: str,
        api_name: str,
        api_version: str,
        scopes: list[str]
    ) -> None:
        if not os.path.exists(secret_file_path):
            raise FileNotFoundError(f'File {secret_file_path} not found')

        self._secret_file_path = secret_file_path
        self._api_name = api_name
        self._api_version = api_version
        self._scopes = scopes
        self._cred = None
        self._pickle_file = f'token_{self._api_name}_{self._api_version}.pickle'

        self._create_google_connect()

    def _create_google_connect(self):
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

    # TODO maybe useless, remove
    def convert_to_RFC_datetime(year=1900, month=1, day=1, hour=0, minute=0):
        dt = datetime.datetime(year, month, day, hour,
                               minute, 0, 000).isoformat() + 'Z'
        return dt

    def get_google_task_lists(self):  # TODO
        return self.connect.tasklists().list().execute()

    def get_google_tasks(self, task_list_id, with_completed=True):
        data = self.connect.tasks().list(tasklist=task_list_id,
                                         showCompleted=with_completed, showHidden=True).execute()['items']
        res = {}
        for task in data:
            res[task['id']] = {
                'title': task['title'],
                'notes': task['notes'],
                'updated': datetime.datetime.strptime(task['updated'], self.GOOGLE_TIME_FORMAT),
                'notes': task['notes'],
                'done': self.GOOGLE_TASK_STATUSES[task['status']],
                'due': datetime.datetime.strptime(task['due'], self.GOOGLE_TIME_FORMAT) if 'due' in task else '',
            }

        return res

    def add_task_to_google_task_list(self, task_list_id, title, notes, due=None, status='needsAction', deleted='False'):
        self.connect.tasks().insert(
            tasklist=task_list_id,
            body={
                'title': title,
                'notes': notes,
                'due': due,
                'status': status,
                'deleted': deleted
            }
        ).execute()

    def __getitem__(self, task_list_id):
        return self.get_google_tasks(task_list_id)


if __name__ == '__main__':
    g_tasks = GoogleTasks(
        GOOGLE_CLIENT_SECRET_FILE,
        GOOGLE_API_NAME,
        GOOGLE_API_VERSION,
        GOOGLE_API_SCOPES
    )
    data = g_tasks.get_google_tasks('YTBIeks1amJKQUJLdnVqcg')
    print(data)
