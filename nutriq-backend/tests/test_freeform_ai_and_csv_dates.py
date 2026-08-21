import pytest
import uuid
import json
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_freeform_ai_and_csv_dates():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User
        uid = uuid.uuid4().hex[:8]
        reg_res = await client.post("/api/auth/register", json={
            "name": "FreeForm Test User",
            "email": f"freeform_{uid}@example.com",
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Setup Profile & Goal
        await client.post("/api/profile", headers=headers, json={
            "name": "FreeForm Test User",
            "age": 29,
            "gender": "male",
            "height_cm": 176.0,
            "weight_kg": 74.0,
            "activity_level": "very_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "vegetarian"
        })

        await client.post("/api/goals", headers=headers, json={
            "goal_type": "weight_loss",
            "current_weight_kg": 74.0,
            "target_weight_kg": 68.0,
            "desired_rate": 0.5
        })

        # Log initial meal and water
        await client.post("/api/meals", headers=headers, json={
            "meal_type": "breakfast",
            "source": "search",
            "items": [
                {
                    "food_name": "Plain Dosa",
                    "quantity": 2.0,
                    "serving_unit": "piece",
                    "grams": 160.0,
                    "calories": 269.0,
                    "protein_g": 6.2,
                    "carbs_g": 47.0,
                    "fat_g": 5.9,
                    "fiber_g": 2.9
                }
            ]
        })
        await client.post("/api/water", headers=headers, json={"amount_ml": 500})

        # =====================================================================
        # PART 1: TEST ALL 20 REQUIRED FREE-FORM NUTRITION QUESTIONS
        # =====================================================================
        questions = [
            ("How many calories do I have left?", ["remaining", "kcal"]),
            ("Can I eat 2 dosa for dinner?", ["dosa", "kcal"]),
            ("I ate 3 idlis and sambar, how many calories is that?", ["idli", "sambar", "kcal"]),
            ("What should I eat after gym?", ["protein", "carbohydrates"]),
            ("Is rice okay for weight loss?", ["rice", "calorie"]),
            ("I am hungry. Give me something under 400 calories.", ["hungry", "kcal"]),
            ("How much protein have I eaten today?", ["protein", "target"]),
            ("What did I eat today?", ["Plain Dosa", "Breakfast"]),
            ("Can I replace rice with chapati?", ["chapati", "phulka", "fiber"]),
            ("I ate 2 eggs.", ["egg", "kcal", "journal"]),
            ("Log 2 eggs for breakfast.", ["logged", "breakfast", "remaining"]),
            ("How much water should I drink?", ["hydration", "ml"]),
            ("My protein is low today. What should I eat?", ["protein", "paneer"]),
            ("Give me a quick vegetarian dinner.", ["phulkas", "millet", "paneer"]),
            ("Can I eat biryani tonight?", ["biriyani", "kcal"]),
            ("What if I eat half a plate?", ["plate", "kcal"]),
            ("How many calories are in 200 grams of rice?", ["rice", "260", "kcal"]),
            ("Suggest something using foods available in Tamil Nadu.", ["tamil", "pongal", "ragi"]),
            ("Why am I hungry even after eating?", ["protein", "fiber", "hunger"]),
            ("Tell me something about nutrition that can help with my goal.", ["thermic", "protein", "satiety"])
        ]

        responses = []
        for q, expected_keywords in questions:
            res = await client.post("/api/ai/chat", headers=headers, json={
                "messages": [{"role": "user", "content": q}]
            })
            assert res.status_code == 200, f"Failed for query '{q}': {res.text}"
            ans = res.json()["response"]
            assert len(ans) > 20, f"Response too short for '{q}'"
            assert not ans.startswith("Sorry, I am temporarily unable"), f"Got fallback error for '{q}'"
            for kw in expected_keywords:
                assert kw.lower() in ans.lower(), f"Keyword '{kw}' missing from response for query '{q}': {ans}"
            responses.append(ans)

        # Ensure all 20 responses are unique and distinct
        assert len(set(responses)) == 20, "Every question must receive a uniquely grounded response"

        # =====================================================================
        # PART 1.1: TEST MULTI-TURN FOLLOW-UP CONVERSATIONS
        # =====================================================================
        # Sequence 1: "Can I eat dosa?" -> "What if I eat 2?"
        history_seq1 = [
            {"role": "user", "content": "Can I eat dosa?"},
            {"role": "assistant", "content": "Yes, 1 Plain Dosa is approximately 168 kcal. How many are you planning to eat?"},
            {"role": "user", "content": "What if I eat 2?"}
        ]
        seq1_res = await client.post("/api/ai/chat", headers=headers, json={"messages": history_seq1})
        assert seq1_res.status_code == 200
        seq1_ans = seq1_res.json()["response"]
        assert "dosa" in seq1_ans.lower()
        assert "336" in seq1_ans or "kcal" in seq1_ans.lower()

        # Sequence 2: "Suggest dinner." -> "Under 500 calories."
        history_seq2 = [
            {"role": "user", "content": "Suggest dinner."},
            {"role": "assistant", "content": "I can suggest a nutritious dinner! Do you have any calorie constraint?"},
            {"role": "user", "content": "Under 500 calories."}
        ]
        seq2_res = await client.post("/api/ai/chat", headers=headers, json={"messages": history_seq2})
        assert seq2_res.status_code == 200
        seq2_ans = seq2_res.json()["response"]
        assert "500" in seq2_ans
        assert "phulkas" in seq2_ans.lower() or "paneer" in seq2_ans.lower() or "millet" in seq2_ans.lower()

        # =====================================================================
        # PART 1.2: TEST OUT-OF-SCOPE NON-NUTRITION QUESTION
        # =====================================================================
        out_scope_res = await client.post("/api/ai/chat", headers=headers, json={
            "messages": [{"role": "user", "content": "What is the capital of France?"}]
        })
        assert out_scope_res.status_code == 200
        out_ans = out_scope_res.json()["response"]
        assert "outside my nutrition focus" in out_ans.lower() or "nutrition" in out_ans.lower()

        # =====================================================================
        # PART 2: TEST CSV DATE & TIME EXPORT (NO ######## IN EXCEL)
        # =====================================================================
        csv_res = await client.get("/api/export/csv", headers=headers)
        assert csv_res.status_code == 200
        assert csv_res.headers["content-type"].startswith("text/csv")
        assert csv_res.content.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM

        csv_text = csv_res.content.decode("utf-8-sig")
        lines = [line.strip() for line in csv_text.splitlines() if line.strip()]

        # Verify Metadata line
        export_date_line = [l for l in lines if l.startswith("# Export Date")]
        assert len(export_date_line) == 1
        # Format must be YYYY-MM-DD (10 chars for date)
        export_dt = export_date_line[0].split(",")[1].strip()
        assert len(export_dt) == 10 and export_dt.count("-") == 2, f"Export date '{export_dt}' is not YYYY-MM-DD"

        # Verify Meal records section
        meal_header_idx = -1
        for idx, line in enumerate(lines):
            if line.startswith("Date,Time,Meal Type"):
                meal_header_idx = idx
                break
        assert meal_header_idx != -1

        # Check the data row following header
        meal_row = lines[meal_header_idx + 1]
        fields = meal_row.split(",")
        date_col = fields[0].strip()
        time_col = fields[1].strip()

        # Date MUST be exactly YYYY-MM-DD
        assert len(date_col) == 10 and date_col.count("-") == 2, f"Meal date '{date_col}' is not YYYY-MM-DD"
        assert "t" not in date_col.lower(), f"Meal date '{date_col}' contains ISO timestamp"
        assert "invalid" not in date_col.lower()
        assert "undefined" not in date_col.lower()

        # Time MUST be HH:mm:ss
        assert len(time_col) == 8 and time_col.count(":") == 2, f"Meal time '{time_col}' is not HH:mm:ss"

        # Verify Hydration section
        hyd_line = [l for l in lines if l.startswith("# Hydration Logs")]
        assert len(hyd_line) == 1

        # Verify Daily Nutrition Summaries section
        sum_line = [l for l in lines if l.startswith("# Daily Nutrition Summaries")]
        assert len(sum_line) == 1
