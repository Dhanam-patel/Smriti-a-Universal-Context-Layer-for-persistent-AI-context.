from unittest.mock import patch

from app import db


def test_client_is_created_lazily_and_only_once():
    db.get_supabase.cache_clear()
    with patch.object(db, "create_client") as create_client:
        create_client.assert_not_called()

        first = db.get_supabase()
        second = db.get_supabase()

    assert first is second
    create_client.assert_called_once_with(
        db.settings.supabase_url, db.settings.supabase_service_role_key
    )
    db.get_supabase.cache_clear()
