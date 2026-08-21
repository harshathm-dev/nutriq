import csv
import io
import json
import html
from collections import defaultdict
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.profile import UserProfile
from app.models.goal import Goal
from app.models.meal import Meal, MealItem
from app.models.tracking import Water, Exercise, WeightHistory
from app.models.privacy import ConsentRecord
from app.services.nutrition_engine import NutritionEngine

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


def format_csv_date(dt_val: Any) -> str:
    """
    Safely extracts strictly YYYY-MM-DD from datetime, date, or date-like strings.
    Guarantees no numeric serial dates, no timestamps in date columns, and no Excel ######## overflow.
    """
    if not dt_val:
        return ""
    if isinstance(dt_val, (datetime, date)):
        return dt_val.strftime("%Y-%m-%d")
    s = str(dt_val).strip()
    if "T" in s:
        s = s.split("T")[0]
    elif " " in s:
        s = s.split(" ")[0]
    return s[:10]


def format_csv_time(dt_val: Any) -> str:
    """
    Safely extracts strictly HH:mm:ss from datetime, time, or timestamp strings.
    Never includes fractional seconds or timezone suffixes.
    """
    if not dt_val:
        return ""
    if isinstance(dt_val, datetime):
        return dt_val.strftime("%H:%M:%S")
    s = str(dt_val).strip()
    if "T" in s:
        t_part = s.split("T", 1)[1]
    elif " " in s:
        t_part = s.split(" ", 1)[1]
    else:
        return ""
    t_part = t_part.rstrip("Z").split("+")[0].split("-")[0].split(".")[0]
    return t_part[:8]


def format_pdf_date(dt_val: Any) -> str:
    """
    Formats a datetime or date string into human-readable e.g. '20 Aug 2026'.
    Guarantees non-empty output if valid date exists.
    """
    if not dt_val:
        return "-"
    if isinstance(dt_val, (datetime, date)):
        return dt_val.strftime("%d %b %Y")
    s = str(dt_val).strip()
    try:
        if "T" in s:
            d_part = s.split("T")[0]
            parsed = date.fromisoformat(d_part)
            return parsed.strftime("%d %b %Y")
        elif " " in s:
            d_part = s.split(" ")[0]
            parsed = date.fromisoformat(d_part)
            return parsed.strftime("%d %b %Y")
        else:
            parsed = date.fromisoformat(s[:10])
            return parsed.strftime("%d %b %Y")
    except Exception:
        return s[:10] if len(s) >= 10 else s


def format_pdf_datetime(dt_val: Any) -> str:
    """
    Formats a datetime string into e.g. '20 Aug 2026, 01:30 PM' or '20 Aug 2026'.
    """
    if not dt_val:
        return "-"
    if isinstance(dt_val, datetime):
        return dt_val.strftime("%d %b %Y, %I:%M %p")
    if isinstance(dt_val, date):
        return dt_val.strftime("%d %b %Y")
    s = str(dt_val).strip()
    try:
        if " " in s:
            parts = s.split(" ")
            d_part = parts[0]
            t_part = parts[1][:5]
            parsed_d = date.fromisoformat(d_part)
            return f"{parsed_d.strftime('%d %b %Y')} {t_part}"
        elif "T" in s:
            parts = s.split("T")
            d_part = parts[0]
            t_part = parts[1][:5]
            parsed_d = date.fromisoformat(d_part)
            return f"{parsed_d.strftime('%d %b %Y')} {t_part}"
        return format_pdf_date(s)
    except Exception:
        return s


def esc(val: Any) -> str:
    """Safely escape text for ReportLab XML/HTML-like Paragraph formatting."""
    if val is None:
        return ""
    return html.escape(str(val))


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and draw total page numbers and footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header rule & mini text (on page 2+)
        if self._pageNumber > 1:
            self.drawString(40, 760, "NutriQ Personal Nutrition Report")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(40, 752, 572, 752)
        
        # Footer rule & pagination
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(40, 42, 572, 42)
        
        footer_text = f"Page {self._pageNumber} of {page_count}  •  NutriQ Nutrition Intelligence"
        self.drawRightString(572, 30, footer_text)
        self.drawString(40, 30, "Confidential • Generated for Personal Wellness Reference")
        self.restoreState()


