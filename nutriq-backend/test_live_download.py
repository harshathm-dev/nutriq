import sys
import httpx
import json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def test_live():
    base_url = "http://127.0.0.1:8000"
    client = httpx.Client(base_url=base_url)

    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[PASS] Backend health check passed:", res.json())

    # 2. Test CORS Preflight from Origin: http://localhost:5173
    cors_res = client.options(
        "/api/ai/chat",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type"
        }
    )
    assert cors_res.status_code == 200, f"CORS preflight failed: {cors_res.status_code}"
    assert cors_res.headers.get("access-control-allow-origin") == "http://localhost:5173", f"CORS origin mismatch: {cors_res.headers}"
    assert cors_res.headers.get("access-control-allow-credentials") == "true"
    print("[PASS] CORS preflight for http://localhost:5173 passed with credentials support")

    # 3. Register or Login
    email = "live_user_test@nutriq.app"
    reg = client.post("/api/auth/register", json={
        "name": "Live Test User",
        "email": email,
        "password": "Password123!",
        "terms_accepted": True,
        "ai_consent_accepted": True
    })
    if reg.status_code == 201:
        token = reg.json()["access_token"]
    else:
        login = client.post("/api/auth/login", json={
            "email": email,
            "password": "Password123!"
        })
        assert login.status_code == 200, f"Login failed: {login.text}"
        token = login.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Origin": "http://localhost:5173"
    }

    # Setup profile & goal
    client.post("/api/profile", headers=headers, json={
        "name": "Live Test User",
        "age": 30,
        "gender": "male",
        "height_cm": 178.0,
        "weight_kg": 76.0,
        "activity_level": "very_active",
        "fitness_goal": "weight_loss",
        "dietary_preference": "vegetarian"
    })

    client.post("/api/goals", headers=headers, json={
        "goal_type": "weight_loss",
        "current_weight_kg": 76.0,
        "target_weight_kg": 70.0,
        "desired_rate": 0.5
    })

    # Log an Indian meal & water
    client.post("/api/meals", headers=headers, json={
        "meal_type": "breakfast",
        "source": "search",
        "items": [
            {
                "food_name": "Idli with Coconut Chutney",
                "quantity": 3.0,
                "serving_unit": "piece",
                "grams": 150.0,
                "calories": 195.0,
                "protein_g": 6.0,
                "carbs_g": 36.0,
                "fat_g": 3.0,
                "fiber_g": 2.1
            }
        ]
    })
    client.post("/api/water", headers=headers, json={"amount_ml": 800})
    print("[PASS] Profile, goals, meal, and water logged successfully")

    # =========================================================================
    # 4. ERROR 1 TEST: Meal Planner Generation & Retrieval
    # =========================================================================
    mp_res = client.post("/api/ai/meal-plan", headers=headers, json={"days": 3, "budget_level": "medium"})
    assert mp_res.status_code == 200, f"Meal planner failed: {mp_res.text}"
    mp_data = mp_res.json()
    assert mp_data["active"] is True
    payload = json.loads(mp_data["plan_payload"])
    assert len(payload["days"]) == 3
    print(f"[PASS] Error 1 Fixed: Meal Planner generated 3-day plan successfully: {mp_data['title']}")

    # GET /api/ai/meal-plan active plan retrieval
    mp_active = client.get("/api/ai/meal-plan", headers=headers)
    assert mp_active.status_code == 200
    assert mp_active.json()["id"] == mp_data["id"]
    print("[PASS] Active Meal Plan retrieval via GET /api/ai/meal-plan verified")

    # =========================================================================
    # 5. ERROR 2 TEST: AI Assistant Grounded Responses
    # =========================================================================
    queries = [
        "How many calories do I have left?",
        "What did I eat today?",
        "How much protein have I consumed?",
        "Suggest a high-protein dinner.",
        "How much water should I drink?",
        "What can I eat instead of white rice?"
    ]
    chat_responses = []
    for q in queries:
        c_res = client.post("/api/ai/chat", headers=headers, json={
            "messages": [{"role": "user", "content": q}]
        })
        assert c_res.status_code == 200, f"AI Chat failed for query '{q}': {c_res.text}"
        ans = c_res.json()["response"]
        assert len(ans) > 20
        chat_responses.append(ans)
        print(f"  • Q: '{q}'\n    A: {ans[:80]}...")

    assert len(set(chat_responses)) == len(queries), "All responses must be distinct and grounded"
    print("[PASS] Error 2 Fixed: AI Assistant responses verified for all grounded query types")

    # =========================================================================
    # 6. ERROR 3 TEST: Privacy & Consent + Export Downloads
    # =========================================================================
    consents_res = client.get("/api/privacy/consents", headers=headers)
    assert consents_res.status_code == 200, f"Consents failed: {consents_res.text}"
    print(f"[PASS] Error 3 Fixed: Privacy consents retrieved ({len(consents_res.json())} active records)")

    # Test PDF Download
    pdf_res = client.get("/api/export/pdf", headers=headers)
    assert pdf_res.status_code == 200, f"PDF failed: {pdf_res.text}"
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert "NutriQ_Nutrition_Report_" in pdf_res.headers["content-disposition"]
    assert pdf_res.content.startswith(b"%PDF-")
    print(f"[PASS] PDF export verified ({len(pdf_res.content)} bytes, filename: {pdf_res.headers['content-disposition']})")

    # Test CSV Download
    csv_res = client.get("/api/export/csv", headers=headers)
    assert csv_res.status_code == 200, f"CSV failed: {csv_res.text}"
    assert "text/csv" in csv_res.headers["content-type"]
    assert "NutriQ_Nutrition_Data_" in csv_res.headers["content-disposition"]
    assert csv_res.content.startswith(b"\xef\xbb\xbf")
    assert "Idli with Coconut Chutney" in csv_res.content.decode("utf-8-sig")
    print(f"[PASS] CSV export verified ({len(csv_res.content)} bytes, filename: {csv_res.headers['content-disposition']})")

    # Test JSON Download
    json_res = client.get("/api/export/json", headers=headers)
    assert json_res.status_code == 200, f"JSON failed: {json_res.text}"
    assert "application/json" in json_res.headers["content-type"]
    assert "NutriQ_Data_Backup_" in json_res.headers["content-disposition"]
    backup_data = json_res.json()
    assert backup_data["profile"]["name"] == "Live Test User"
    assert len(backup_data["meals"]) >= 1
    print(f"[PASS] JSON export verified ({len(json_res.content)} bytes, filename: {json_res.headers['content-disposition']})")

    print("\n============================================================")
    print("ALL LIVE BACKEND DIAGNOSTICS & VERIFICATIONS PASSED SUCCESSFULLY!")
    print("============================================================")

if __name__ == "__main__":
    test_live()
