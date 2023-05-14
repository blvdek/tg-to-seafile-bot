import os

from dotenv import load_dotenv

load_dotenv()

TG_TOKEN: str | None = os.getenv('TG_TOKEN')
SEAFILE_URL: str | None = os.getenv('SEAFILE_URL')
SEAFILE_EMAIL: str | None = os.getenv('SEAFILE_EMAIL')
SEAFILE_PASSWORD: str | None = os.getenv('SEAFILE_PASSWORD')
SEAFILE_REPO: str | None = os.getenv('SEAFILE_REPO')
ALLOWED_IDS: list[int] | None = list(map(int, os.getenv('ALLOWED_IDS').split()))
DEVELOPER_CHAT_ID: str | None = os.getenv('DEVELOPER_CHAT_ID')
