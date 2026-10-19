from datetime import datetime, timezone

import pytest

from app.application.post_service import create_post
from app.domain.models import User


def test_create_post_returns_post_for_persisted_user():
    created_at = datetime(2026, 10, 19, tzinfo=timezone.utc)

    post = create_post(User(id=7, username="alice"), "Hello", created_at=created_at)

    assert post.user_id == 7
    assert post.content == "Hello"
    assert post.created_at == created_at


@pytest.mark.parametrize(
    ("user", "content", "message"),
    [
        (User(username="alice"), "Hello", "persisted user id"),
        (User(id=7, username="alice"), " \t", "must not be blank"),
    ],
)
def test_create_post_rejects_invalid_application_input(
    user: User, content: str, message: str
):
    with pytest.raises(ValueError, match=message):
        create_post(user, content)
