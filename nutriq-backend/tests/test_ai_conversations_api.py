import pytest
import uuid
import json
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_ai_conversations_full_crud_and_isolation():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User 1
        uid1 = uuid.uuid4().hex[:8]
        reg1 = await client.post("/api/auth/register", json={
            "name": "Conv User 1",
            "email": f"conv1_{uid1}@example.com",
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg1.status_code == 201
        token1 = reg1.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Setup Profile
        await client.post("/api/profile", headers=headers1, json={
            "name": "Conv User 1",
            "age": 28,
            "gender": "male",
            "height_cm": 178.0,
            "weight_kg": 75.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "standard"
        })

        # 2. POST /api/ai/conversations -> Create new conversation
        create_res = await client.post("/api/ai/conversations", headers=headers1, json={"title": "New Conversation"})
        assert create_res.status_code == 201
        c1 = create_res.json()
        c1_id = c1["id"]
        assert c1["title"] == "New Conversation"
        assert c1["user_id"] is not None

        # 3. POST /api/ai/conversations/{id}/messages -> Send first message and verify smart auto-title
        msg1_res = await client.post(
            f"/api/ai/conversations/{c1_id}/messages",
            headers=headers1,
            json={"content": "How many calories do I have left today?", "stream": False}
        )
        assert msg1_res.status_code == 200
        msg1_data = msg1_res.json()
        assert msg1_data["role"] == "assistant"
        assert len(msg1_data["content"]) > 5

        # Fetch detail: GET /api/ai/conversations/{c1_id}
        c1_detail = await client.get(f"/api/ai/conversations/{c1_id}", headers=headers1)
        assert c1_detail.status_code == 200
        d1 = c1_detail.json()
        assert len(d1["messages"]) == 2  # 1 user + 1 assistant
        assert d1["messages"][0]["role"] == "user"
        assert d1["messages"][0]["content"] == "How many calories do I have left today?"
        assert d1["messages"][1]["role"] == "assistant"
        # Auto-title should have been updated from "New Conversation" to "Calorie Progress"
        assert d1["title"] == "Calorie Progress"

        # 4. Create second conversation with dinner question
        c2_res = await client.post("/api/ai/conversations", headers=headers1, json={})
        assert c2_res.status_code == 201
        c2_id = c2_res.json()["id"]

        msg2_res = await client.post(
            f"/api/ai/conversations/{c2_id}/messages",
            headers=headers1,
            json={"content": "What should I eat for dinner?", "stream": False}
        )
        assert msg2_res.status_code == 200

        c2_detail = await client.get(f"/api/ai/conversations/{c2_id}", headers=headers1)
        assert c2_detail.status_code == 200
        assert c2_detail.json()["title"] == "Dinner Suggestions"

        # 5. GET /api/ai/conversations -> List all conversations
        list_res = await client.get("/api/ai/conversations", headers=headers1)
        assert list_res.status_code == 200
        conv_list = list_res.json()
        assert len(conv_list) >= 2
        # c2 was updated last, so should be first in list
        assert conv_list[0]["id"] == c2_id

        # 6. Test search filter inside conversations
        search_res = await client.get("/api/ai/conversations?q=dinner", headers=headers1)
        assert search_res.status_code == 200
        search_list = search_res.json()
        assert any(c["id"] == c2_id for c in search_list)

        # 7. PATCH /api/ai/conversations/{id} -> Rename conversation
        rename_res = await client.patch(
            f"/api/ai/conversations/{c1_id}",
            headers=headers1,
            json={"title": "Custom Calorie Tracking Session"}
        )
        assert rename_res.status_code == 200
        assert rename_res.json()["title"] == "Custom Calorie Tracking Session"

        # Verify rename persisted
        check_rename = await client.get(f"/api/ai/conversations/{c1_id}", headers=headers1)
        assert check_rename.json()["title"] == "Custom Calorie Tracking Session"

        # 8. Test User B Isolation
        uid2 = uuid.uuid4().hex[:8]
        reg2 = await client.post("/api/auth/register", json={
            "name": "Conv User 2",
            "email": f"conv2_{uid2}@example.com",
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg2.status_code == 201
        token2 = reg2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # User B should have 0 conversations
        b_list = await client.get("/api/ai/conversations", headers=headers2)
        assert b_list.status_code == 200
        assert len(b_list.json()) == 0

        # User B cannot access User 1's conversation
        b_get_unauth = await client.get(f"/api/ai/conversations/{c1_id}", headers=headers2)
        assert b_get_unauth.status_code == 404

        # User B cannot rename User 1's conversation
        b_rename_unauth = await client.patch(
            f"/api/ai/conversations/{c1_id}",
            headers=headers2,
            json={"title": "Hacked Title"}
        )
        assert b_rename_unauth.status_code == 404

        # User B cannot send message to User 1's conversation
        b_msg_unauth = await client.post(
            f"/api/ai/conversations/{c1_id}/messages",
            headers=headers2,
            json={"content": "Unauthorized message", "stream": False}
        )
        assert b_msg_unauth.status_code == 404

        # User B cannot delete User 1's conversation
        b_del_unauth = await client.delete(f"/api/ai/conversations/{c1_id}", headers=headers2)
        assert b_del_unauth.status_code == 404

        # 9. User 1 Deletes c2
        del_res = await client.delete(f"/api/ai/conversations/{c2_id}", headers=headers1)
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True

        # c2 should no longer exist
        get_c2_after_del = await client.get(f"/api/ai/conversations/{c2_id}", headers=headers1)
        assert get_c2_after_del.status_code == 404

        # c1 still exists
        get_c1_after_del = await client.get(f"/api/ai/conversations/{c1_id}", headers=headers1)
        assert get_c1_after_del.status_code == 200
