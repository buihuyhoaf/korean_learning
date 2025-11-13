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
        logger.warning("Firebase disabled: GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
        return None

    if not os.path.exists(credentials_path):
        logger.warning("Firebase disabled: credentials file not found at %s", credentials_path)
        return None

    try:
        cred = credentials.Certificate(credentials_path)
        # Log project ID for debugging
        project_id = cred.project_id if hasattr(cred, 'project_id') else None
        
        # Also try to read from JSON directly for comparison
        import json
        try:
            with open(credentials_path, 'r', encoding='utf-8') as f:
                cred_json = json.load(f)
                json_project_id = cred_json.get('project_id')
                logger.info(
                    "Firebase credentials loaded - Project ID from cred: %s, from JSON: %s",
                    project_id,
                    json_project_id
                )
                if project_id != json_project_id:
                    logger.warning(
                        "Project ID mismatch! cred.project_id=%s vs JSON project_id=%s",
                        project_id,
                        json_project_id
                    )
        except Exception as json_exc:
            logger.debug("Could not read JSON for comparison: %s", json_exc)
        
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("✅ Firebase initialized successfully (Project: %s)", project_id)
        
        # Note: Firebase project IDs can have "project-" prefix in service account JSON
        # but google-services.json may show without prefix. Both refer to the same project.
        # The actual project identifier is the same: "korean-learning-474814"
        normalized_project_id = project_id.replace('project-', '') if project_id else None
        expected_project_id = 'korean-learning-474814'
        
        if normalized_project_id != expected_project_id:
            logger.warning(
                "Project ID mismatch detected! "
                "Service account project_id: %s (normalized: %s), "
                "Expected (from Android app): %s. "
                "This may cause PERMISSION_DENIED errors when sending FCM messages.",
                project_id,
                normalized_project_id,
                expected_project_id
            )
        else:
            logger.info(
                "Project ID verified: %s (normalized: %s) matches Android app project",
                project_id,
                normalized_project_id
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to initialize Firebase Admin SDK: %s", exc)
        _firebase_app = None

    return _firebase_app


def get_firebase_app() -> Optional[firebase_admin.App]:
    """Return the initialised Firebase app if available."""
    return _firebase_app


