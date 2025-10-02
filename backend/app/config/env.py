from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv


_DOTENV_LOADED = False


def load_env(dotenv_path: Optional[str] = None) -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    # Load from provided path or default search
    load_dotenv(dotenv_path, override=False)
    _DOTENV_LOADED = True


def get_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    user = os.getenv("DB_USER", os.getenv("USER", "client"))
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "hom")
    auth = f"{user}:{password}@" if password else f"{user}@"
    return f"postgresql://{auth}{host}:{port}/{name}"


def get_paycom_env() -> tuple[str, str, Optional[str]]:
    sid = os.getenv("PAYCOM_SID")
    token = os.getenv("PAYCOM_TOKEN")
    base_url = os.getenv("PAYCOM_BASE_URL")
    return sid or "", token or "", base_url


