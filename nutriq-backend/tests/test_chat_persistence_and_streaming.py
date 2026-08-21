import pytest
import uuid
import json
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_chat_persistence_and_streaming():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User A
        uid_a = uuid.uuid4().hex[:8]
        reg_a = await client.post("/api/auth/register", json={
            "name": "Chat User A",
            "email": f"chat_a_{uid_a}@example.com",
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_a.status_code == 201
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Setup Profile
        await client.post("/api/profile", headers=headers_a, json={
            "name": "Chat User A",
            "age": 27,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 72.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "standard"
        })

        # 2. GET /api/ai/chat/current (Initializes new conversation)
        curr_res = await client.get("/api/ai/chat/current", headers=headers_a)
        assert curr_res.status_code == 200
        curr_data = curr_res.json()
        assert "id" in curr_data
        assert "user_id" in curr_data
        assert isinstance(curr_data["messages"], list)
        session_1_id = curr_data["id"]


        # 3. POST /api/ai/chat/message (Non-streaming test)
        msg1_res = await client.post("/api/ai/chat/message", headers=headers_a, json={
            "session_id": session_1_id,
            "content": "How many calories do I have left today?",
            "stream": False
        })
        assert msg1_res.status_code == 200
        msg1_data = msg1_res.json()
        assert msg1_data["role"] == "assistant"
        assert len(msg1_data["content"]) > 10
        assert "metadata" in msg1_data

        # 4. Verify message persistence by fetching /current again (simulating page refresh)
        refresh_res = await client.get("/api/ai/chat/current", headers=headers_a)
        assert refresh_res.status_code == 200
        ref_data = refresh_res.json()
        assert ref_data["id"] == session_1_id
        assert len(ref_data["messages"]) == 2  # 1 user + 1 assistant
        assert ref_data["messages"][0]["role"] == "user"
        assert "How many calories" in ref_data["messages"][0]["content"]
        assert ref_data["messages"][1]["role"] == "assistant"

        # 5. POST /api/ai/chat/message (Streaming SSE test)
        stream_res = await client.post("/api/ai/chat/message", headers=headers_a, json={
            "session_id": session_1_id,
            "content": "Suggest a high protein dinner",
            "stream": True
        })
        assert stream_res.status_code == 200
        assert "text/event-stream" in stream_res.headers["content-type"]
        body_text = stream_res.text
        assert "data:" in body_text
        assert '"done": true' in body_text

        # 6. Verify session now has 4 messages
        refresh_res2 = await client.get("/api/ai/chat/current", headers=headers_a)
        assert refresh_res2.status_code == 200
        assert len(refresh_res2.json()["messages"]) == 4

        # 7. Create New Session: POST /api/ai/chat/session
        sess2_res = await client.post("/api/ai/chat/session", headers=headers_a, json={
            "title": "Weekend Meal Prep"
        })
        assert sess2_res.status_code == 200
        session_2_id = sess2_res.json()["id"]
        assert session_2_id != session_1_id
        assert sess2_res.json()["title"] == "Weekend Meal Prep"

        # 8. Check History: GET /api/ai/chat/history
        hist_res = await client.get("/api/ai/chat/history", headers=headers_a)
        assert hist_res.status_code == 200
        hist_data = hist_res.json()
        assert len(hist_data) >= 2
        session_ids = [s["id"] for s in hist_data]
        assert session_1_id in session_ids
        assert session_2_id in session_ids

        # 9. Register User B & Test Data Isolation
        uid_b = uuid.uuid4().hex[:8]
        reg_b = await client.post("/api/auth/register", json={
            "name": "Chat User B",
            "email": f"chat_b_{uid_b}@example.com",
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B history must NOT include User A sessions
        b_hist = await client.get("/api/ai/chat/history", headers=headers_b)
        assert b_hist.status_code == 200
        assert len(b_hist.json()) == 0

        # User B cannot delete User A's session
        unauth_del = await client.delete(f"/api/ai/chat/session/{session_1_id}", headers=headers_b)
        assert unauth_del.status_code == 404

        # 10. User A Deletes session_2
        del_res = await client.delete(f"/api/ai/chat/session/{session_2_id}", headers=headers_a)
        assert del_res.status_code == 200
        hist_after_del = await client.get("/api/ai/chat/history", headers=headers_a)
        remaining_ids = [s["id"] for s in hist_after_del.json()]
        assert session_2_id not in remaining_ids
        assert session_1_id in remaining_ids
