import sys
import io
import uuid
import httpx

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def run_live_tests():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        print("=== 1. Testing Live User Registration ===")
        uid = uuid.uuid4().hex[:6]
        email = f"live_ai_test_{uid}@example.com"
        reg = client.post("/api/auth/register", json={
            "name": "Live Assistant Tester",
            "email": email,
            "password": "Password123!",
            "terms_accepted": True,
            "ai_consent_accepted": True
        })
        assert reg.status_code == 201, f"Registration failed: {reg.text}"
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"Registered user: {email}")

        print("=== 2. Setting Profile & Goal ===")
        client.post("/api/profile", headers=headers, json={
            "name": "Live Assistant Tester",
            "age": 27,
            "gender": "male",
            "height_cm": 178.0,
            "weight_kg": 75.0,
            "activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "vegetarian"
        })

        client.post("/api/goals", headers=headers, json={
            "goal_type": "weight_loss",
            "current_weight_kg": 75.0,
            "target_weight_kg": 70.0,
            "desired_rate": 0.5
        })

        # Log a meal and water
        client.post("/api/meals", headers=headers, json={
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
        client.post("/api/water", headers=headers, json={"amount_ml": 500})

        print("=== 3. Testing 20 Natural Language Questions ===")
        questions = [
            "How many calories do I have left?",
            "Can I eat 2 dosa for dinner?",
            "I ate 3 idlis and sambar, how many calories is that?",
            "What should I eat after gym?",
            "Is rice okay for weight loss?",
            "I am hungry. Give me something under 400 calories.",
            "How much protein have I eaten today?",
            "What did I eat today?",
            "Can I replace rice with chapati?",
            "I ate 2 eggs.",
            "Log 2 eggs for breakfast.",
            "How much water should I drink?",
            "My protein is low today. What should I eat?",
            "Give me a quick vegetarian dinner.",
            "Can I eat biryani tonight?",
            "What if I eat half a plate?",
            "How many calories are in 200 grams of rice?",
            "Suggest something using foods available in Tamil Nadu.",
            "Why am I hungry even after eating?",
            "Tell me something about nutrition that can help with my goal."
        ]

        for i, q in enumerate(questions, 1):
            res = client.post("/api/ai/chat", headers=headers, json={
                "messages": [{"role": "user", "content": q}]
            })
            assert res.status_code == 200, f"Chat failed for question {i}: {q}"
            resp_text = res.json()["response"]
            print(f"[{i:02d}] Q: {q}")
            print(f"     A: {resp_text[:110]}...")

        print("=== 4. Testing Multi-Turn Follow-Ups ===")
        # Seq 1
        seq1 = [
            {"role": "user", "content": "Can I eat dosa?"},
            {"role": "assistant", "content": "Yes, 1 Plain Dosa is ~168 kcal."},
            {"role": "user", "content": "What if I eat 2?"}
        ]
        res1 = client.post("/api/ai/chat", headers=headers, json={"messages": seq1})
        assert res1.status_code == 200
        print(f"Follow-up 1 (What if I eat 2?): {res1.json()['response'][:110]}...")

        # Seq 2
        seq2 = [
            {"role": "user", "content": "Suggest dinner."},
            {"role": "assistant", "content": "I can suggest dinner options! Do you have a calorie limit?"},
            {"role": "user", "content": "Under 500 calories."}
        ]
        res2 = client.post("/api/ai/chat", headers=headers, json={"messages": seq2})
        assert res2.status_code == 200
        print(f"Follow-up 2 (Under 500 calories.): {res2.json()['response'][:110]}...")

        print("=== 5. Testing Out-of-Scope Protection ===")
        res_out = client.post("/api/ai/chat", headers=headers, json={
            "messages": [{"role": "user", "content": "What is the capital of France?"}]
        })
        assert res_out.status_code == 200
        print(f"Out-of-scope response: {res_out.json()['response']}")

        print("=== 6. Testing CSV Date Formatting Against Live Server ===")
        csv_res = client.get("/api/export/csv", headers=headers)
        assert csv_res.status_code == 200
        raw = csv_res.content.decode("utf-8-sig")
        lines = [l.strip() for l in raw.splitlines() if l.strip()]

        for l in lines:
            if l.startswith("# Export Date"):
                dt = l.split(",")[1].strip()
                assert len(dt) == 10 and dt.count("-") == 2, f"Invalid meta date {dt}"
                print(f"CSV Metadata Export Date: {dt} (Valid YYYY-MM-DD)")
            elif "Plain Dosa" in l:
                parts = l.split(",")
                date_val, time_val = parts[0], parts[1]
                assert len(date_val) == 10 and date_val.count("-") == 2, f"Invalid meal date {date_val}"
                assert len(time_val) == 8 and time_val.count(":") == 2, f"Invalid meal time {time_val}"
                print(f"CSV Meal Row: Date={date_val}, Time={time_val} (Valid YYYY-MM-DD & HH:mm:ss)")

        print("ALL LIVE TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_live_tests()