class ExportDataService:
    @classmethod
    async def get_normalized_export_snapshot(cls, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """
        Single, unified data retrieval pipeline. Queries the NutriQ database once
        and constructs a complete normalized export snapshot.
        """
        # User record
        user_stmt = select(User).where(User.id == user_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        # Profile
        prof_stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        prof_res = await session.execute(prof_stmt)
        prof = prof_res.scalar_one_or_none()

        profile_dict = {}
        targets_dict = {}
        if prof:
            profile_dict = {
                "name": prof.name,
                "age": prof.age,
                "gender": prof.gender,
                "height_cm": prof.height_cm,
                "weight_kg": prof.weight_kg,
                "activity_level": prof.activity_level,
                "fitness_goal": prof.fitness_goal,
                "dietary_preference": prof.dietary_preference,
                "food_preferences": prof.food_preferences
            }
            # Deterministic calculated targets
            calc_targets = NutritionEngine.calculate_targets(
                weight_kg=prof.weight_kg,
                height_cm=prof.height_cm,
                age=prof.age,
                gender=prof.gender,
                activity_level=prof.activity_level or "moderately_active",
                fitness_goal=prof.fitness_goal or "maintain",
                dietary_preference=prof.dietary_preference or "standard"
            )
            targets_dict = {
                "daily_calories_target": calc_targets.get("target_calories"),
                "protein_target_g": calc_targets.get("protein_g"),
                "carbohydrates_target_g": calc_targets.get("carbs_g"),
                "fat_target_g": calc_targets.get("fat_g"),
                "water_target_ml": calc_targets.get("water_ml"),
                "bmr_kcal": calc_targets.get("bmr"),
                "tdee_kcal": calc_targets.get("tdee")
            }

        # Goals
        goals_stmt = select(Goal).where(Goal.user_id == user_id).order_by(desc(Goal.created_at))
        goals_res = await session.execute(goals_stmt)
        goals_list = [
            {
                "goal_type": g.goal_type,
                "current_weight_kg": g.current_weight_kg,
                "target_weight_kg": g.target_weight_kg,
                "desired_rate": g.desired_rate,
                "target_date": g.target_date.strftime("%Y-%m-%d") if g.target_date else None,
                "active": g.active,
                "created_at": g.created_at.strftime("%Y-%m-%d %H:%M:%S") if g.created_at else None
            }
            for g in goals_res.scalars().all()
        ]

        # Meals with items
        meals_stmt = select(Meal).where(Meal.user_id == user_id).options(
            selectinload(Meal.items)
        ).order_by(desc(Meal.occurred_at))
        meals_res = await session.execute(meals_stmt)
        meals_list = []
        for m in meals_res.scalars().all():
            m_items = [
                {
                    "food_name": item.food_name,
                    "quantity": item.quantity,
                    "serving_unit": item.serving_unit,
                    "grams": item.grams,
                    "calories": round(item.calories, 1),
                    "protein_g": round(item.protein_g, 1),
                    "carbs_g": round(item.carbs_g, 1),
                    "fat_g": round(item.fat_g, 1),
                    "fiber_g": round(item.fiber_g or 0.0, 1)
                }
                for item in m.items
            ]
            tot_cal = round(sum(i["calories"] for i in m_items), 1)
            tot_pro = round(sum(i["protein_g"] for i in m_items), 1)
            tot_carb = round(sum(i["carbs_g"] for i in m_items), 1)
            tot_fat = round(sum(i["fat_g"] for i in m_items), 1)

            meals_list.append({
                "id": m.id,
                "meal_type": m.meal_type,
                "occurred_at": m.occurred_at.strftime("%Y-%m-%d %H:%M:%S") if m.occurred_at else None,
                "source": m.source,
                "total_calories": tot_cal,
                "total_protein_g": tot_pro,
                "total_carbs_g": tot_carb,
                "total_fat_g": tot_fat,
                "items": m_items
            })

        # Water logs
        water_stmt = select(Water).where(Water.user_id == user_id).order_by(desc(Water.recorded_at))
        water_res = await session.execute(water_stmt)
        water_list = [
            {
                "amount_ml": w.amount_ml,
                "recorded_at": w.recorded_at.strftime("%Y-%m-%d %H:%M:%S") if w.recorded_at else None
            }
            for w in water_res.scalars().all()
        ]

        # Weight history
        weight_stmt = select(WeightHistory).where(WeightHistory.user_id == user_id).order_by(desc(WeightHistory.recorded_at))
        weight_res = await session.execute(weight_stmt)
        weight_list = [
            {
                "weight_kg": wt.weight_kg,
                "recorded_at": wt.recorded_at.strftime("%Y-%m-%d %H:%M:%S") if wt.recorded_at else None
            }
            for wt in weight_res.scalars().all()
        ]

        # Exercise history
        ex_stmt = select(Exercise).where(Exercise.user_id == user_id).order_by(desc(Exercise.recorded_at))
        ex_res = await session.execute(ex_stmt)
        ex_list = [
            {
                "type": e.type,
                "duration_min": e.duration_min,
                "calories_burned_est": e.calories_burned_est,
                "recorded_at": e.recorded_at.strftime("%Y-%m-%d %H:%M:%S") if e.recorded_at else None
            }
            for e in ex_res.scalars().all()
        ]


        # Consent records
        consent_stmt = select(ConsentRecord).where(ConsentRecord.user_id == user_id).order_by(desc(ConsentRecord.accepted_at))
        consent_res = await session.execute(consent_stmt)
        consent_list = [
            {
                "consent_type": cr.consent_type,
                "version": cr.version,
                "accepted_at": cr.accepted_at.strftime("%Y-%m-%d %H:%M:%S") if cr.accepted_at else None
            }
            for cr in consent_res.scalars().all()
        ]

        # Aggregate Daily Nutrition Summaries
        daily_map = defaultdict(lambda: {
            "calories": 0.0,
            "protein_g": 0.0,
            "carbs_g": 0.0,
            "fat_g": 0.0,
            "fiber_g": 0.0,
            "meal_count": 0,
            "water_ml": 0.0
        })

        for m in meals_list:
            dt_raw = m.get("occurred_at")
            if dt_raw:
                d_key = dt_raw.split(" ")[0]
                daily_map[d_key]["calories"] += m.get("total_calories", 0.0)
                daily_map[d_key]["protein_g"] += m.get("total_protein_g", 0.0)
                daily_map[d_key]["carbs_g"] += m.get("total_carbs_g", 0.0)
                daily_map[d_key]["fat_g"] += m.get("total_fat_g", 0.0)
                for it in m.get("items", []):
                    daily_map[d_key]["fiber_g"] += it.get("fiber_g", 0.0)
                daily_map[d_key]["meal_count"] += 1

        for w in water_list:
            dt_raw = w.get("recorded_at")
            if dt_raw:
                d_key = dt_raw.split(" ")[0]
                daily_map[d_key]["water_ml"] += w.get("amount_ml", 0.0)

        nutrition_summary_list = []
        for d_key in sorted(daily_map.keys(), reverse=True):
            entry = daily_map[d_key]
            nutrition_summary_list.append({
                "date": d_key,
                "total_calories": round(entry["calories"], 1),
                "total_protein_g": round(entry["protein_g"], 1),
                "total_carbs_g": round(entry["carbs_g"], 1),
                "total_fat_g": round(entry["fat_g"], 1),
                "total_fiber_g": round(entry["fiber_g"], 1),
                "total_water_ml": round(entry["water_ml"], 1),
                "meal_count": entry["meal_count"]
            })

        now_utc = datetime.now(timezone.utc)
        return {
            "export_metadata": {
                "application": "NutriQ",
                "export_date": now_utc.strftime("%Y-%m-%d"),
                "generated_at": now_utc.isoformat(),
                "format_version": "1.0"
            },
            "profile": profile_dict,
            "nutrition_targets": targets_dict,
            "goals": goals_list,
            "meals": meals_list,
            "nutrition_summary": nutrition_summary_list,
            "water_logs": water_list,
            "weight_history": weight_list,
            "exercise_history": ex_list,
            "consent_records": consent_list
        }

    # =========================================================================
    # JSON GENERATOR
    # =========================================================================
    @classmethod
    def generate_json(cls, snapshot: Dict[str, Any]) -> str:
        """Serializes the snapshot into pretty-printed, human-readable UTF-8 JSON."""
        return json.dumps(snapshot, indent=2, ensure_ascii=False)

    # =========================================================================
    # CSV GENERATOR
    # =========================================================================
    @classmethod
    def generate_csv(cls, snapshot: Dict[str, Any]) -> str:
        """
        Generates a spreadsheet-ready CSV with all itemized meal logs, portions,
        macros, and calories. Encoded as UTF-8 with BOM for native Excel support.
        Guarantees strict YYYY-MM-DD date and HH:mm:ss time formatting to prevent
        Excel '########' display overflows.
        """
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")

        # 1. Header Information Block
        meta_date = format_csv_date(snapshot.get("export_metadata", {}).get("export_date"))
        writer.writerow(["# NutriQ Nutrition Export Data"])
        writer.writerow(["# Export Date", meta_date])
        user_name = snapshot.get("profile", {}).get("name", "NutriQ User")
        writer.writerow(["# User", user_name])
        writer.writerow([])

        # 2. Main Meal History Table
        writer.writerow([
            "Date", "Time", "Meal Type", "Food Name",
            "Quantity", "Serving Unit", "Grams (g)",
            "Calories (kcal)", "Protein (g)", "Carbohydrates (g)", "Fat (g)", "Fiber (g)"
        ])

        meals = snapshot.get("meals", [])
        has_items = False
        for m in meals:
            dt_raw = m.get("occurred_at", "")
            date_part = format_csv_date(dt_raw)
            time_part = format_csv_time(dt_raw)
            meal_type = (m.get("meal_type") or "").replace("_", " ").title()

            for item in m.get("items", []):
                has_items = True
                writer.writerow([
                    date_part,
                    time_part,
                    meal_type,
                    item.get("food_name", ""),
                    item.get("quantity", 1),
                    item.get("serving_unit", ""),
                    item.get("grams", 0),
                    item.get("calories", 0),
                    item.get("protein_g", 0),
                    item.get("carbs_g", 0),
                    item.get("fat_g", 0),
                    item.get("fiber_g", 0)
                ])

        if not has_items:
            writer.writerow(["No meal records logged yet", "", "", "", "", "", "", "", "", "", "", ""])

        # 3. Daily Nutrition Summaries Section
        nutrition_summary = snapshot.get("nutrition_summary", [])
        if nutrition_summary:
            writer.writerow([])
            writer.writerow(["# Daily Nutrition Summaries"])
            writer.writerow([
                "Date", "Meal Count", "Total Calories (kcal)",
                "Protein (g)", "Carbohydrates (g)", "Fat (g)", "Fiber (g)", "Water (ml)"
            ])
            for s in nutrition_summary:
                writer.writerow([
                    format_csv_date(s.get("date", "")),
                    s.get("meal_count", 0),
                    s.get("total_calories", 0),
                    s.get("total_protein_g", 0),
                    s.get("total_carbs_g", 0),
                    s.get("total_fat_g", 0),
                    s.get("total_fiber_g", 0),
                    s.get("total_water_ml", 0)
                ])

        # 4. Water Logs Section
        water_logs = snapshot.get("water_logs", [])
        if water_logs:
            writer.writerow([])
            writer.writerow(["# Hydration Logs"])
            writer.writerow(["Date", "Time", "Water Consumed (ml)"])
            for w in water_logs:
                dt_raw = w.get("recorded_at", "")
                writer.writerow([format_csv_date(dt_raw), format_csv_time(dt_raw), w.get("amount_ml", 0)])

        # 5. Weight History Section
        weight_logs = snapshot.get("weight_history", [])
        if weight_logs:
            writer.writerow([])
            writer.writerow(["# Weight History"])
            writer.writerow(["Date", "Time", "Weight (kg)"])
            for wt in weight_logs:
                dt_raw = wt.get("recorded_at", "")
                writer.writerow([format_csv_date(dt_raw), format_csv_time(dt_raw), wt.get("weight_kg", 0)])

        return output.getvalue()

    # =========================================================================
    # PDF GENERATOR
    # =========================================================================
    @classmethod
    def generate_pdf(cls, snapshot: Dict[str, Any]) -> bytes:
        """
        Generates a professional, multi-page PDF report with NutriQ branding,
        profile demographics, targets, goal progress, meal history tables,
        daily summaries, and hydration & weight check-ins.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=40,
            rightMargin=40,
            topMargin=45,
            bottomMargin=55
        )

        styles = getSampleStyleSheet()
        
        # Color Palette
        primary_color = colors.HexColor("#059669")     # Emerald 600
        dark_header = colors.HexColor("#0f172a")       # Slate 900
        card_bg = colors.HexColor("#f8fafc")           # Slate 50
        border_color = colors.HexColor("#e2e8f0")      # Slate 200
        muted_text = colors.HexColor("#64748b")        # Slate 500
        text_color = colors.HexColor("#1e293b")        # Slate 800

        # Custom typography styles
        title_style = ParagraphStyle(
            'NutriQTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=primary_color,
            spaceAfter=2
        )

        subtitle_style = ParagraphStyle(
            'NutriQSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=13,
            textColor=muted_text,
            spaceAfter=12
        )

        section_heading = ParagraphStyle(
            'NutriQSectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=dark_header,
            spaceBefore=14,
            spaceAfter=6
        )

        table_header_style = ParagraphStyle(
            'NutriQTableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=10.5,
            textColor=colors.white
        )

        table_body_style = ParagraphStyle(
            'NutriQTableBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=text_color
        )

        table_bold_style = ParagraphStyle(
            'NutriQTableBodyBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=text_color
        )

        meta_label_style = ParagraphStyle(
            'NutriQMetaLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11,
            textColor=muted_text
        )

        meta_val_style = ParagraphStyle(
            'NutriQMetaVal',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            textColor=text_color
        )

        no_data_style = ParagraphStyle(
            'NutriQNoData',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=8.5,
            leading=11,
            textColor=muted_text,
            spaceAfter=6
        )

        elements = []

        # =========================================================================
        # 1. HEADER & REPORT METADATA
        # =========================================================================
        elements.append(Paragraph("NUTRIQ", title_style))
        elements.append(Paragraph("Personal Nutrition & Health Data Report", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=0, spaceAfter=14))

        meta = snapshot.get("export_metadata", {})
        prof = snapshot.get("profile", {})
        targets = snapshot.get("nutrition_targets", {})
        
        # Meta Card
        meta_table_data = [
            [
                Paragraph("<b>Export Date:</b>", meta_label_style),
                Paragraph(esc(meta.get("export_date", "-")), meta_val_style),
                Paragraph("<b>Application:</b>", meta_label_style),
                Paragraph("NutriQ Intelligence v2.0", meta_val_style)
            ],
            [
                Paragraph("<b>User Name:</b>", meta_label_style),
                Paragraph(esc(prof.get("name") or "NutriQ Member"), meta_val_style),
                Paragraph("<b>Format Version:</b>", meta_label_style),
                Paragraph(esc(meta.get("format_version", "1.0")), meta_val_style)
            ]
        ]
        meta_table = Table(meta_table_data, colWidths=[80, 180, 90, 182])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), card_bg),
            ('BOX', (0, 0), (-1, -1), 1, border_color),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

        # =========================================================================
        # 2. PROFILE & DEMOGRAPHICS
        # =========================================================================
        elements.append(Paragraph("Personal Profile & Physical Demographics", section_heading))
        if prof and prof.get("age"):
            prof_data = [
                [
                    Paragraph("<b>Age:</b>", meta_label_style), Paragraph(f"{esc(prof.get('age'))} years", meta_val_style),
                    Paragraph("<b>Biological Sex:</b>", meta_label_style), Paragraph(esc(str(prof.get('gender', '-')).capitalize()), meta_val_style)
                ],
                [
                    Paragraph("<b>Height:</b>", meta_label_style), Paragraph(f"{esc(prof.get('height_cm'))} cm", meta_val_style),
                    Paragraph("<b>Weight:</b>", meta_label_style), Paragraph(f"{esc(prof.get('weight_kg'))} kg", meta_val_style)
                ],
                [
                    Paragraph("<b>Activity Level:</b>", meta_label_style), Paragraph(esc(str(prof.get('activity_level', '-')).replace('_', ' ').title()), meta_val_style),
                    Paragraph("<b>Fitness Goal:</b>", meta_label_style), Paragraph(esc(str(prof.get('fitness_goal', '-')).replace('_', ' ').title()), meta_val_style)
                ],
                [
                    Paragraph("<b>Dietary Style:</b>", meta_label_style), Paragraph(esc(str(prof.get('dietary_preference', '-')).capitalize()), meta_val_style),
                    Paragraph("<b>Food Notes:</b>", meta_label_style), Paragraph(esc(str(prof.get('food_preferences') or 'None specified')), meta_val_style)
                ]
            ]
            prof_table = Table(prof_data, colWidths=[85, 175, 95, 177])
            prof_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), card_bg),
                ('GRID', (0, 0), (-1, -1), 0.5, border_color),
                ('PADDING', (0, 0), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(prof_table)
        else:
            elements.append(Paragraph("No profile demographics recorded.", no_data_style))

        elements.append(Spacer(1, 14))

        # =========================================================================
        # 3. NUTRITION TARGETS & METABOLIC BUDGET
        # =========================================================================
        elements.append(Paragraph("Calibrated Daily Nutrition Targets (Mifflin-St Jeor)", section_heading))
        if targets and targets.get("daily_calories_target"):
            t_data = [
                [
                    Paragraph("Metric", table_header_style),
                    Paragraph("Daily Target", table_header_style),
                    Paragraph("Clinical Context", table_header_style)
                ],
                [
                    Paragraph("<b>Calorie Budget</b>", table_body_style),
                    Paragraph(f"<b>{targets.get('daily_calories_target'):,} kcal</b>", table_bold_style),
                    Paragraph("Calculated for energy equilibrium / prescribed goal delta", table_body_style)
                ],
                [
                    Paragraph("<b>Protein</b>", table_body_style),
                    Paragraph(f"{esc(targets.get('protein_target_g'))} g", table_body_style),
                    Paragraph("Essential amino acid & lean muscle preservation budget", table_body_style)
                ],
                [
                    Paragraph("<b>Carbohydrates</b>", table_body_style),
                    Paragraph(f"{esc(targets.get('carbohydrates_target_g'))} g", table_body_style),
                    Paragraph("Complex glycogen replenishing energy source", table_body_style)
                ],
                [
                    Paragraph("<b>Fat</b>", table_body_style),
                    Paragraph(f"{esc(targets.get('fat_target_g'))} g", table_body_style),
                    Paragraph("Lipid and cellular hormone synthesis budget", table_body_style)
                ],
                [
                    Paragraph("<b>Daily Hydration</b>", table_body_style),
                    Paragraph(f"{targets.get('water_target_ml'):,} ml", table_body_style),
                    Paragraph("Metabolic fluid & hydration target (35ml/kg baseline)", table_body_style)
                ],
                [
                    Paragraph("<b>BMR / TDEE</b>", table_body_style),
                    Paragraph(f"{esc(targets.get('bmr_kcal'))} / {esc(targets.get('tdee_kcal'))} kcal", table_body_style),
                    Paragraph("Basal Metabolic Rate & Total Daily Energy Expenditure", table_body_style)
                ]
            ]
            t_table = Table(t_data, colWidths=[110, 110, 312])
            t_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), primary_color),
                ('GRID', (0, 0), (-1, -1), 0.5, border_color),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, card_bg]),
                ('PADDING', (0, 0), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(t_table)
        else:
            elements.append(Paragraph("No calibrated nutrition targets available.", no_data_style))

        elements.append(Spacer(1, 14))

        # =========================================================================
        # 4. GOAL PROGRESS
        # =========================================================================
        elements.append(Paragraph("Goal Progress & Fitness Objectives", section_heading))
        goals = snapshot.get("goals", [])
        if goals:
            g_data = [
                [
                    Paragraph("Goal Type", table_header_style),
                    Paragraph("Current Weight", table_header_style),
                    Paragraph("Target Weight", table_header_style),
                    Paragraph("Weekly Rate", table_header_style),
                    Paragraph("Status", table_header_style),
                    Paragraph("Created Date", table_header_style)
                ]
            ]
            for g in goals:
                g_type = esc(str(g.get("goal_type", "-")).replace("_", " ").title())
                c_wt = f"{esc(g.get('current_weight_kg', '-'))} kg"
                t_wt = f"{esc(g.get('target_weight_kg', '-'))} kg"
                rate = f"{esc(g.get('desired_rate', '-'))} kg/wk"
                status_str = "Active" if g.get("active") else "Completed / Inactive"
                c_date = esc(format_pdf_date(g.get("created_at", "-")))
                g_data.append([
                    Paragraph(g_type, table_bold_style),
                    Paragraph(c_wt, table_body_style),
                    Paragraph(t_wt, table_body_style),
                    Paragraph(rate, table_body_style),
                    Paragraph(status_str, table_body_style),
                    Paragraph(c_date, table_body_style)
                ])
            g_table = Table(g_data, colWidths=[95, 80, 80, 85, 92, 100], repeatRows=1)
            g_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), dark_header),
                ('GRID', (0, 0), (-1, -1), 0.5, border_color),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, card_bg]),
                ('PADDING', (0, 0), (-1, -1), 4.5),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(g_table)
        else:
            elements.append(Paragraph("No goal progress data available.", no_data_style))

        elements.append(Spacer(1, 14))

        # =========================================================================
        # 5. MEAL HISTORY & ITEMIZED JOURNAL
        # =========================================================================
        elements.append(Paragraph("Meal History & Itemized Food Journal", section_heading))
        meals = snapshot.get("meals", [])
        
        if meals:
            m_table_rows = [
                [
                    Paragraph("Date", table_header_style),
                    Paragraph("Meal", table_header_style),
                    Paragraph("Food Item", table_header_style),
                    Paragraph("Portion / Unit", table_header_style),
                    Paragraph("Calories", table_header_style),
                    Paragraph("Macros (P / C / F)", table_header_style)
                ]
            ]

            for m in meals:
                dt_raw = m.get("occurred_at", "")
                dt_str = esc(format_pdf_date(dt_raw))
                m_type = esc((m.get("meal_type") or "").replace("_", " ").title())

                items = m.get("items", [])
                if items:
                    for idx, it in enumerate(items):
                        time_cell = Paragraph(dt_str, table_body_style)
                        type_cell = Paragraph(f"<b>{m_type}</b>", table_body_style)
                        food_name_clean = esc(it.get("food_name", ""))
                        food_cell = Paragraph(food_name_clean, table_bold_style)
                        serving_unit_clean = esc(it.get("serving_unit", ""))
                        portion_cell = Paragraph(f"{esc(it.get('quantity'))}x {serving_unit_clean} ({esc(it.get('grams'))}g)", table_body_style)
                        cal_cell = Paragraph(f"<b>{esc(it.get('calories'))} kcal</b>", table_body_style)
                        macro_cell = Paragraph(f"{esc(it.get('protein_g'))}g P • {esc(it.get('carbs_g'))}g C • {esc(it.get('fat_g'))}g F", table_body_style)

                        m_table_rows.append([time_cell, type_cell, food_cell, portion_cell, cal_cell, macro_cell])
                else:
                    m_table_rows.append([
                        Paragraph(dt_str, table_body_style),
                        Paragraph(m_type, table_body_style),
                        Paragraph("Meal logged without itemized items", table_body_style),
                        Paragraph("-", table_body_style),
                        Paragraph(f"{esc(m.get('total_calories'))} kcal", table_body_style),
                        Paragraph(f"{esc(m.get('total_protein_g'))}g P • {esc(m.get('total_carbs_g'))}g C • {esc(m.get('total_fat_g'))}g F", table_body_style)
                    ])

            # col widths: 532 pt total
            m_table = Table(m_table_rows, colWidths=[90, 65, 145, 102, 60, 70], repeatRows=1)
            m_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), dark_header),
                ('GRID', (0, 0), (-1, -1), 0.5, border_color),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, card_bg]),
                ('PADDING', (0, 0), (-1, -1), 4.5),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(m_table)
        else:
            elements.append(Paragraph("No meal history available.", no_data_style))

        elements.append(Spacer(1, 14))

        # =========================================================================
        # 6. DAILY NUTRITION SUMMARIES
        # =========================================================================
        elements.append(Paragraph("Daily Nutrition Summaries", section_heading))
        nutrition_summary = snapshot.get("nutrition_summary", [])
        if nutrition_summary:
            s_data = [
                [
                    Paragraph("Date", table_header_style),
                    Paragraph("Meals", table_header_style),
                    Paragraph("Total Calories", table_header_style),
                    Paragraph("Protein", table_header_style),
                    Paragraph("Carbs", table_header_style),
                    Paragraph("Fat", table_header_style),
                    Paragraph("Fiber", table_header_style),
                    Paragraph("Hydration", table_header_style)
                ]
            ]
            for s in nutrition_summary:
                s_data.append([
                    Paragraph(esc(format_pdf_date(s.get("date", "-"))), table_bold_style),
                    Paragraph(str(s.get("meal_count", 0)), table_body_style),
                    Paragraph(f"<b>{s.get('total_calories', 0):,} kcal</b>", table_bold_style),
                    Paragraph(f"{s.get('total_protein_g', 0)} g", table_body_style),
                    Paragraph(f"{s.get('total_carbs_g', 0)} g", table_body_style),
                    Paragraph(f"{s.get('total_fat_g', 0)} g", table_body_style),
                    Paragraph(f"{s.get('total_fiber_g', 0)} g", table_body_style),
                    Paragraph(f"{s.get('total_water_ml', 0):,} ml", table_body_style)
                ])
            s_table = Table(s_data, colWidths=[75, 45, 82, 65, 65, 60, 60, 80], repeatRows=1)
            s_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), primary_color),
                ('GRID', (0, 0), (-1, -1), 0.5, border_color),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, card_bg]),
                ('PADDING', (0, 0), (-1, -1), 4.5),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(s_table)
        else:
            elements.append(Paragraph("No daily nutrition summaries available.", no_data_style))

        elements.append(Spacer(1, 14))

        # =========================================================================
        # 7. RECENT HYDRATION & WEIGHT CHECK-INS
        # =========================================================================
        water_logs = snapshot.get("water_logs", [])
        weight_logs = snapshot.get("weight_history", [])

        if water_logs or weight_logs:
            elements.append(Paragraph("Recent Hydration & Weight Check-ins", section_heading))
            
            # Sub-table 1: Water
            w_rows = [[Paragraph("Water Log Date", table_header_style), Paragraph("Amount Consumed", table_header_style)]]
            if water_logs:
                for w in water_logs[:10]:
                    w_rows.append([Paragraph(esc(format_pdf_datetime(w.get("recorded_at", ""))), table_body_style), Paragraph(f"<b>{esc(w.get('amount_ml'))} ml</b>", table_body_style)])
            else:
                w_rows.append([Paragraph("No hydration logs recorded", table_body_style), Paragraph("-", table_body_style)])
            
            w_table = Table(w_rows, colWidths=[150, 100])
            w_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), primary_color),
                ('GRID', (0, 0), (-1, -1), 0.5, border_color),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, card_bg]),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))

            # Sub-table 2: Weight
            wt_rows = [[Paragraph("Weight Check-in Date", table_header_style), Paragraph("Recorded Weight", table_header_style)]]
            if weight_logs:
                for wt in weight_logs[:10]:
                    wt_rows.append([Paragraph(esc(format_pdf_datetime(wt.get("recorded_at", ""))), table_body_style), Paragraph(f"<b>{esc(wt.get('weight_kg'))} kg</b>", table_body_style)])
            else:
                wt_rows.append([Paragraph("No weight history recorded", table_body_style), Paragraph("-", table_body_style)])

            wt_table = Table(wt_rows, colWidths=[150, 100])
            wt_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), dark_header),
                ('GRID', (0, 0), (-1, -1), 0.5, border_color),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, card_bg]),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))

            combined_table = Table([[w_table, wt_table]], colWidths=[260, 260])
            combined_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('PADDING', (0, 0), (-1, -1), 0),
            ]))
            elements.append(combined_table)

        # Build PDF
        doc.build(elements, canvasmaker=NumberedCanvas)
        return buffer.getvalue()
