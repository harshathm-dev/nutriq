import json
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_
from sqlalchemy.orm import selectinload

from app.models.chat import ChatSession, ChatMessage
from app.models.base import utc_now

logger = logging.getLogger(__name__)


class ChatService:
    @staticmethod
    def generate_smart_title(user_prompt: str) -> str:
        """
        Generates a concise, meaningful title from the first user message.
        Examples:
        - "How many calories do I have left?" -> "Calorie Progress"
        - "What should I eat for dinner?" -> "Dinner Suggestions"
        - "How much protein do I need?" -> "Protein Intake"
        """
        if not user_prompt or not user_prompt.strip():
            return "New Conversation"

        text = user_prompt.strip().lower()

        # Domain-specific keyword matching
        if "calorie" in text or "calories" in text or "budget" in text or "deficit" in text:
            if "left" in text or "remaining" in text or "progress" in text or "status" in text or "goal" in text:
                return "Calorie Progress"
            return "Calorie Breakdown"

        if "protein" in text:
            if "need" in text or "intake" in text or "much" in text or "requirement" in text:
                return "Protein Intake"
            return "Protein Sources & Targets"

        if "dinner" in text:
            return "Dinner Suggestions"

        if "lunch" in text:
            return "Lunch Suggestions"

        if "breakfast" in text:
            return "Breakfast Ideas"

        if "snack" in text or "snacks" in text:
            return "Healthy Snack Ideas"

        if "weight loss" in text or "lose weight" in text or "fat loss" in text:
            return "Weight Loss Plan"

        if "weight gain" in text or "muscle gain" in text or "bulk" in text:
            return "Muscle Gain Plan"

        if "weight" in text:
            return "Weight Progress"

        if "water" in text or "hydration" in text or "drink" in text:
            return "Hydration Tracking"

        if "meal plan" in text or "diet plan" in text:
            return "Meal Planning"

        if any(w in text for w in ["dosa", "idli", "roti", "chapati", "biryani", "paneer", "dal", "curry", "sambar", "khichdi"]):
            if "dosa" in text:
                return "Dosa Nutrition"
            if "idli" in text:
                return "Idli Nutrition"
            if "paneer" in text:
                return "Paneer Nutrition"
            if "rice" in text:
                return "Rice & Carbohydrates"
            return "Indian Food Ideas"

        if "carb" in text or "carbs" in text or "carbohydrate" in text:
            return "Carbohydrate Intake"

        if "fat" in text or "fats" in text or "lipid" in text:
            return "Dietary Fats Breakdown"

        if "workout" in text or "exercise" in text or "cardio" in text or "gym" in text or "steps" in text:
            return "Activity & Calorie Burn"

        if "progress" in text or "summary" in text or "how did i do" in text or "report" in text:
            return "Nutrition Progress Summary"

        # General clean title extraction: strip common questions & fillers
        cleaned = re.sub(
            r"^(can you tell me|can you suggest|can i eat|could you please|how many|how much|how to|what is|what are|what should i|give me|suggest a|suggest me|i want to know|tell me about|is it okay to|why is)\s+",
            "",
            user_prompt.strip(),
            flags=re.IGNORECASE
        )
        cleaned = re.sub(r"[?!.,;:]+$", "", cleaned).strip()

        words = cleaned.split()
        if not words:
            return "New Conversation"

        # Take up to 4 significant words
        short_words = words[:4]
        title = " ".join(short_words).title()
        if len(title) > 32:
            title = title[:30] + "..."

        return title or "New Conversation"

    @classmethod
    def _format_message(cls, msg: ChatMessage) -> Dict[str, Any]:
        meta = {}
        if msg.metadata_json:
            try:
                meta = json.loads(msg.metadata_json)
            except Exception:
                meta = {}

        return {
            "id": msg.id,
            "messageId": msg.id,
            "session_id": msg.session_id,
            "conversationId": msg.session_id,
            "user_id": msg.user_id,
            "userId": msg.user_id,
            "role": msg.role,
            "content": msg.content,
            "metadata_json": msg.metadata_json,
            "metadata": meta,
            "created_at": msg.created_at,
            "timestamp": msg.created_at
        }

    @classmethod
    def _format_session(cls, s: ChatSession, include_messages: bool = False) -> Dict[str, Any]:
        msgs = s.messages or []
        last_msg = msgs[-1].content if msgs else None
        if last_msg and len(last_msg) > 60:
            last_msg = last_msg[:60] + "..."

        data = {
            "id": s.id,
            "conversationId": s.id,
            "user_id": s.user_id,
            "userId": s.user_id,
            "title": s.title or "New Conversation",
            "summary": s.summary,
            "created_at": s.created_at,
            "createdAt": s.created_at,
            "updated_at": s.updated_at,
            "updatedAt": s.updated_at,
            "message_count": len(msgs),
            "last_message_preview": last_msg
        }
        if include_messages:
            data["messages"] = [cls._format_message(m) for m in msgs]
        return data

    @classmethod
    async def get_or_create_current_session(cls, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """
        Fetches the user's latest active chat session with messages,
        or creates a new session if none exists.
        """
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.messages))
            .order_by(ChatSession.updated_at.desc())
            .limit(1)
        )
        res = await session.execute(stmt)
        chat_sess = res.scalars().first()

        if not chat_sess:
            chat_sess = ChatSession(
                user_id=user_id,
                title="New Conversation",
                created_at=utc_now(),
                updated_at=utc_now()
            )
            session.add(chat_sess)
            await session.commit()
            # Reload with messages relationship
            res = await session.execute(
                select(ChatSession)
                .where(ChatSession.id == chat_sess.id)
                .options(selectinload(ChatSession.messages))
            )
            chat_sess = res.scalars().first()

        return cls._format_session(chat_sess, include_messages=True)

    @classmethod
    async def get_user_sessions(
        cls,
        session: AsyncSession,
        user_id: str,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns all chat sessions for the user sorted by updated_at DESC.
        Optionally filters by title or message content.
        """
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.messages))
            .order_by(ChatSession.updated_at.desc())
        )
        res = await session.execute(stmt)
        sessions = res.scalars().all()

        result = []
        q = (search_query or "").strip().lower()

        for s in sessions:
            msgs = s.messages or []
            # Optional search filtering
            if q:
                title_matches = q in (s.title or "").lower()
                msg_matches = any(q in (m.content or "").lower() for m in msgs)
                if not (title_matches or msg_matches):
                    continue

            result.append(cls._format_session(s, include_messages=False))

        return result

    @classmethod
    async def get_session_detail(
        cls,
        session: AsyncSession,
        user_id: str,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches a specific session and its messages ensuring user isolation.
        """
        stmt = (
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.messages))
        )
        res = await session.execute(stmt)
        s = res.scalars().first()
        if not s:
            return None
        return cls._format_session(s, include_messages=True)

    @classmethod
    async def create_session(
        cls,
        session: AsyncSession,
        user_id: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explicitly creates a new chat session.
        """
        clean_title = title.strip() if (title and title.strip()) else "New Conversation"
        chat_sess = ChatSession(
            user_id=user_id,
            title=clean_title,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        session.add(chat_sess)
        await session.commit()
        await session.refresh(chat_sess)
        # Reload with empty messages
        res = await session.execute(
            select(ChatSession)
            .where(ChatSession.id == chat_sess.id)
            .options(selectinload(ChatSession.messages))
        )
        chat_sess = res.scalars().first()
        return cls._format_session(chat_sess, include_messages=True)

    @classmethod
    async def update_session_title(
        cls,
        session: AsyncSession,
        user_id: str,
        session_id: str,
        new_title: str
    ) -> Optional[Dict[str, Any]]:
        """
        Renames a conversation title.
        """
        stmt = (
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.messages))
        )
        res = await session.execute(stmt)
        chat_sess = res.scalars().first()
        if not chat_sess:
            return None

        clean_title = new_title.strip() if new_title and new_title.strip() else "New Conversation"
        chat_sess.title = clean_title
        chat_sess.updated_at = utc_now()
        await session.commit()
        await session.refresh(chat_sess)
        return cls._format_session(chat_sess, include_messages=False)

    @classmethod
    async def delete_session(cls, session: AsyncSession, user_id: str, session_id: str) -> bool:
        """
        Deletes a chat session and all its messages.
        """
        stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        res = await session.execute(stmt)
        chat_sess = res.scalars().first()
        if not chat_sess:
            return False

        await session.delete(chat_sess)
        await session.commit()
        return True

    @classmethod
    async def save_message(
        cls,
        session: AsyncSession,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """
        Saves a single message to the specified session and updates session timestamp/title.
        """
        # Validate session ownership
        sess_stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        sess_res = await session.execute(sess_stmt)
        chat_sess = sess_res.scalars().first()
        if not chat_sess:
            raise ValueError("Chat session not found or unauthorized")

        meta_json = json.dumps(metadata) if metadata else "{}"
        msg = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            metadata_json=meta_json,
            created_at=utc_now()
        )
        session.add(msg)

        # Update session timestamp
        chat_sess.updated_at = utc_now()

        # If title is default, update with intelligent title from first user message
        if role == "user" and (chat_sess.title in ["New Conversation", "Today's Nutrition", "New Chat"] or not chat_sess.title):
            smart_title = cls.generate_smart_title(content)
            chat_sess.title = smart_title

        await session.commit()
        await session.refresh(msg)
        return msg

    @classmethod
    async def get_session_memory(
        cls,
        session: AsyncSession,
        session_id: str,
        limit: int = 15
    ) -> List[Dict[str, str]]:
        """
        Retrieves recent conversation history for Gemini conversational context.
        """
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        res = await session.execute(stmt)
        msgs = list(res.scalars().all())
        msgs.reverse()  # Chronological order

        return [{"role": m.role, "content": m.content} for m in msgs]
