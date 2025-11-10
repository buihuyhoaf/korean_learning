import logging
import os
from typing import Optional

import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger(__name__)

_firebase_app: Optional[firebase_admin.App] = None


def init_firebase() -> Optional[firebase_admin.App]:
    """Initialise Firebase Admin SDK if credentials are available."""
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        logger.warning(
            "Firebase disabled: GOOGLE_APPLICATION_CREDENTIALS environment variable not set."
        )
        return None

    try:
        cred = credentials.Certificate(credentials_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("✅ Firebase initialized successfully")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to initialize Firebase Admin SDK: %s", exc)
        _firebase_app = None

    return _firebase_app


def get_firebase_app() -> Optional[firebase_admin.App]:
    """Return the initialised Firebase app if available."""
    return _firebase_app


