from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app.core.db.database import Base
from src.app.models.user_push_token import UserPushToken
from src.app.services.push_service import FirebaseNotInitializedError, PushSendResult, send_push_notification


@pytest.fixture
async def db_session() -> AsyncSession:
    """Provide an in-memory SQLite session for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


class DummyBatchResponse:
    """Helper to simulate firebase_admin.messaging.BatchResponse."""

    def __init__(self, successes: list[bool], error_codes: list[str | None]):
        self.responses = []
        for success, code in zip(successes, error_codes, strict=False):
            if success:
                self.responses.append(SimpleNamespace(success=True, exception=None))
            else:
                self.responses.append(
                    SimpleNamespace(success=False, exception=SimpleNamespace(code=code))
                )


@pytest.mark.asyncio
async def test_send_push_notification_success(monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession) -> None:
    """Ensure successful sends are reported correctly."""
    user_id = uuid.uuid4()
    db_session.add(UserPushToken(user_id=user_id, token="token-success", platform="android"))
    await db_session.commit()

    async def mock_send(tokens: list[str], title: str, body: str):
        assert tokens == ["token-success"]
        return DummyBatchResponse([True], [None])

    monkeypatch.setattr("src.app.services.push_service.get_firebase_app", lambda: object())
    monkeypatch.setattr("src.app.services.push_service._send_multicast", mock_send)

    result = await send_push_notification(db=db_session, user_ids=[user_id], title="Hello", body="World")
    assert isinstance(result, PushSendResult)
    assert result.requested_tokens == 1
    assert result.success == 1
    assert result.failed == 0


@pytest.mark.asyncio
async def test_send_push_notification_marks_inactive_on_not_registered(
    monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
) -> None:
    """Tokens returning registration errors should be marked inactive."""
    user_id = uuid.uuid4()
    token = UserPushToken(user_id=user_id, token="token-fail", platform="android")
    db_session.add(token)
    await db_session.commit()

    async def mock_send(tokens: list[str], title: str, body: str):
        return DummyBatchResponse([False], ["registration-token-not-registered"])

    monkeypatch.setattr("src.app.services.push_service.get_firebase_app", lambda: object())
    monkeypatch.setattr("src.app.services.push_service._send_multicast", mock_send)

    result = await send_push_notification(db=db_session, user_ids=[user_id], title="Hello", body="World")
    assert result.failed == 1

    refreshed = await db_session.get(UserPushToken, token.id)
    assert refreshed is not None
    assert refreshed.is_active is False


@pytest.mark.asyncio
async def test_send_push_notification_requires_firebase(monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession) -> None:
    """Service should raise when Firebase is unavailable."""

    async def fake_send(*args, **kwargs):
        return DummyBatchResponse([True], [None])

    monkeypatch.setattr("src.app.services.push_service.get_firebase_app", lambda: None)
    monkeypatch.setattr("src.app.services.push_service.init_firebase", lambda: None)
    monkeypatch.setattr("src.app.services.push_service._send_multicast", fake_send)

    with pytest.raises(FirebaseNotInitializedError):
        await send_push_notification(
            db=db_session,
            user_ids=[uuid.uuid4()],
            title="Hello",
            body="World",
        )


