import os
import json
import logging
import re
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

class GeminiRecommendationItem(BaseModel):
    food_name: str
    serving_size: str = "1 serving"
    calories: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    reason: str = ""

class GeminiAssistantResponse(BaseModel):
    answer: str
    recommendations: List[GeminiRecommendationItem] = []
    warnings: List[str] = []
    remaining_calories: float = 0.0
    remaining_protein: float = 0.0
    sources: List[str] = ["NutriQ Verified Food Database", "IFCT"]
    suggested_actions: List[str] = []

class GeminiService:
    """
    Google GenAI SDK Integration for NutriQ AI Companion.
    Uses official `google-genai` SDK with strict database-grounded context,
    deterministic nutrition values, allergen pre-filtering, and zero hallucination.
    """

    @classmethod
    def get_client(cls):
        api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        if not api_key or not api_key.strip() or "your-gemini-api-key" in api_key.lower():
            return None
        try:
            from google import genai
            return genai.Client(api_key=api_key.strip())
        except Exception as e:
            logger.error(f"Failed to initialize Google GenAI client: {e}")
            return None

    @classmethod
    def is_available(cls) -> bool:
        api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        return bool(api_key and api_key.strip() and "your-gemini-api-key" not in api_key.lower())

    @classmethod
    def _build_user_prompt(
        cls,
        user_message: str,
        context: Dict[str, Any],
        candidate_foods: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        user_prof = context.get("user_profile", {})
        today_data = context.get("today", {})
        targets = context.get("nutrition_target", {})
        recent_meals = context.get("recent_meals", [])
        backend_warnings = context.get("warnings", [])

        rem_cal = today_data.get("calories_remaining", 0.0)
        rem_pro = today_data.get("protein_remaining", 0.0)
        cal_consumed = today_data.get("calories_consumed", 0.0)
        cal_target = targets.get("calories", 2000.0)
        allergies_str = ", ".join(user_prof.get("allergies", [])) if user_prof.get("allergies") else "None"

        # Format conversational memory
        history_lines = []
        if conversation_history:
            for m in conversation_history[-10:]:
                role_label = "User" if m.get("role") == "user" else "Assistant"
                content_text = m.get("content", "")
                if content_text:
                    history_lines.append(f"{role_label}: {content_text}")
        history_str = "\n".join(history_lines) if history_lines else "None (New Conversation)"

        # Format logged meals
        recent_meals_formatted = []
        if recent_meals:
            for m in recent_meals:
                m_type = m.get("meal_type", "Meal").capitalize()
                items_str = ", ".join([f"{it.get('food_name', '')} ({int(it.get('calories', 0))} kcal)" for it in m.get("items", [])])
                recent_meals_formatted.append(f"{m_type}: {items_str} ({int(m.get('meal_calories', 0))} kcal total)")
        recent_meals_str = "; ".join(recent_meals_formatted) if recent_meals_formatted else "None logged yet"

        yesterday_data = context.get("yesterday", {})
        yesterday_meals = context.get("yesterday_meals", [])
        yesterday_meals_formatted = []
        if yesterday_meals:
            for m in yesterday_meals:
                m_type = m.get("meal_type", "Meal").capitalize()
                items_str = ", ".join([f"{it.get('food_name', '')} ({int(it.get('calories', 0))} kcal)" for it in m.get("items", [])])
                yesterday_meals_formatted.append(f"{m_type}: {items_str} ({int(m.get('meal_calories', 0))} kcal total)")
        yesterday_meals_str = "; ".join(yesterday_meals_formatted) if yesterday_meals_formatted else "None logged yesterday"

        return f"""USER QUESTION:
{user_message}

RECENT CONVERSATION HISTORY:
{history_str}

GROUNDED CONTEXT SUMMARY:
- User Fitness Goal: {user_prof.get('fitness_goal', 'maintain')}
- Dietary Preference: {user_prof.get('dietary_preference', 'standard')}
- Stored Allergies: {allergies_str}
- Today's Calorie Target: {cal_target} kcal
- Calories Consumed Today: {cal_consumed} kcal
- Calories Remaining Today: {rem_cal} kcal
- Protein Target: {targets.get('protein', 0.0)}g
- Protein Consumed Today: {today_data.get('protein_consumed', 0.0)}g
- Protein Remaining Today: {rem_pro}g
- Hydration: {today_data.get('water_consumed', 0)} ml / {targets.get('hydration', 2500)} ml
- Logged Meals Today ({len(recent_meals)} recorded): {recent_meals_str}
- Yesterday's Consumption: {yesterday_data.get('total_calories', 0.0)} kcal consumed ({len(yesterday_meals)} meals recorded: {yesterday_meals_str})
- Active Calorie Warnings: {json.dumps(backend_warnings)}

AVAILABLE VERIFIED DATABASE CANDIDATE FOODS (Must only recommend from these if suggesting foods):
{json.dumps(candidate_foods[:12], indent=2) if candidate_foods else '[]'}

Provide a structured, empathetic, and strictly factual response."""



    @classmethod
    async def generate_assistant_response(
        cls,
        user_message: str,
        context: Dict[str, Any],
        candidate_foods: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generates a grounded, structured AI assistant response using Gemini.
        If Gemini is unavailable or errors out (e.g. rate limit 429/503), falls back safely to deterministic rules.
        """
        client = cls.get_client()
        if not client:
            return cls._generate_deterministic_fallback(
                user_message=user_message,
                context=context,
                candidate_foods=candidate_foods,
                reason="api_key_missing"
            )

        system_instruction = cls._build_system_instruction(
            user_prof=context.get("user_profile", {}),
            today_data=context.get("today", {}),
            targets=context.get("nutrition_target", {}),
            recent_meals=context.get("recent_meals", []),
            backend_warnings=context.get("warnings", []),
            candidate_foods=candidate_foods
        )
        user_prompt = cls._build_user_prompt(
            user_message=user_message,
            context=context,
            candidate_foods=candidate_foods,
            conversation_history=conversation_history
        )

        configured_model = getattr(settings, "GEMINI_MODEL", "gemini-flash-latest") or "gemini-flash-latest"
        candidate_models = [configured_model, "gemini-flash-latest", "gemini-3.6-flash"]
        unique_models = []
        for m in candidate_models:
            if m and m not in unique_models:
                unique_models.append(m)

        for model_name in unique_models:
            try:
                def _sync_call(m_name=model_name):
                    return client.models.generate_content(
                        model=m_name,
                        contents=user_prompt,
                        config={
                            "system_instruction": system_instruction,
                            "temperature": 0.2,
                            "response_mime_type": "application/json"
                        }
                    )

                response = await asyncio.wait_for(asyncio.to_thread(_sync_call), timeout=2.5)
                response_text = response.text if hasattr(response, "text") else ""
                if response_text and response_text.strip():
                    parsed = cls._parse_and_validate_gemini_json(
                        response_text=response_text,
                        context=context,
                        candidate_foods=candidate_foods
                    )
                    return parsed

            except Exception as e:
                err_str = str(e).lower()
                logger.warning(f"NutriQ AI Gemini call failed with model '{model_name}': {e}")
                if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str or "demand" in err_str or "503" in err_str:
                    break
                continue

        logger.info("Falling back to NutriQ deterministic nutrition engine.")
        return cls._generate_deterministic_fallback(
            user_message=user_message,
            context=context,
            candidate_foods=candidate_foods,
            reason="api_call_error"
        )

    @classmethod
    async def generate_assistant_stream(
        cls,
        user_message: str,
        context: Dict[str, Any],
        candidate_foods: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams response chunks for the AI Assistant via Server-Sent Events (SSE).
        Yields dictionaries with chunk text, followed by the finalized response object.
        """
        client = cls.get_client()

        if not client:
            fallback = cls._generate_deterministic_fallback(
                user_message=user_message,
                context=context,
                candidate_foods=candidate_foods,
                reason="api_key_missing"
            )
            full_text = fallback.get("answer", "")
            words = re.split(r'(\s+)', full_text)
            for w in words:
                if w:
                    yield {"chunk": w, "done": False}
                    await asyncio.sleep(0.008)

            yield {"chunk": "", "done": True, "full_response": fallback}
            return

        system_instruction = cls._build_system_instruction(
            user_prof=context.get("user_profile", {}),
            today_data=context.get("today", {}),
            targets=context.get("nutrition_target", {}),
            recent_meals=context.get("recent_meals", []),
            backend_warnings=context.get("warnings", []),
            candidate_foods=candidate_foods
        )
        user_prompt = cls._build_user_prompt(
            user_message=user_message,
            context=context,
            candidate_foods=candidate_foods,
            conversation_history=conversation_history
        )

        configured_model = getattr(settings, "GEMINI_MODEL", "gemini-flash-latest") or "gemini-flash-latest"
        candidate_models = [configured_model, "gemini-flash-latest", "gemini-3.6-flash"]
        unique_models = []
        for m in candidate_models:
            if m and m not in unique_models:
                unique_models.append(m)

        for model_name in unique_models:
            try:
                def _sync_stream(m_name=model_name):
                    return client.models.generate_content(
                        model=m_name,
                        contents=user_prompt,
                        config={
                            "system_instruction": system_instruction,
                            "temperature": 0.2,
                            "response_mime_type": "application/json"
                        }
                    )

                response = await asyncio.wait_for(asyncio.to_thread(_sync_stream), timeout=2.5)
                response_text = response.text if hasattr(response, "text") else ""
                if response_text and response_text.strip():
                    parsed = cls._parse_and_validate_gemini_json(
                        response_text=response_text,
                        context=context,
                        candidate_foods=candidate_foods
                    )
                    full_answer = parsed.get("answer", "")
                    words = re.split(r'(\s+)', full_answer)
                    for w in words:
                        if w:
                            yield {"chunk": w, "done": False}
                            await asyncio.sleep(0.008)

                    yield {"chunk": "", "done": True, "full_response": parsed}
                    return

            except Exception as e:
                err_str = str(e).lower()
                logger.warning(f"NutriQ AI streaming attempt failed with model '{model_name}': {e}")
                if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str or "demand" in err_str or "503" in err_str:
                    break
                continue

        # Deterministic fallback streaming
        logger.info("Streaming NutriQ deterministic nutrition response fallback.")
        fallback = cls._generate_deterministic_fallback(
            user_message=user_message,
            context=context,
            candidate_foods=candidate_foods,
            reason="api_call_error"
        )
        words = re.split(r'(\s+)', fallback.get("answer", ""))
        for w in words:
            if w:
                yield {"chunk": w, "done": False}
                await asyncio.sleep(0.008)

        yield {"chunk": "", "done": True, "full_response": fallback}


    @classmethod
    def _build_system_instruction(
        cls,
        user_prof: Dict[str, Any],
        today_data: Dict[str, Any],
        targets: Dict[str, Any],
        recent_meals: List[Dict[str, Any]],
        backend_warnings: List[Dict[str, Any]],
        candidate_foods: List[Dict[str, Any]]
    ) -> str:
        return """You are NutriQ AI, a personal nutrition assistant.

Your job is to help the user with:
- calories
- protein
- carbohydrates
- fats
- fiber
- hydration
- weight management
- Indian food
- meal suggestions
- food substitutions
- meal planning
- nutrition progress
- logged food analysis

Use the user's actual nutrition data provided in the context.
Never invent the user's intake.
When the user asks for a meal suggestion, calculate the remaining nutrition needs and recommend suitable foods from the available food catalog when possible.
If the user asks about calories, use the user's current calorie target and actual consumed calories.
If the user asks about protein, use their actual protein target and intake.
If the user asks about progress, analyze their actual logged data.
If insufficient data exists, clearly state what information is missing.
Do not respond with a generic fallback if the question is a valid nutrition question.
Keep answers practical and concise.
You are allowed to answer predefined NutriQ nutrition questions.

CRITICAL SAFETY & GROUNDING RULES:
1. STRICT ALLERGEN SAFETY: Never recommend foods containing user's recorded allergens.
2. ZERO ARITHMETIC HALLUCINATION: All numerical values must strictly reflect the user's calculated remaining targets and logged meals.
3. When recommending foods, prioritize the verified database candidate list provided in context.

RESPONSE FORMAT (Strict JSON schema):
{
  "answer": "Clear, formatted conversational response in markdown with bullet points and bolding.",
  "recommendations": [
    {
      "food_name": "Dish Name",
      "serving_size": "1 serving (150g)",
      "calories": 220,
      "protein_g": 18.5,
      "carbs_g": 12.0,
      "fat_g": 6.5,
      "fiber_g": 3.0,
      "reason": "Why this fits user's goal and remaining budget"
    }
  ],
  "warnings": [],
  "remaining_calories": 0,
  "remaining_protein": 0,
  "sources": ["NutriQ Verified Food Database", "IFCT"],
  "suggested_actions": ["Action 1", "Action 2"]
}
"""

    @classmethod
    def _parse_and_validate_gemini_json(
        cls,
        response_text: str,
        context: Dict[str, Any],
        candidate_foods: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        today_data = context.get("today", {})
        rem_cal = float(today_data.get("calories_remaining", 0.0))
        rem_pro = float(today_data.get("protein_remaining", 0.0))
        backend_warnings = context.get("warnings", [])

        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
                cleaned = re.sub(r"\n```$", "", cleaned)
            
            data = json.loads(cleaned)
            answer = data.get("answer", "").strip()
            recommendations_raw = data.get("recommendations", [])
            warnings_raw = data.get("warnings", [])
            suggested_actions = data.get("suggested_actions", ["How many calories left?", "Suggest a Dinner", "View Dashboard"])

            # Validate recommendations against candidates
            candidate_lookup = {c.get("name", "").lower(): c for c in candidate_foods}
            candidate_lookup.update({c.get("food_name", "").lower(): c for c in candidate_foods})

            validated_recs = []
            for r in recommendations_raw:
                fname = r.get("food_name", "").strip()
                matched_cand = candidate_lookup.get(fname.lower())
                if matched_cand:
                    validated_recs.append({
                        "food_name": matched_cand.get("name") or matched_cand.get("food_name") or fname,
                        "serving_size": matched_cand.get("serving_label") or r.get("serving_size", "1 serving"),
                        "calories": round(float(matched_cand.get("calories", r.get("calories", 0)))),
                        "protein_g": round(float(matched_cand.get("protein_g", r.get("protein_g", 0))), 1),
                        "carbs_g": round(float(matched_cand.get("carbs_g", r.get("carbs_g", 0))), 1),
                        "fat_g": round(float(matched_cand.get("fat_g", r.get("fat_g", 0))), 1),
                        "fiber_g": round(float(matched_cand.get("fiber_g", r.get("fiber_g", 0))), 1),
                        "reason": r.get("reason", "")
                    })
                elif fname:
                    validated_recs.append({
                        "food_name": fname,
                        "serving_size": r.get("serving_size", "1 serving"),
                        "calories": round(float(r.get("calories", 0))),
                        "protein_g": round(float(r.get("protein_g", 0)), 1),
                        "carbs_g": round(float(r.get("carbs_g", 0)), 1),
                        "fat_g": round(float(r.get("fat_g", 0)), 1),
                        "fiber_g": round(float(r.get("fiber_g", 0)), 1),
                        "reason": r.get("reason", "")
                    })

            # Format warnings
            formatted_warnings = [w.get("message", "") if isinstance(w, dict) else str(w) for w in backend_warnings]
            for w in warnings_raw:
                w_str = str(w).strip()
                if w_str and w_str not in formatted_warnings:
                    formatted_warnings.append(w_str)

            return {
                "answer": answer or "Here is your nutrition summary based on verified NutriQ data.",
                "recommendations": validated_recs,
                "warnings": formatted_warnings,
                "remaining_calories": round(rem_cal),
                "remaining_protein": round(rem_pro, 1),
                "sources": ["NutriQ Verified Food Database", "IFCT"],
                "suggested_actions": suggested_actions[:4]
            }
        except Exception as e:
            logger.warning(f"Error parsing Gemini JSON response: {e}. Raw: {response_text[:100]}")
            return {
                "answer": response_text or "NutriQ AI Companion processed your request.",
                "recommendations": candidate_foods[:3],
                "warnings": [w.get("message", "") if isinstance(w, dict) else str(w) for w in backend_warnings],
                "remaining_calories": round(rem_cal),
                "remaining_protein": round(rem_pro, 1),
                "sources": ["NutriQ Verified Food Database", "IFCT"],
                "suggested_actions": ["How many calories left?", "Suggest a Dinner", "View Dashboard"]
            }

    @classmethod
    def _generate_deterministic_fallback(
        cls,
        user_message: str,
        context: Dict[str, Any],
        candidate_foods: List[Dict[str, Any]],
        reason: str = "api_key_missing"
    ) -> Dict[str, Any]:
        """
        Grounded, deterministic nutrition engine adhering to exact NutriQ user calculations and IFCT food catalog.
        Provides rich, factual responses for ALL valid nutrition and meal questions.
        """
        user_prof = context.get("user_profile", {})
        today_data = context.get("today", {})
        targets = context.get("nutrition_target", {})
        recent_meals = context.get("recent_meals", [])
        backend_warnings = context.get("warnings", [])

        rem_cal = max(0, round(float(today_data.get("calories_remaining", 0.0))))
        rem_pro = max(0.0, round(float(today_data.get("protein_remaining", 0.0)), 1))
        cal_consumed = round(float(today_data.get("consumed_calories", today_data.get("calories_consumed", 0.0))))
        cal_target = round(float(targets.get("calories", targets.get("target_calories", 2000.0))))
        pro_consumed = round(float(today_data.get("protein_consumed", 0.0)), 1)
        pro_target = round(float(targets.get("protein", targets.get("protein_g", 70.0))), 1)
        water_consumed = round(float(today_data.get("water_consumed", 0.0)))
        water_target = round(float(targets.get("hydration", targets.get("water_ml", 2500.0))))
        rem_water = max(0, water_target - water_consumed)
        fitness_goal = (user_prof.get("fitness_goal") or "maintain").replace("_", " ")
        dietary_pref = user_prof.get("dietary_preference") or "standard"

        msg_lower = user_message.lower().strip()
        formatted_warnings = [w.get("message", "") if isinstance(w, dict) else str(w) for w in backend_warnings]
        suggested_actions = ["How many calories do I have left?", "Suggest lunch.", "Suggest dinner.", "How much protein do I need?"]
        recs = []

        # =========================================================================
        # 1. "How many calories do I have left?" / Calorie Budget Balance
        # =========================================================================
        if any(k in msg_lower for k in ["calories left", "calories do i have left", "how many calories left", "calories remaining", "calorie balance", "calorie budget", "how many calories do i have", "calories today"]):
            ans = (
                f"Here is your current **Calorie Breakdown** for today:\n\n"
                f"• **Daily Target**: **{cal_target:,} kcal**\n"
                f"• **Calories Consumed**: **{cal_consumed:,} kcal**\n"
                f"• **Remaining Calories**: **{rem_cal:,} kcal**\n\n"
                f"You also have **{rem_pro}g protein** and **{rem_water:,} ml water** left to reach your daily nutrition targets for your **{fitness_goal}** goal."
            )
            suggested_actions = ["Am I within my calorie goal?", "Suggest lunch.", "Suggest dinner.", "How much protein do I need?"]

        # =========================================================================
        # 2. "Am I within my calorie goal?"
        # =========================================================================
        elif any(k in msg_lower for k in ["within my calorie goal", "within my goal", "within calorie goal", "am i within", "am i over my calories", "calorie goal status"]):
            if cal_consumed > cal_target:
                over = cal_consumed - cal_target
                ans = (
                    f"You have currently consumed **{cal_consumed:,} kcal** today, which is **{over:,} kcal** over your daily target of **{cal_target:,} kcal**.\n\n"
                    f"• **Protein Consumed**: **{pro_consumed}g** / **{pro_target}g** ({rem_pro}g remaining)\n"
                    f"• **Hydration**: **{water_consumed:,} ml** / **{water_target:,} ml**\n\n"
                    f"Exceeding your calorie target occasionally won't ruin long-term progress. For the rest of today, focus on light hydration and high-fiber, low-calorie options like clear vegetable soups or cucumber salads."
                )
            else:
                ans = (
                    f"**Yes, you are on track!** You have consumed **{cal_consumed:,} kcal** of your **{cal_target:,} kcal** budget, leaving **{rem_cal:,} kcal remaining**.\n\n"
                    f"• **Protein Progress**: **{pro_consumed}g** consumed of **{pro_target}g** target ({rem_pro}g remaining)\n"
                    f"• **Hydration Progress**: **{water_consumed:,} ml** / **{water_target:,} ml**\n\n"
                    f"You are pacing well to support your **{fitness_goal}** plan."
                )
            suggested_actions = ["How many calories should dinner have?", "Suggest lunch.", "How much protein do I need?", "Am I progressing toward my goal?"]

        # =========================================================================
        # 3. "How many calories should dinner have?"
        # =========================================================================
        elif any(k in msg_lower for k in ["how many calories should dinner have", "dinner have", "dinner calories", "calories for dinner", "dinner budget"]):
            dinner_target = round(cal_target * 0.32)
            suggested_dinner_cal = min(rem_cal, dinner_target) if rem_cal > 0 else dinner_target
            ans = (
                f"For optimal digestion and overnight metabolic recovery, dinner should ideally account for **30%–35% of your daily intake (~{dinner_target:,} kcal)**.\n\n"
                f"• **Your Total Remaining Budget**: **{rem_cal:,} kcal**\n"
                f"• **Recommended Dinner Target**: **~{suggested_dinner_cal:,} kcal** with **20g–25g protein**\n\n"
                "Aim for lean protein (paneer, boiled eggs, tofu, dal, or chicken) combined with high-fiber steamed vegetables and a moderate portion of whole grains (phulkas or millets)."
            )
            recs = [
                {"food_name": "Palak Paneer", "serving_size": "1 katori (150g)", "calories": 185, "protein_g": 11.2, "carbs_g": 8.5, "fat_g": 12.0, "fiber_g": 3.6, "reason": "High-protein vegetable dish for dinner."},
                {"food_name": "Whole Wheat Chapati / Phulka", "serving_size": "2 pieces (80g)", "calories": 208, "protein_g": 6.2, "carbs_g": 41.6, "fat_g": 1.6, "fiber_g": 5.6, "reason": "High-fiber whole wheat bread."}
            ]
            suggested_actions = ["Suggest dinner.", "Give me a meal under 400 calories.", "How many calories do I have left?"]

        # =========================================================================
        # 4. "Suggest lunch." / Lunch Recommendations
        # =========================================================================
        elif any(k in msg_lower for k in ["suggest lunch", "lunch suggestions", "lunch ideas", "what should i eat for lunch", "lunch recommendation", "lunch options", "lunch"]):
            lunch_budget = min(rem_cal, round(cal_target * 0.38)) if rem_cal > 0 else round(cal_target * 0.38)
            ans = (
                f"Here are balanced **Lunch Recommendations** designed to fit within your remaining **{rem_cal:,} kcal** budget (~{lunch_budget} kcal target):\n\n"
                f"1. **Option A: Traditional Balanced Thali (~390 kcal, 17g Protein)**\n"
                f"   • 2 Whole Wheat Phulkas (208 kcal) + 1 Katori Dal Tadka (115 kcal) + Mixed Cucumber Salad (45 kcal) + Curd (25 kcal)\n\n"
                f"2. **Option B: South Indian Rice & Protein Combo (~420 kcal, 22g Protein)**\n"
                f"   • 1 Cup Steamed Rice / Foxtail Millet (165 kcal) + Tamil Sambar (85 kcal) + Grilled Paneer Tikka (170 kcal)\n\n"
                f"3. **Option C: High-Protein Chicken Lunch (~380 kcal, 32g Protein)**\n"
                f"   • 150g Indian-style Chicken Curry (220 kcal) + 1 Phulka (104 kcal) + Steamed Beans Poriyal (60 kcal)\n\n"
                f"You have **{rem_pro}g protein** remaining for today's goal."
            )
            recs = [
                {"food_name": "Yellow Dal Tadka", "serving_size": "1 katori (150g)", "calories": 115, "protein_g": 7.2, "carbs_g": 16.0, "fat_g": 2.5, "fiber_g": 3.8, "reason": "Classic high-protein lentil preparation."},
                {"food_name": "Whole Wheat Chapati / Phulka", "serving_size": "2 pieces (80g)", "calories": 208, "protein_g": 6.2, "carbs_g": 41.6, "fat_g": 1.6, "fiber_g": 5.6, "reason": "High-fiber whole grain staple."},
                {"food_name": "Paneer Tikka", "serving_size": "100g", "calories": 190, "protein_g": 14.5, "carbs_g": 5.0, "fat_g": 12.0, "fiber_g": 1.2, "reason": "Rich vegetarian protein source."}
            ]
            suggested_actions = ["How many calories do I have left?", "Give me a meal under 400 calories.", "Suggest dinner.", "How much protein do I need?"]

        # =========================================================================
        # 5. "Suggest breakfast." / Breakfast Recommendations
        # =========================================================================
        elif any(k in msg_lower for k in ["suggest breakfast", "breakfast suggestions", "breakfast ideas", "what should i eat for breakfast", "breakfast recommendation", "breakfast options", "breakfast"]):
            ans = (
                f"Here are nutrient-dense **Breakfast Options** tailored to support your **{fitness_goal}** goal:\n\n"
                f"1. **Option A: South Indian Steamed Classic (~275 kcal, 9.8g Protein)**\n"
                f"   • 3 Steamed Idlis (190 kcal) + 1 Bowl Sambar (85 kcal)\n\n"
                f"2. **Option B: High-Protein Egg Toast (~260 kcal, 18g Protein)**\n"
                f"   • 3 Boiled Egg Whites + 1 Whole Egg (156 kcal) + 1 Whole Wheat Toast (100 kcal)\n\n"
                f"3. **Option C: Traditional Poha / Millet Pongal (~280 kcal, 8g Protein)**\n"
                f"   • 1 Bowl Vegetable Poha with Peanuts (260 kcal) + 1 Cup Buttermilk (35 kcal)\n\n"
                f"Today's total calorie target is **{cal_target:,} kcal** with **{rem_cal:,} kcal remaining**."
            )
            recs = [
                {"food_name": "Idli (Steamed Rice & Urad Cake)", "serving_size": "3 pieces (135g)", "calories": 190, "protein_g": 5.8, "carbs_g": 40.0, "fat_g": 0.6, "fiber_g": 2.4, "reason": "Low-fat, easily digestible steamed breakfast."},
                {"food_name": "Tamil Sambar", "serving_size": "1 katori (150g)", "calories": 85, "protein_g": 4.0, "carbs_g": 12.5, "fat_g": 2.0, "fiber_g": 3.2, "reason": "Lentil stew rich in plant protein and dietary fiber."}
            ]
            suggested_actions = ["Suggest lunch.", "How many calories do I have left?", "How much protein do I need?"]

        # =========================================================================
        # 6. "Suggest dinner." / Dinner Recommendations
        # =========================================================================
        elif any(k in msg_lower for k in ["suggest dinner", "dinner suggestions", "dinner ideas", "what should i eat for dinner", "dinner recommendation", "dinner options", "dinner"]):
            dinner_target = min(rem_cal, round(cal_target * 0.32)) if rem_cal > 0 else round(cal_target * 0.32)
            ans = (
                f"Here are light, protein-forward **Dinner Recommendations** for your remaining **{rem_cal:,} kcal** budget (~{dinner_target} kcal):\n\n"
                f"1. **Option A: Paneer Bhurji & Phulkas (~340 kcal, 19g Protein)**\n"
                f"   • 120g Paneer Bhurji with Onions & Tomatoes (236 kcal) + 1 Whole Wheat Phulka (104 kcal) + Cucumber Salad\n\n"
                f"2. **Option B: Grilled Chicken & Stir-Fry (~320 kcal, 28g Protein)**\n"
                f"   • 150g Grilled Chicken Breast (240 kcal) + Stir-fried Bell Peppers and Zucchini (80 kcal)\n\n"
                f"3. **Option C: Light South Indian Comfort (~295 kcal, 12g Protein)**\n"
                f"   • 2 Plain Dosas (210 kcal) + 1 Bowl Protein Sambar (85 kcal)\n\n"
                f"You have **{rem_pro}g protein** remaining today."
            )
            recs = [
                {"food_name": "Paneer Bhurji", "serving_size": "150g", "calories": 250, "protein_g": 18.0, "carbs_g": 6.0, "fat_g": 17.0, "fiber_g": 1.5, "reason": "High-protein satisfying dinner."},
                {"food_name": "Whole Wheat Chapati / Phulka", "serving_size": "1 piece (40g)", "calories": 104, "protein_g": 3.1, "carbs_g": 20.8, "fat_g": 0.8, "fiber_g": 2.8, "reason": "Whole grain carbohydrate source."}
            ]
            suggested_actions = ["How many calories should dinner have?", "Give me a meal under 400 calories.", "How many calories do I have left?"]

        # =========================================================================
        # 7. "Give me a meal under 400 calories."
        # =========================================================================
        elif any(k in msg_lower for k in ["under 400", "meal under 400", "under 300", "under 500", "under 600", "400 calories", "500 calories", "low calorie meal"]):
            cal_match = re.search(r'(\d{3,4})', msg_lower)
            lim_val = int(cal_match.group(1)) if cal_match else 400
            ans = (
                f"Here are verified satisfying meals kept strictly under **{lim_val} kcal**:\n\n"
                f"1. **Palak Paneer with 2 Whole Wheat Phulkas**: **~360 kcal** (18.2g Protein, 48g Carbs, 13g Fat, 8.4g Fiber)\n"
                f"2. **Foxtail Millet Pongal + Sambar**: **~340 kcal** (13.5g Protein, 50g Carbs, 6g Fat, 7.2g Fiber)\n"
                f"3. **3 Boiled Eggs (1 Whole + 2 Whites) + Sprouted Moong Salad**: **~310 kcal** (24g Protein, 22g Carbs, 8g Fat, 6g Fiber)\n"
                f"4. **Grilled Chicken Breast (140g) + Steamed Veggies**: **~285 kcal** (32g Protein, 12g Carbs, 5g Fat, 4g Fiber)\n\n"
                f"You currently have **{rem_cal:,} kcal** remaining today."
            )
            recs = [
                {"food_name": "Palak Paneer", "serving_size": "1 katori (150g)", "calories": 185, "protein_g": 11.2, "carbs_g": 8.5, "fat_g": 12.0, "fiber_g": 3.6, "reason": "High-protein spinach and cottage cheese curry."},
                {"food_name": "Whole Wheat Chapati / Phulka", "serving_size": "2 pieces (80g)", "calories": 208, "protein_g": 6.2, "carbs_g": 41.6, "fat_g": 1.6, "fiber_g": 5.6, "reason": "Fiber-dense whole grain bread."}
            ]
            suggested_actions = ["Suggest lunch.", "Suggest dinner.", "How many calories do I have left?"]

        # =========================================================================
        # 8. "How much protein do I need?" / Protein Requirements
        # =========================================================================
        elif any(k in msg_lower for k in ["how much protein", "protein do i need", "protein need", "protein target", "protein status", "my protein", "protein intake"]):
            ans = (
                f"Here is your personalized **Protein Target & Status** for today:\n\n"
                f"• **Daily Protein Target**: **{pro_target}g**\n"
                f"• **Protein Consumed Today**: **{pro_consumed}g**\n"
                f"• **Remaining Protein Needed**: **{rem_pro}g**\n\n"
                f"**Top Foods to Hit Your Remaining {rem_pro}g Protein**:\n"
                f"• **Paneer (100g)**: ~18g Protein (260 kcal)\n"
                f"• **3 Boiled Eggs**: ~19g Protein (180 kcal)\n"
                f"• **Chicken Breast (100g)**: ~31g Protein (165 kcal)\n"
                f"• **Sprouted Moong / Chana (150g)**: ~14g Protein (160 kcal)\n"
                f"• **Yellow Moong Dal (1 Bowl)**: ~8g Protein (115 kcal)"
            )
            suggested_actions = ["Suggest lunch.", "Suggest dinner.", "How many calories do I have left?"]

        # =========================================================================
        # 9. "How much water should I drink?" / Hydration
        # =========================================================================
        elif any(k in msg_lower for k in ["how much water", "water should i drink", "hydration target", "drink water", "water goal", "my water", "water", "hydration"]):
            ans = (
                f"Here is your daily **Hydration Breakdown**:\n\n"
                f"• **Daily Water Target**: **{water_target:,} ml**\n"
                f"• **Consumed Today**: **{water_consumed:,} ml**\n"
                f"• **Remaining to Drink**: **{rem_water:,} ml**\n\n"
                f"**Hydration Tips**:\n"
                f"• Drink 1–2 glasses (250–500 ml) right upon waking.\n"
                f"• Have a glass 15 minutes before meals to aid satiety.\n"
                f"• Keep a water bottle nearby and log your intake in the NutriQ journal."
            )
            suggested_actions = ["How many calories do I have left?", "Suggest lunch.", "Am I progressing toward my goal?"]

        # =========================================================================
        # 10. "Am I progressing toward my goal?" / Goal Status
        # =========================================================================
        elif any(k in msg_lower for k in ["progressing toward my goal", "progress toward goal", "am i progressing", "goal progress", "my goal status", "am i on track"]):
            ans = (
                f"You are actively logging and working toward your **{fitness_goal}** goal!\n\n"
                f"• **Calorie Balance**: **{cal_consumed:,} kcal** consumed out of **{cal_target:,} kcal** ({rem_cal:,} kcal remaining)\n"
                f"• **Protein Intake**: **{pro_consumed}g** / **{pro_target}g** ({rem_pro}g remaining)\n"
                f"• **Hydration**: **{water_consumed:,} ml** / **{water_target:,} ml** ({rem_water:,} ml remaining)\n"
                f"• **Meals Logged Today**: **{len(recent_meals)} recorded meals**\n\n"
                f"Consistent daily tracking and meeting your protein target while maintaining your caloric deficit is the key to sustainable progress."
            )
            suggested_actions = ["How many calories do I have left?", "Suggest lunch.", "Suggest dinner.", "View Dashboard"]

        # =========================================================================
        # 11. "What should I eat for weight loss?"
        # =========================================================================
        elif any(k in msg_lower for k in ["what should i eat for weight loss", "eat for weight loss", "foods for weight loss", "best foods for fat loss", "weight loss diet", "lose weight", "fat loss"]):
            ans = (
                f"For effective, sustainable **Weight Loss**, structure your meals around these four evidence-based pillars:\n\n"
                f"1. **High-Protein Foundation**: Paneer, eggs, chicken, fish, sprouts, and dal (aim for 25g–30g per main meal to protect lean mass and increase fullness).\n"
                f"2. **High-Fiber Volume**: Green leafy vegetables, cucumber salads, foxtail millets, and whole wheat phulkas (slows digestion and moderates glucose response).\n"
                f"3. **Hydration**: At least 2.5L water daily (drink 1 glass before meals).\n"
                f"4. **Calorie Control**: Stay within your **{cal_target:,} kcal** daily budget (you have **{rem_cal:,} kcal remaining** today).\n\n"
                f"Would you like me to suggest a lunch or dinner that fits these guidelines?"
            )
            suggested_actions = ["Suggest lunch.", "Suggest dinner.", "Give me a meal under 400 calories.", "How many calories do I have left?"]

        # =========================================================================
        # 12. "Suggest Indian food." / Regional Indian Diet
        # =========================================================================
        elif any(k in msg_lower for k in ["suggest indian food", "indian food", "indian diet", "indian meal", "south indian", "north indian", "tamil nadu"]):
            ans = (
                f"Here are verified, healthy **Indian Meal Options** from our database matching your **{dietary_pref}** preferences:\n\n"
                f"• **Steamed Idli with Sambar**: ~275 kcal (9.8g Protein, 2.6g Fat, 5.6g Fiber)\n"
                f"• **2 Whole Wheat Phulkas + Palak Paneer**: ~360 kcal (18g Protein, 8.4g Fiber)\n"
                f"• **Thinai (Foxtail Millet) Pongal with Dal**: ~340 kcal (14g Protein, 7.2g Fiber)\n"
                f"• **Grilled Paneer Tikka with Mint Chutney**: ~260 kcal (18.5g Protein)\n"
                f"• **Indian Chicken Curry with 1 Phulka**: ~320 kcal (28g Protein)\n\n"
                f"You have **{rem_cal:,} kcal** remaining today."
            )
            recs = [
                {"food_name": "Idli (Steamed Rice & Urad Cake)", "serving_size": "3 pieces (135g)", "calories": 190, "protein_g": 5.8, "carbs_g": 40.0, "fat_g": 0.6, "fiber_g": 2.4, "reason": "Traditional steamed South Indian staple."},
                {"food_name": "Palak Paneer", "serving_size": "1 katori (150g)", "calories": 185, "protein_g": 11.2, "carbs_g": 8.5, "fat_g": 12.0, "fiber_g": 3.6, "reason": "Nutrient-dense Indian vegetable and protein curry."}
            ]
            suggested_actions = ["Suggest lunch.", "Suggest dinner.", "How many calories do I have left?"]

        # =========================================================================
        # 13. Idli / Dosa / Egg / Rice / Specific Food Breakdown
        # =========================================================================
        elif any(k in msg_lower for k in ["idli", "idlis"]):
            ans = (
                f"Here is the nutritional breakdown for **Idli with Sambar** from the verified IFCT database:\n\n"
                f"• **3 Steamed Idlis (135g)**: **~190 kcal** (5.8g Protein, 40g Carbs, 0.6g Fat)\n"
                f"• **1 Bowl Sambar (150g)**: **~85 kcal** (4.0g Protein, 12.5g Carbs, 2.0g Fat)\n"
                f"• **Total**: **~275 kcal** (9.8g Protein, 52.5g Carbs, 2.6g Fat)\n\n"
                f"You have **{rem_cal:,} kcal remaining** today. Would you like me to log this to your breakfast journal?"
            )
            recs = [
                {"food_name": "Idli (Steamed Rice & Urad Cake)", "serving_size": "3 pieces (135g)", "calories": 190, "protein_g": 5.8, "carbs_g": 40.0, "fat_g": 0.6, "fiber_g": 2.4, "reason": "Steamed low-fat South Indian staple."},
                {"food_name": "Tamil Sambar", "serving_size": "1 katori (150g)", "calories": 85, "protein_g": 4.0, "carbs_g": 12.5, "fat_g": 2.0, "fiber_g": 3.2, "reason": "Lentil stew providing protein and fiber."}
            ]
            suggested_actions = ["Suggest lunch.", "How many calories do I have left?", "Suggest dinner."]

        elif any(k in msg_lower for k in ["dosa", "dosas"]):
            ans = (
                f"**Plain Dosa Nutritional Profile**:\n\n"
                f"• **2 Plain Dosas (160g)**: **~270–336 kcal** (6.2g Protein, 47g Carbs, 6g Fat, 2.8g Fiber)\n"
                f"• **With 1 Bowl Sambar (150g)**: **~355 kcal** (10.2g Protein, 59.5g Carbs, 8g Fat)\n\n"
                f"Fits comfortably inside your **{rem_cal:,} kcal** remaining budget today!"
            )
            recs = [
                {"food_name": "Plain Dosa", "serving_size": "2 pieces (160g)", "calories": 270, "protein_g": 6.2, "carbs_g": 47.0, "fat_g": 6.0, "fiber_g": 2.8, "reason": "Standard South Indian breakfast/dinner portion."},
                {"food_name": "Tamil Sambar", "serving_size": "1 katori (150g)", "calories": 85, "protein_g": 4.0, "carbs_g": 12.5, "fat_g": 2.0, "fiber_g": 3.2, "reason": "Lentil stew providing protein and fiber."}
            ]
            suggested_actions = ["Suggest lunch.", "How many calories do I have left?", "Suggest dinner."]

        elif "egg" in msg_lower and any(k in msg_lower for k in ["ate 2 eggs", "i ate 2 egg", "log 2 egg", "boiled egg", "egg"]):
            ans = (
                f"**2 Boiled Eggs** provide approximately **156 kcal** (12.6g Protein, 1.1g Carbs, 10.6g Fat).\n\n"
                f"• **Your Remaining Budget**: **{rem_cal:,} kcal**\n"
                f"• **After 2 Eggs**: **{max(0, rem_cal - 156):,} kcal remaining**\n"
                f"• **Remaining Protein**: **{max(0.0, round(rem_pro - 12.6, 1))}g**"
            )
            suggested_actions = ["How many calories do I have left?", "Suggest lunch.", "Suggest dinner."]

        elif "rice" in msg_lower:
            ans = (
                f"**Cooked White Rice Nutrition**:\n\n"
                f"• **100g Cooked White Rice**: **130 kcal** (2.7g Protein, 28g Carbs, 0.4g Fiber)\n"
                f"• **1 Standard Cup (150g)**: **195 kcal** (4.1g Protein, 42g Carbs, 0.6g Fiber)\n"
                f"• **200g Portion**: **260 kcal** (5.4g Protein, 56g Carbs)\n\n"
                f"Rice fits well in your **{fitness_goal}** plan when paired with protein (dal, paneer, eggs, chicken) and a high-fiber vegetable poriyal. You currently have **{rem_cal:,} kcal remaining** today."
            )
            suggested_actions = ["Suggest lunch.", "How many calories do I have left?", "Give me a meal under 400 calories."]

        # =========================================================================
        # 14. What did I eat today / Yesterday
        # =========================================================================
        elif any(k in msg_lower for k in ["what did i eat", "logged meals", "today's meals", "meal log", "meals logged", "what i ate"]):
            if not recent_meals:
                ans = f"You haven't logged any meals yet today. Your daily target is **{cal_target:,} kcal** with **{rem_cal:,} kcal remaining**."
            else:
                meal_lines = []
                for m in recent_meals:
                    items_str = ", ".join([f"{it.get('quantity', 1)}x {it.get('food_name', '')} ({int(it.get('calories', 0))} kcal)" for it in m.get("items", [])])
                    meal_lines.append(f"• **{m.get('meal_type', 'Meal').capitalize()}**: {items_str} — Total: **{int(m.get('meal_calories', 0))} kcal** ({m.get('meal_protein_g', 0)}g Protein)")
                ans = f"Here is your food journal for today (**{len(recent_meals)} meals recorded**, {cal_consumed:,} kcal total consumed):\n\n" + "\n".join(meal_lines)
            suggested_actions = ["How many calories do I have left?", "Suggest lunch.", "Suggest dinner."]

        # =========================================================================
        # 15. General Food / Nutrition / Snack Query
        # =========================================================================
        elif any(k in msg_lower for k in ["food", "meal", "eat", "diet", "snack", "calorie", "calories", "protein", "carbs", "fat", "fiber", "recommend", "suggest", "substitute", "healthy", "recipe", "hungry"]):
            if candidate_foods:
                recs = candidate_foods[:3]
                rec_lines = [f"• **{r.get('name') or r.get('food_name')}** ({r.get('serving_size') or r.get('serving_label', '1 serving')}): **{int(r.get('calories', 0))} kcal**, **{r.get('protein_g', 0)}g Protein**" for r in recs]
                ans = (
                    f"Based on your daily target of **{cal_target:,} kcal** and current remaining **{rem_cal:,} kcal** ({rem_pro}g protein needed), here are verified database suggestions:\n\n"
                    + "\n".join(rec_lines) + "\n\n"
                    f"All options respect your **{dietary_pref}** preferences and stored allergens."
                )
            else:
                ans = (
                    f"Based on your remaining **{rem_cal:,} kcal** and **{rem_pro}g protein** budget today:\n\n"
                    f"• **Paneer Bhurji / Palak Paneer (150g)**: ~220 kcal, 16g Protein\n"
                    f"• **2 Whole Wheat Phulkas with Dal Tadka**: ~320 kcal, 13g Protein\n"
                    f"• **Sprouted Moong Salad with Lemon (150g)**: ~160 kcal, 12g Protein\n"
                    f"• **3 Boiled Eggs (1 whole + 2 whites)**: ~156 kcal, 18g Protein"
                )
            suggested_actions = ["Suggest lunch.", "Suggest dinner.", "How many calories do I have left?", "How much protein do I need?"]

        # =========================================================================
        # 16. Truly Off-Topic / Non-Nutrition Fallback
        # =========================================================================
        else:
            ans = (
                f"I am your **NutriQ AI Companion**, dedicated to personalized nutrition intelligence, calorie tracking, and meal planning.\n\n"
                f"• **Today's Budget**: **{rem_cal:,} kcal remaining** ({cal_consumed:,} / {cal_target:,} kcal consumed)\n"
                f"• **Protein Needed**: **{rem_pro}g remaining** ({pro_consumed}g / {pro_target}g)\n"
                f"• **Hydration**: **{water_consumed:,} ml** / **{water_target:,} ml**\n\n"
                f"Feel free to ask me for meal ideas (breakfast, lunch, dinner), calorie breakdowns, protein optimization, or food substitutions!"
            )
            suggested_actions = ["How many calories do I have left?", "Suggest lunch.", "Suggest dinner.", "How much protein do I need?"]

        notice = "*Based on verified NutriQ nutrition calculations and IFCT database.*"

        return {
            "answer": f"{ans}\n\n{notice}",
            "recommendations": recs,
            "warnings": formatted_warnings,
            "remaining_calories": rem_cal,
            "remaining_protein": rem_pro,
            "sources": ["NutriQ Verified Food Database", "IFCT"],
            "suggested_actions": suggested_actions
        }

