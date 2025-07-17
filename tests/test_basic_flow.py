"""Basic integration tests for memes-ranker application."""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Database
from app.utils import generate_user_name, generate_session_token
from setup_db import create_database


async def test_database_operations():
    """Test basic database operations."""
    print("Testing database operations...")

    # Setup test database
    test_db_path = "data/test.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    create_database(test_db_path)

    db = Database(test_db_path)

    # Test user creation
    user_name = generate_user_name()
    session_token = generate_session_token()

    user_id = await db.create_user(user_name, session_token)
    print(f"✓ Created user: {user_name} (ID: {user_id})")

    # Test user retrieval
    user = await db.get_user_by_token(session_token)
    assert user is not None
    assert user["name"] == user_name
    print(f"✓ Retrieved user: {user['name']}")

    # Test meme creation
    meme_id = await db.create_meme("test-meme.png", "/static/memes/test-meme.png")
    print(f"✓ Created meme (ID: {meme_id})")

    # Test session creation and activation
    session_id = await db.create_session("Test Session")
    await db.start_session(session_id)
    print(f"✓ Created and started session (ID: {session_id})")

    # Test ranking creation
    ranking_id = await db.create_ranking(user_id, meme_id, 8)
    print(f"✓ Created ranking (ID: {ranking_id})")

    # Test ranking retrieval
    user_rankings = await db.get_user_rankings(user_id)
    assert len(user_rankings) == 1
    assert user_rankings[0]["score"] == 8
    print(f"✓ Retrieved user rankings: {len(user_rankings)} found")

    # Test meme stats
    stats = await db.get_meme_stats()
    assert len(stats) >= 1
    print(f"✓ Retrieved meme stats: {len(stats)} memes")

    # Test ranking update (UPSERT)
    await db.create_ranking(user_id, meme_id, 9)  # Update score
    user_rankings = await db.get_user_rankings(user_id)
    assert len(user_rankings) == 1  # Still only one ranking
    assert user_rankings[0]["score"] == 9  # Updated score
    print("✓ Updated ranking (UPSERT working)")

    # Test session management
    session_id = await db.create_session("Test Session")
    await db.start_session(session_id)
    active_session = await db.get_active_session()
    assert active_session is not None
    assert active_session["name"] == "Test Session"
    print("✓ Session management working")

    print("All database tests passed! ✅")


def test_utility_functions():
    """Test utility functions."""
    print("\nTesting utility functions...")

    from app.utils import generate_user_name, generate_session_token, generate_qr_code

    # Test name generation
    name1 = generate_user_name()
    name2 = generate_user_name()
    assert name1 != name2  # Should be different
    assert len(name1.split(" ")) == 2  # Should have two parts
    print(f"✓ Generated user names: {name1}, {name2}")

    # Test token generation
    token1 = generate_session_token()
    token2 = generate_session_token()
    assert token1 != token2  # Should be different
    assert len(token1) > 20  # Should be reasonably long
    print(f"✓ Generated session tokens: {token1[:10]}..., {token2[:10]}...")

    # Test QR code generation
    qr_bytes = generate_qr_code("https://example.com")
    assert len(qr_bytes) > 0
    assert qr_bytes.startswith(b"\x89PNG")  # PNG header
    print("✓ Generated QR code")

    print("All utility tests passed! ✅")


async def test_game_simulation():
    """Simulate a complete game flow."""
    print("\nSimulating complete game flow...")

    # Setup test database
    test_db_path = "data/test.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    create_database(test_db_path)

    db = Database(test_db_path)

    # Create multiple users
    users = []
    for i in range(3):
        name = generate_user_name()
        token = generate_session_token()
        user_id = await db.create_user(name, token)
        users.append({"id": user_id, "name": name, "token": token})

    print(f"✓ Created {len(users)} users")

    # Create multiple memes
    memes = []
    for i in range(5):
        filename = f"sample-meme-{i + 1}.png"
        path = f"/static/memes/{filename}"
        meme_id = await db.create_meme(filename, path)
        memes.append({"id": meme_id, "filename": filename})

    print(f"✓ Created {len(memes)} memes")

    # Create and start a session for the game
    session_id = await db.create_session("Game Session")
    await db.start_session(session_id)
    print(f"✓ Created and started session (ID: {session_id})")

    # Each user rates each meme
    import random

    for user in users:
        for meme in memes:
            score = random.randint(1, 10)
            await db.create_ranking(user["id"], meme["id"], score)

    print("✓ All users rated all memes")

    # Check final statistics
    stats = await db.get_meme_stats()
    for stat in stats:
        if stat["ranking_count"] > 0:
            print(
                f"  📊 {stat['filename']}: {stat['average_score']:.1f}/10 (from {stat['ranking_count']} ratings)"
            )

    print("Game simulation completed! ✅")


def test_authentication():
    """Test authentication functions."""
    print("\nTesting authentication...")

    from app.auth import (
        verify_password,
        get_password_hash,
        create_access_token,
        verify_token,
    )

    # Test password hashing
    password = "test_password"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)
    print("✓ Password hashing working")

    # Test JWT tokens
    token = create_access_token({"sub": "admin", "role": "admin"})
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "admin"
    assert payload["role"] == "admin"
    print("✓ JWT tokens working")

    print("Authentication tests passed! ✅")


async def main():
    """Run all tests."""
    print("🧪 Running Memes Ranker Integration Tests\n")

    try:
        # Test database operations
        await test_database_operations()

        # Test utility functions
        test_utility_functions()

        # Test authentication
        test_authentication()

        # Test complete game simulation
        await test_game_simulation()

        print("\n🎉 All tests passed! The memes ranker application is ready!")
        print("\nTo start the application:")
        print("1. Make sure database is initialized: uv run python setup_db.py")
        print("2. Start the server: uv run python -m app.main")
        print("3. Open http://localhost:8000 in your browser")
        print("4. Admin login: http://localhost:8000/admin (password: admin123)")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
