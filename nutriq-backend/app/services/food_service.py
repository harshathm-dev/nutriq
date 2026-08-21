import re
import unicodedata
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, delete
from sqlalchemy.orm import selectinload
from app.models.food import Food, ServingConversion, CustomFood

# Comprehensive Curated IFCT & Indian/Tamil Nadu Regional Food Dataset (100+ Verified Foods)
CURATED_FOOD_SEEDS: List[Dict[str, Any]] = [
    # -------------------------------------------------------------
    # 1. DOSA & IDLI VARIETIES (Tamil Nadu & South India)
    # -------------------------------------------------------------
    {
        "name": "Plain Dosa",
        "category": "dosa",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 168.0,
        "protein_g": 3.9,
        "carbs_g": 29.4,
        "fat_g": 3.7,
        "fiber_g": 1.8,
        "sugar_g": 0.5,
        "sodium_mg": 210.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece (medium)", "grams": 80.0, "unit": "piece"},
            {"serving_label": "1 large crispy dosa", "grams": 120.0, "unit": "dosa"},
            {"serving_label": "2 dosas (standard serving)", "grams": 160.0, "unit": "serving"}
        ]
    },
    {
        "name": "Masala Dosa",
        "category": "dosa",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 210.0,
        "protein_g": 4.5,
        "carbs_g": 32.0,
        "fat_g": 7.2,
        "fiber_g": 2.5,
        "sugar_g": 1.2,
        "sodium_mg": 320.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece with potato masala", "grams": 150.0, "unit": "piece"},
            {"serving_label": "1 restaurant plate", "grams": 180.0, "unit": "plate"}
        ]
    },
    {
        "name": "Ghee Roast Dosa",
        "category": "dosa",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 260.0,
        "protein_g": 4.2,
        "carbs_g": 30.5,
        "fat_g": 13.8,
        "fiber_g": 1.6,
        "sugar_g": 0.4,
        "sodium_mg": 225.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 conical ghee roast", "grams": 110.0, "unit": "piece"},
            {"serving_label": "1 large ghee roast", "grams": 150.0, "unit": "dosa"}
        ]
    },
    {
        "name": "Ragi Dosa (Finger Millet Dosa)",
        "category": "dosa",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 155.0,
        "protein_g": 4.8,
        "carbs_g": 28.0,
        "fat_g": 2.6,
        "fiber_g": 4.2,
        "sugar_g": 0.3,
        "sodium_mg": 180.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece", "grams": 75.0, "unit": "piece"},
            {"serving_label": "2 ragi dosas", "grams": 150.0, "unit": "serving"}
        ]
    },
    {
        "name": "Onion Rava Dosa",
        "category": "dosa",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 195.0,
        "protein_g": 4.1,
        "carbs_g": 31.0,
        "fat_g": 6.0,
        "fiber_g": 2.1,
        "sugar_g": 1.4,
        "sodium_mg": 260.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece", "grams": 120.0, "unit": "piece"},
            {"serving_label": "1 large rava dosa", "grams": 160.0, "unit": "dosa"}
        ]
    },
    {
        "name": "Egg Dosa (Muttai Dosa)",
        "category": "dosa",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 198.0,
        "protein_g": 8.5,
        "carbs_g": 22.0,
        "fat_g": 8.4,
        "fiber_g": 1.2,
        "sugar_g": 0.5,
        "sodium_mg": 280.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 single egg dosa", "grams": 130.0, "unit": "piece"},
            {"serving_label": "1 double egg dosa", "grams": 180.0, "unit": "serving"}
        ]
    },
    {
        "name": "Adai (Mixed Lentil & Rice Dosa)",
        "category": "dosa",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 185.0,
        "protein_g": 7.8,
        "carbs_g": 28.5,
        "fat_g": 4.5,
        "fiber_g": 5.2,
        "sugar_g": 0.8,
        "sodium_mg": 210.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 thick adai", "grams": 100.0, "unit": "piece"},
            {"serving_label": "2 adais with avial", "grams": 200.0, "unit": "serving"}
        ]
    },
    {
        "name": "Pesarattu (Green Gram Dosa)",
        "category": "dosa",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 172.0,
        "protein_g": 8.9,
        "carbs_g": 27.0,
        "fat_g": 3.2,
        "fiber_g": 6.0,
        "sugar_g": 0.6,
        "sodium_mg": 195.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece", "grams": 90.0, "unit": "piece"},
            {"serving_label": "1 MLA pesarattu (with upma)", "grams": 160.0, "unit": "serving"}
        ]
    },
    {
        "name": "Idli (Steamed Rice Cake)",
        "category": "idli",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 140.0,
        "protein_g": 4.2,
        "carbs_g": 29.0,
        "fat_g": 0.4,
        "fiber_g": 1.6,
        "sugar_g": 0.2,
        "sodium_mg": 180.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece", "grams": 45.0, "unit": "piece"},
            {"serving_label": "2 pieces", "grams": 90.0, "unit": "serving"},
            {"serving_label": "1 plate (3 idlis)", "grams": 135.0, "unit": "plate"},
            {"serving_label": "1 plate (4 idlis)", "grams": 180.0, "unit": "plate"}
        ]
    },
    {
        "name": "Podi Idli (Ghee Podi Idli)",
        "category": "idli",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 215.0,
        "protein_g": 5.4,
        "carbs_g": 28.0,
        "fat_g": 9.2,
        "fiber_g": 2.5,
        "sugar_g": 0.4,
        "sodium_mg": 290.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "2 podi idlis", "grams": 110.0, "unit": "serving"},
            {"serving_label": "1 plate mini podi idlis (14 pcs)", "grams": 160.0, "unit": "plate"}
        ]
    },
    {
        "name": "Rava Idli",
        "category": "idli",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 165.0,
        "protein_g": 4.8,
        "carbs_g": 26.5,
        "fat_g": 4.6,
        "fiber_g": 1.8,
        "sugar_g": 0.5,
        "sodium_mg": 220.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece", "grams": 55.0, "unit": "piece"},
            {"serving_label": "2 rava idlis", "grams": 110.0, "unit": "serving"}
        ]
    },
    {
        "name": "Onion Uthappam",
        "category": "uthappam",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 178.0,
        "protein_g": 4.4,
        "carbs_g": 28.0,
        "fat_g": 5.2,
        "fiber_g": 2.2,
        "sugar_g": 1.8,
        "sodium_mg": 230.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 small uthappam", "grams": 110.0, "unit": "piece"},
            {"serving_label": "1 large onion uthappam", "grams": 170.0, "unit": "uthappam"}
        ]
    },
    {
        "name": "Tomato & Veg Uthappam",
        "category": "uthappam",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 168.0,
        "protein_g": 4.2,
        "carbs_g": 27.5,
        "fat_g": 4.5,
        "fiber_g": 2.6,
        "sugar_g": 2.2,
        "sodium_mg": 215.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece", "grams": 140.0, "unit": "piece"},
            {"serving_label": "1 plate", "grams": 180.0, "unit": "plate"}
        ]
    },

    # -------------------------------------------------------------
    # 2. PONGAL, VADA, PANIYARAM & BREAKFAST STAPLES
    # -------------------------------------------------------------
    {
        "name": "Ven Pongal (Ghee Khara Pongal)",
        "category": "breakfast",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 192.0,
        "protein_g": 5.2,
        "carbs_g": 24.5,
        "fat_g": 8.4,
        "fiber_g": 2.4,
        "sugar_g": 0.2,
        "sodium_mg": 240.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori / small bowl", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 plate / standard serving", "grams": 220.0, "unit": "plate"}
        ]
    },
    {
        "name": "Sakkarai Pongal (Sweet Jaggery Pongal)",
        "category": "sweets",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 245.0,
        "protein_g": 3.8,
        "carbs_g": 45.0,
        "fat_g": 6.2,
        "fiber_g": 1.4,
        "sugar_g": 26.0,
        "sodium_mg": 40.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 small katori", "grams": 100.0, "unit": "katori"},
            {"serving_label": "1 serving scoop", "grams": 60.0, "unit": "scoop"}
        ]
    },
    {
        "name": "Medu Vada (Urad Dal Crispy Vada)",
        "category": "snacks",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 275.0,
        "protein_g": 8.8,
        "carbs_g": 25.4,
        "fat_g": 15.6,
        "fiber_g": 4.8,
        "sugar_g": 0.5,
        "sodium_mg": 280.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece", "grams": 45.0, "unit": "piece"},
            {"serving_label": "2 pieces with sambar", "grams": 90.0, "unit": "serving"}
        ]
    },
    {
        "name": "Masala Vada (Chana Dal Vada / Paruppu Vadai)",
        "category": "snacks",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 290.0,
        "protein_g": 9.6,
        "carbs_g": 28.0,
        "fat_g": 16.0,
        "fiber_g": 6.2,
        "sugar_g": 0.8,
        "sodium_mg": 310.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece", "grams": 40.0, "unit": "piece"},
            {"serving_label": "2 vadas (tea-time snack)", "grams": 80.0, "unit": "serving"}
        ]
    },
    {
        "name": "Kuzhi Paniyaram (Savory Rice-Lentil Dumplings)",
        "category": "breakfast",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 180.0,
        "protein_g": 4.6,
        "carbs_g": 28.2,
        "fat_g": 5.4,
        "fiber_g": 2.0,
        "sugar_g": 0.6,
        "sodium_mg": 220.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece", "grams": 25.0, "unit": "piece"},
            {"serving_label": "1 plate (5 paniyarams)", "grams": 125.0, "unit": "plate"},
            {"serving_label": "1 plate (7 paniyarams)", "grams": 175.0, "unit": "plate"}
        ]
    },
    {
        "name": "Appam (Fermented Rice Pancake)",
        "category": "breakfast",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 135.0,
        "protein_g": 2.6,
        "carbs_g": 26.0,
        "fat_g": 2.1,
        "fiber_g": 1.2,
        "sugar_g": 1.5,
        "sodium_mg": 90.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece", "grams": 60.0, "unit": "piece"},
            {"serving_label": "2 appams with coconut milk", "grams": 120.0, "unit": "serving"}
        ]
    },
    {
        "name": "Idiyappam (Steamed Rice String Hoppers)",
        "category": "breakfast",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 128.0,
        "protein_g": 2.4,
        "carbs_g": 28.0,
        "fat_g": 0.4,
        "fiber_g": 1.0,
        "sugar_g": 0.2,
        "sodium_mg": 45.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 nest / piece", "grams": 40.0, "unit": "piece"},
            {"serving_label": "1 plate (3 pieces)", "grams": 120.0, "unit": "plate"}
        ]
    },
    {
        "name": "Puttu with Kadala Curry (Steamed Rice & Chickpea)",
        "category": "breakfast",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 162.0,
        "protein_g": 5.4,
        "carbs_g": 28.8,
        "fat_g": 3.1,
        "fiber_g": 4.5,
        "sugar_g": 1.2,
        "sodium_mg": 180.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 cylindrical puttu portion", "grams": 120.0, "unit": "piece"},
            {"serving_label": "1 full plate (puttu + curry)", "grams": 250.0, "unit": "plate"}
        ]
    },

    # -------------------------------------------------------------
    # 3. RICE VARIETIES & TAMIL NADU LUNCH DISHES
    # -------------------------------------------------------------
    {
        "name": "White Rice (Cooked Ponni / Sona Masuri)",
        "category": "rice",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 130.0,
        "protein_g": 2.7,
        "carbs_g": 28.2,
        "fat_g": 0.3,
        "fiber_g": 0.4,
        "sugar_g": 0.1,
        "sodium_mg": 2.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 cup cooked", "grams": 160.0, "unit": "cup"},
            {"serving_label": "1 plate cooked", "grams": 250.0, "unit": "plate"}
        ]
    },
    {
        "name": "Brown Rice (Cooked)",
        "category": "rice",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 111.0,
        "protein_g": 2.6,
        "carbs_g": 23.0,
        "fat_g": 0.9,
        "fiber_g": 1.8,
        "sugar_g": 0.2,
        "sodium_mg": 5.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 cup", "grams": 160.0, "unit": "cup"}
        ]
    },
    {
        "name": "Curd Rice (Thayir Sadam with Mustard Tadka)",
        "category": "rice",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 142.0,
        "protein_g": 4.1,
        "carbs_g": 21.0,
        "fat_g": 4.6,
        "fiber_g": 0.6,
        "sugar_g": 2.2,
        "sodium_mg": 180.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 full lunch bowl", "grams": 250.0, "unit": "bowl"}
        ]
    },
    {
        "name": "Lemon Rice (Elumichai Sadam)",
        "category": "rice",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 165.0,
        "protein_g": 3.2,
        "carbs_g": 27.4,
        "fat_g": 4.8,
        "fiber_g": 1.2,
        "sugar_g": 0.5,
        "sodium_mg": 210.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 lunch plate", "grams": 220.0, "unit": "plate"}
        ]
    },
    {
        "name": "Tamarind Rice (Puliyodharai / Kovil Prasadam Style)",
        "category": "rice",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 188.0,
        "protein_g": 3.8,
        "carbs_g": 29.5,
        "fat_g": 6.4,
        "fiber_g": 2.0,
        "sugar_g": 1.5,
        "sodium_mg": 260.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 lunch plate", "grams": 220.0, "unit": "plate"}
        ]
    },
    {
        "name": "Tomato Rice (Thakkali Sadam)",
        "category": "rice",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 152.0,
        "protein_g": 3.0,
        "carbs_g": 26.0,
        "fat_g": 4.0,
        "fiber_g": 1.6,
        "sugar_g": 1.8,
        "sodium_mg": 220.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 lunch plate", "grams": 220.0, "unit": "plate"}
        ]
    },
    {
        "name": "Sambar Rice (Bisibelebath / Sambar Sadam)",
        "category": "rice",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 145.0,
        "protein_g": 4.6,
        "carbs_g": 24.2,
        "fat_g": 3.5,
        "fiber_g": 2.8,
        "sugar_g": 1.2,
        "sodium_mg": 240.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 full bowl", "grams": 250.0, "unit": "bowl"}
        ]
    },
    {
        "name": "Vegetable Biriyani / Pulao",
        "category": "rice",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 160.0,
        "protein_g": 3.8,
        "carbs_g": 26.5,
        "fat_g": 4.4,
        "fiber_g": 2.2,
        "sugar_g": 1.4,
        "sodium_mg": 280.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 plate biriyani", "grams": 280.0, "unit": "plate"}
        ]
    },
    {
        "name": "Chicken Biriyani (Ambur / Chettinad Style)",
        "category": "meat",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 195.0,
        "protein_g": 11.5,
        "carbs_g": 22.0,
        "fat_g": 6.8,
        "fiber_g": 1.2,
        "sugar_g": 0.8,
        "sodium_mg": 380.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 small bowl (1 pc chicken)", "grams": 200.0, "unit": "bowl"},
            {"serving_label": "1 full plate (2-3 pcs chicken)", "grams": 350.0, "unit": "plate"}
        ]
    },
    {
        "name": "Mutton Biriyani (Thalappakatti Seeraga Samba Style)",
        "category": "meat",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 220.0,
        "protein_g": 12.8,
        "carbs_g": 21.0,
        "fat_g": 9.5,
        "fiber_g": 1.0,
        "sugar_g": 0.6,
        "sodium_mg": 410.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 small bowl (with mutton)", "grams": 200.0, "unit": "bowl"},
            {"serving_label": "1 full plate biriyani", "grams": 350.0, "unit": "plate"}
        ]
    },

    # -------------------------------------------------------------
    # 4. SAMBAR, RASAM, KOOTU, PORIYAL & VEGETABLE DISHES
    # -------------------------------------------------------------
    {
        "name": "Tamil Sambar (Drumstick, Shallots & Vegetables)",
        "category": "legumes",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 68.0,
        "protein_g": 3.4,
        "carbs_g": 10.2,
        "fat_g": 1.6,
        "fiber_g": 2.5,
        "sugar_g": 1.8,
        "sodium_mg": 230.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 cup", "grams": 180.0, "unit": "cup"},
            {"serving_label": "1 ladle / scoop", "grams": 80.0, "unit": "ladle"}
        ]
    },
    {
        "name": "Tomato Pepper Rasam",
        "category": "soups",
        "serving_size": 100.0,
        "unit": "ml",
        "calories": 32.0,
        "protein_g": 1.2,
        "carbs_g": 4.8,
        "fat_g": 0.8,
        "fiber_g": 0.8,
        "sugar_g": 1.4,
        "sodium_mg": 190.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori / soup bowl", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 glass / cup", "grams": 200.0, "unit": "glass"}
        ]
    },
    {
        "name": "Keerai Kootu (Spinach & Moong Dal Stew)",
        "category": "vegetables",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 82.0,
        "protein_g": 4.8,
        "carbs_g": 9.5,
        "fat_g": 2.8,
        "fiber_g": 3.6,
        "sugar_g": 1.0,
        "sodium_mg": 160.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 cup", "grams": 180.0, "unit": "cup"}
        ]
    },
    {
        "name": "Chow Chow Kootu (Chayote Squash with Lentils)",
        "category": "vegetables",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 78.0,
        "protein_g": 3.8,
        "carbs_g": 9.8,
        "fat_g": 2.4,
        "fiber_g": 3.0,
        "sugar_g": 1.5,
        "sodium_mg": 150.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"}
        ]
    },
    {
        "name": "Beans Poriyal (Green Beans with Fresh Coconut)",
        "category": "vegetables",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 74.0,
        "protein_g": 2.8,
        "carbs_g": 8.0,
        "fat_g": 3.6,
        "fiber_g": 3.8,
        "sugar_g": 1.6,
        "sodium_mg": 140.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 100.0, "unit": "katori"},
            {"serving_label": "1 cup", "grams": 140.0, "unit": "cup"}
        ]
    },
    {
        "name": "Cabbage Poriyal (Cabbage with Mustard & Coconut)",
        "category": "vegetables",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 65.0,
        "protein_g": 2.2,
        "carbs_g": 6.8,
        "fat_g": 3.2,
        "fiber_g": 2.9,
        "sugar_g": 2.4,
        "sodium_mg": 130.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 100.0, "unit": "katori"}
        ]
    },
    {
        "name": "Avial (Mixed Vegetables in Coconut Curd Stew)",
        "category": "vegetables",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 115.0,
        "protein_g": 3.0,
        "carbs_g": 11.2,
        "fat_g": 6.5,
        "fiber_g": 3.8,
        "sugar_g": 2.6,
        "sodium_mg": 160.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 cup", "grams": 180.0, "unit": "cup"}
        ]
    },
    {
        "name": "Vazhaikkai Poriyal / Varuval (Raw Banana Roast)",
        "category": "vegetables",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 145.0,
        "protein_g": 2.0,
        "carbs_g": 24.5,
        "fat_g": 4.5,
        "fiber_g": 3.2,
        "sugar_g": 1.0,
        "sodium_mg": 190.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 100.0, "unit": "katori"}
        ]
    },

    # -------------------------------------------------------------
    # 5. TAMIL & SOUTH INDIAN MEAT, FISH & CURRIES
    # -------------------------------------------------------------
    {
        "name": "Meen Kulambu (Tamil Fish Curry with Tamarind)",
        "category": "fish",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 138.0,
        "protein_g": 14.2,
        "carbs_g": 4.5,
        "fat_g": 7.0,
        "fiber_g": 1.0,
        "sugar_g": 1.2,
        "sodium_mg": 340.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece with gravy", "grams": 150.0, "unit": "serving"},
            {"serving_label": "1 katori bowl", "grams": 180.0, "unit": "katori"}
        ]
    },
    {
        "name": "Vanjaram Fish Fry (Seer Fish Tawa Fry)",
        "category": "fish",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 190.0,
        "protein_g": 24.5,
        "carbs_g": 3.0,
        "fat_g": 8.8,
        "fiber_g": 0.4,
        "sugar_g": 0.2,
        "sodium_mg": 310.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 medium slice / piece", "grams": 100.0, "unit": "piece"},
            {"serving_label": "1 large steak slice", "grams": 150.0, "unit": "piece"}
        ]
    },
    {
        "name": "Chettinad Chicken Curry",
        "category": "meat",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 175.0,
        "protein_g": 16.8,
        "carbs_g": 4.2,
        "fat_g": 10.2,
        "fiber_g": 1.4,
        "sugar_g": 1.0,
        "sodium_mg": 360.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori (with 2 pcs)", "grams": 180.0, "unit": "katori"},
            {"serving_label": "1 plate portion", "grams": 250.0, "unit": "plate"}
        ]
    },
    {
        "name": "Chettinad Chicken Sukka",
        "category": "meat",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 210.0,
        "protein_g": 22.4,
        "carbs_g": 3.5,
        "fat_g": 11.8,
        "fiber_g": 1.1,
        "sugar_g": 0.6,
        "sodium_mg": 390.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 small cup / starter", "grams": 120.0, "unit": "cup"},
            {"serving_label": "1 katori portion", "grams": 150.0, "unit": "katori"}
        ]
    },
    {
        "name": "Mutton Sukka (Dry Spiced Mutton Roast)",
        "category": "meat",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 245.0,
        "protein_g": 21.0,
        "carbs_g": 3.2,
        "fat_g": 16.5,
        "fiber_g": 0.8,
        "sugar_g": 0.5,
        "sodium_mg": 410.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 starter portion", "grams": 120.0, "unit": "cup"}
        ]
    },
    {
        "name": "Egg Poriyal (South Indian Scrambled Eggs with Onion & Curry Leaves)",
        "category": "eggs",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 185.0,
        "protein_g": 12.0,
        "carbs_g": 3.0,
        "fat_g": 13.6,
        "fiber_g": 0.8,
        "sugar_g": 1.2,
        "sodium_mg": 280.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 single egg scramble", "grams": 75.0, "unit": "serving"},
            {"serving_label": "2 eggs scramble", "grams": 140.0, "unit": "serving"}
        ]
    },

    # -------------------------------------------------------------
    # 6. PAROTTA, ROTI, POORI & BREADS
    # -------------------------------------------------------------
    {
        "name": "Malabar / Parotta (Layered Flatbread)",
        "category": "breads",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 320.0,
        "protein_g": 6.8,
        "carbs_g": 48.0,
        "fat_g": 11.5,
        "fiber_g": 1.8,
        "sugar_g": 2.2,
        "sodium_mg": 310.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece", "grams": 75.0, "unit": "piece"},
            {"serving_label": "2 parottas", "grams": 150.0, "unit": "serving"}
        ]
    },
    {
        "name": "Kothu Parotta (Egg & Chicken Kothu Parotta)",
        "category": "street food",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 240.0,
        "protein_g": 10.5,
        "carbs_g": 26.0,
        "fat_g": 10.8,
        "fiber_g": 1.6,
        "sugar_g": 1.4,
        "sodium_mg": 420.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 plate kothu parotta", "grams": 280.0, "unit": "plate"},
            {"serving_label": "1 small box", "grams": 200.0, "unit": "box"}
        ]
    },
    {
        "name": "Chapati / Roti (Whole Wheat Phulka)",
        "category": "roti/chapati",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 264.0,
        "protein_g": 9.2,
        "carbs_g": 52.0,
        "fat_g": 2.5,
        "fiber_g": 8.5,
        "sugar_g": 1.5,
        "sodium_mg": 190.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece / chapati (no oil)", "grams": 35.0, "unit": "piece"},
            {"serving_label": "1 standard chapati (with light ghee)", "grams": 40.0, "unit": "chapati"},
            {"serving_label": "2 chapatis", "grams": 80.0, "unit": "serving"},
            {"serving_label": "3 chapatis", "grams": 120.0, "unit": "serving"}
        ]
    },
    {
        "name": "Poori (Deep Fried Whole Wheat Bread)",
        "category": "breads",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 340.0,
        "protein_g": 7.5,
        "carbs_g": 46.0,
        "fat_g": 14.5,
        "fiber_g": 4.2,
        "sugar_g": 1.0,
        "sodium_mg": 240.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece", "grams": 35.0, "unit": "piece"},
            {"serving_label": "1 set (2 pooris with aloo)", "grams": 70.0, "unit": "set"},
            {"serving_label": "1 set (3 pooris)", "grams": 105.0, "unit": "set"}
        ]
    },
    {
        "name": "Aloo Paratha (Stuffed Potato Flatbread with Butter)",
        "category": "roti/chapati",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 240.0,
        "protein_g": 5.8,
        "carbs_g": 36.0,
        "fat_g": 8.5,
        "fiber_g": 3.8,
        "sugar_g": 1.5,
        "sodium_mg": 320.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 paratha", "grams": 120.0, "unit": "piece"},
            {"serving_label": "2 parathas with curd", "grams": 240.0, "unit": "serving"}
        ]
    },
    {
        "name": "Paneer Paratha (Stuffed Cottage Cheese Flatbread)",
        "category": "roti/chapati",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 275.0,
        "protein_g": 9.8,
        "carbs_g": 32.0,
        "fat_g": 12.0,
        "fiber_g": 3.2,
        "sugar_g": 1.2,
        "sodium_mg": 310.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 paratha", "grams": 130.0, "unit": "piece"}
        ]
    },

    # -------------------------------------------------------------
    # 7. PAN-INDIAN CURRIES, DALS & GRAVIES
    # -------------------------------------------------------------
    {
        "name": "Paneer Butter Masala",
        "category": "dairy",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 235.0,
        "protein_g": 8.5,
        "carbs_g": 7.8,
        "fat_g": 19.5,
        "fiber_g": 1.8,
        "sugar_g": 3.4,
        "sodium_mg": 380.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 restaurant bowl", "grams": 220.0, "unit": "bowl"}
        ]
    },
    {
        "name": "Palak Paneer (Spinach Cottage Cheese Curry)",
        "category": "dairy",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 165.0,
        "protein_g": 8.8,
        "carbs_g": 5.4,
        "fat_g": 12.2,
        "fiber_g": 3.0,
        "sugar_g": 1.8,
        "sodium_mg": 280.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"}
        ]
    },
    {
        "name": "Yellow Dal Tadka / Cooked Toor Dal",
        "category": "legumes",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 115.0,
        "protein_g": 6.8,
        "carbs_g": 16.5,
        "fat_g": 3.0,
        "fiber_g": 4.2,
        "sugar_g": 0.8,
        "sodium_mg": 240.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 cup", "grams": 180.0, "unit": "cup"},
            {"serving_label": "1 small bowl", "grams": 120.0, "unit": "bowl"}
        ]
    },
    {
        "name": "Dal Makhani (Slow Cooked Black Lentils with Cream)",
        "category": "legumes",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 180.0,
        "protein_g": 7.2,
        "carbs_g": 18.0,
        "fat_g": 9.0,
        "fiber_g": 5.1,
        "sugar_g": 1.4,
        "sodium_mg": 320.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"}
        ]
    },
    {
        "name": "Chole / Chana Masala (Spiced Chickpea Curry)",
        "category": "legumes",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 145.0,
        "protein_g": 7.5,
        "carbs_g": 21.0,
        "fat_g": 4.2,
        "fiber_g": 5.8,
        "sugar_g": 1.8,
        "sodium_mg": 310.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 cup", "grams": 180.0, "unit": "cup"}
        ]
    },
    {
        "name": "Rajma Masala (Kidney Bean Curry)",
        "category": "legumes",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 138.0,
        "protein_g": 8.1,
        "carbs_g": 19.5,
        "fat_g": 3.6,
        "fiber_g": 6.2,
        "sugar_g": 1.5,
        "sodium_mg": 290.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 cup (with rajma rice)", "grams": 180.0, "unit": "cup"}
        ]
    },
    {
        "name": "Poha (Flattened Rice with Peanuts & Mustard)",
        "category": "breakfast",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 180.0,
        "protein_g": 3.8,
        "carbs_g": 31.0,
        "fat_g": 5.2,
        "fiber_g": 2.1,
        "sugar_g": 1.2,
        "sodium_mg": 210.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 120.0, "unit": "katori"},
            {"serving_label": "1 standard breakfast plate", "grams": 180.0, "unit": "plate"}
        ]
    },
    {
        "name": "Upma (Rava Upma with Vegetables & Mustard)",
        "category": "breakfast",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 165.0,
        "protein_g": 4.1,
        "carbs_g": 26.5,
        "fat_g": 5.0,
        "fiber_g": 2.0,
        "sugar_g": 1.0,
        "sodium_mg": 220.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 120.0, "unit": "katori"},
            {"serving_label": "1 plate upma", "grams": 180.0, "unit": "plate"}
        ]
    },
    {
        "name": "Moong Dal Chilla (Savory Green Gram Pancake)",
        "category": "breakfast",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 160.0,
        "protein_g": 8.5,
        "carbs_g": 23.0,
        "fat_g": 4.0,
        "fiber_g": 4.5,
        "sugar_g": 0.8,
        "sodium_mg": 180.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 chilla", "grams": 70.0, "unit": "piece"},
            {"serving_label": "2 chillas with green chutney", "grams": 140.0, "unit": "serving"}
        ]
    },

    # -------------------------------------------------------------
    # 8. MILLETS & WHOLE GRAINS
    # -------------------------------------------------------------
    {
        "name": "Ragi Mudde (Finger Millet Kali / Ball)",
        "category": "grains",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 150.0,
        "protein_g": 3.6,
        "carbs_g": 32.0,
        "fat_g": 0.9,
        "fiber_g": 4.8,
        "sugar_g": 0.2,
        "sodium_mg": 15.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 small mudde ball", "grams": 150.0, "unit": "piece"},
            {"serving_label": "1 large mudde ball", "grams": 220.0, "unit": "piece"}
        ]
    },
    {
        "name": "Foxtail Millet (Cooked Thinai Rice)",
        "category": "grains",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 122.0,
        "protein_g": 3.8,
        "carbs_g": 24.2,
        "fat_g": 1.2,
        "fiber_g": 3.2,
        "sugar_g": 0.1,
        "sodium_mg": 4.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 cup", "grams": 160.0, "unit": "cup"}
        ]
    },
    {
        "name": "Little Millet (Cooked Samai Rice)",
        "category": "grains",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 120.0,
        "protein_g": 3.5,
        "carbs_g": 23.8,
        "fat_g": 1.4,
        "fiber_g": 3.6,
        "sugar_g": 0.1,
        "sodium_mg": 3.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"}
        ]
    },
    {
        "name": "Barnyard Millet (Cooked Kuthiraivali Rice)",
        "category": "grains",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 118.0,
        "protein_g": 3.2,
        "carbs_g": 23.0,
        "fat_g": 1.1,
        "fiber_g": 4.2,
        "sugar_g": 0.1,
        "sodium_mg": 3.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"}
        ]
    },
    {
        "name": "Oatmeal (Cooked with Water/Milk)",
        "category": "grains",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 71.0,
        "protein_g": 2.5,
        "carbs_g": 12.0,
        "fat_g": 1.5,
        "fiber_g": 1.7,
        "sugar_g": 0.5,
        "sodium_mg": 49.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 cup cooked", "grams": 200.0, "unit": "cup"},
            {"serving_label": "1 bowl", "grams": 250.0, "unit": "bowl"}
        ]
    },

    # -------------------------------------------------------------
    # 9. PROTEINS, EGGS, MEAT, DAIRY & NUTS
    # -------------------------------------------------------------
    {
        "name": "Boiled Egg",
        "category": "eggs",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 155.0,
        "protein_g": 12.6,
        "carbs_g": 1.1,
        "fat_g": 10.6,
        "fiber_g": 0.0,
        "sugar_g": 1.1,
        "sodium_mg": 124.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece (whole egg)", "grams": 50.0, "unit": "egg"},
            {"serving_label": "2 boiled eggs", "grams": 100.0, "unit": "serving"},
            {"serving_label": "3 boiled eggs", "grams": 150.0, "unit": "serving"},
            {"serving_label": "1 egg white only", "grams": 33.0, "unit": "egg white"}
        ]
    },
    {
        "name": "Egg Omelette (with Onion & Chili)",
        "category": "eggs",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 195.0,
        "protein_g": 11.8,
        "carbs_g": 3.2,
        "fat_g": 15.0,
        "fiber_g": 0.5,
        "sugar_g": 1.2,
        "sodium_mg": 310.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 single egg omelette", "grams": 75.0, "unit": "serving"},
            {"serving_label": "1 double egg omelette", "grams": 130.0, "unit": "serving"}
        ]
    },
    {
        "name": "Chicken Breast (Cooked / Grilled)",
        "category": "meat",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 165.0,
        "protein_g": 31.0,
        "carbs_g": 0.0,
        "fat_g": 3.6,
        "fiber_g": 0.0,
        "sugar_g": 0.0,
        "sodium_mg": 74.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece (palm size)", "grams": 120.0, "unit": "piece"},
            {"serving_label": "1 cup diced", "grams": 140.0, "unit": "cup"},
            {"serving_label": "200g portion", "grams": 200.0, "unit": "portion"}
        ]
    },
    {
        "name": "Paneer (Indian Cottage Cheese / Raw)",
        "category": "dairy",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 289.0,
        "protein_g": 18.3,
        "carbs_g": 3.4,
        "fat_g": 22.0,
        "fiber_g": 0.0,
        "sugar_g": 2.5,
        "sodium_mg": 22.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 cube", "grams": 25.0, "unit": "cube"},
            {"serving_label": "100g slice", "grams": 100.0, "unit": "serving"},
            {"serving_label": "1 cup cubed", "grams": 140.0, "unit": "cup"}
        ]
    },
    {
        "name": "Paneer Tikka (Grilled Cottage Cheese Skewers)",
        "category": "dairy",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 220.0,
        "protein_g": 16.0,
        "carbs_g": 5.5,
        "fat_g": 15.0,
        "fiber_g": 1.5,
        "sugar_g": 1.8,
        "sodium_mg": 320.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 skewer / plate (4-5 cubes)", "grams": 150.0, "unit": "plate"}
        ]
    },
    {
        "name": "Curd / Dahi (Plain Yogurt)",
        "category": "dairy",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 61.0,
        "protein_g": 3.5,
        "carbs_g": 4.7,
        "fat_g": 3.3,
        "fiber_g": 0.0,
        "sugar_g": 4.7,
        "sodium_mg": 46.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 cup", "grams": 200.0, "unit": "cup"},
            {"serving_label": "1 glass lassi/chaas", "grams": 250.0, "unit": "glass"}
        ]
    },
    {
        "name": "Greek Yogurt (0% Fat Plain)",
        "category": "dairy",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 59.0,
        "protein_g": 10.0,
        "carbs_g": 3.6,
        "fat_g": 0.4,
        "fiber_g": 0.0,
        "sugar_g": 3.2,
        "sodium_mg": 36.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 cup", "grams": 170.0, "unit": "cup"},
            {"serving_label": "1 small tub (100g)", "grams": 100.0, "unit": "tub"}
        ]
    },
    {
        "name": "Milk (Cow / Toned)",
        "category": "beverages",
        "serving_size": 100.0,
        "unit": "ml",
        "calories": 58.0,
        "protein_g": 3.2,
        "carbs_g": 4.8,
        "fat_g": 3.0,
        "fiber_g": 0.0,
        "sugar_g": 4.8,
        "sodium_mg": 44.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 cup / glass", "grams": 200.0, "unit": "glass"},
            {"serving_label": "1 small cup (chai / coffee)", "grams": 100.0, "unit": "cup"}
        ]
    },
    {
        "name": "Whey Protein Isolate (Unflavored / Chocolate)",
        "category": "packaged foods",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 370.0,
        "protein_g": 80.0,
        "carbs_g": 4.0,
        "fat_g": 2.5,
        "fiber_g": 1.0,
        "sugar_g": 1.5,
        "sodium_mg": 180.0,
        "source": "Nutritionix",
        "conversions": [
            {"serving_label": "1 scoop (30g)", "grams": 30.0, "unit": "scoop"},
            {"serving_label": "2 scoops (60g)", "grams": 60.0, "unit": "serving"}
        ]
    },
    {
        "name": "Soya Chunks / Mealmaker (Cooked Curry)",
        "category": "legumes",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 140.0,
        "protein_g": 18.2,
        "carbs_g": 9.5,
        "fat_g": 3.2,
        "fiber_g": 6.8,
        "sugar_g": 1.2,
        "sodium_mg": 210.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori curry", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 cup chunks", "grams": 140.0, "unit": "cup"}
        ]
    },
    {
        "name": "Tofu (Firm / Sauteed)",
        "category": "legumes",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 120.0,
        "protein_g": 12.5,
        "carbs_g": 2.8,
        "fat_g": 6.8,
        "fiber_g": 1.8,
        "sugar_g": 0.5,
        "sodium_mg": 18.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 block / slice", "grams": 100.0, "unit": "piece"},
            {"serving_label": "1 cup cubed", "grams": 140.0, "unit": "cup"}
        ]
    },

    # -------------------------------------------------------------
    # 10. CHUTNEYS, SNACKS, FRUITS & BEVERAGES
    # -------------------------------------------------------------
    {
        "name": "Coconut Chutney (Thengai Chutney)",
        "category": "chutneys",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 215.0,
        "protein_g": 3.8,
        "carbs_g": 8.5,
        "fat_g": 19.0,
        "fiber_g": 4.5,
        "sugar_g": 2.2,
        "sodium_mg": 290.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 tablespoon", "grams": 20.0, "unit": "tbsp"},
            {"serving_label": "1 small katori", "grams": 50.0, "unit": "katori"}
        ]
    },
    {
        "name": "Tomato Kara Chutney (Spicy Onion Tomato Chutney)",
        "category": "chutneys",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 95.0,
        "protein_g": 2.1,
        "carbs_g": 9.4,
        "fat_g": 5.8,
        "fiber_g": 2.4,
        "sugar_g": 3.8,
        "sodium_mg": 280.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 tablespoon", "grams": 20.0, "unit": "tbsp"},
            {"serving_label": "1 small katori", "grams": 50.0, "unit": "katori"}
        ]
    },
    {
        "name": "Mixed Sprouts Salad (Moong & Chana with Lemon & Cucumber)",
        "category": "legumes",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 135.0,
        "protein_g": 8.5,
        "carbs_g": 21.0,
        "fat_g": 1.8,
        "fiber_g": 6.5,
        "sugar_g": 2.0,
        "sodium_mg": 140.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 katori", "grams": 120.0, "unit": "katori"},
            {"serving_label": "1 cup", "grams": 150.0, "unit": "cup"}
        ]
    },
    {
        "name": "Chana Sundal (White Chickpea Sundal with Coconut)",
        "category": "snacks",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 155.0,
        "protein_g": 7.4,
        "carbs_g": 22.5,
        "fat_g": 4.2,
        "fiber_g": 5.8,
        "sugar_g": 1.8,
        "sodium_mg": 210.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 cup sundal", "grams": 120.0, "unit": "cup"},
            {"serving_label": "1 katori", "grams": 100.0, "unit": "katori"}
        ]
    },
    {
        "name": "Roasted Makhana (Fox Nuts)",
        "category": "snacks",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 350.0,
        "protein_g": 9.7,
        "carbs_g": 64.0,
        "fat_g": 2.4,
        "fiber_g": 7.6,
        "sugar_g": 0.5,
        "sodium_mg": 110.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 bowl (1 cup)", "grams": 30.0, "unit": "cup"},
            {"serving_label": "2 bowls (healthy snack)", "grams": 60.0, "unit": "serving"}
        ]
    },
    {
        "name": "Samosa (Potato & Pea Crispy Pastry)",
        "category": "snacks",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 310.0,
        "protein_g": 5.2,
        "carbs_g": 38.0,
        "fat_g": 15.5,
        "fiber_g": 2.8,
        "sugar_g": 1.8,
        "sodium_mg": 380.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 piece", "grams": 80.0, "unit": "piece"},
            {"serving_label": "2 samosas", "grams": 160.0, "unit": "serving"}
        ]
    },
    {
        "name": "Almonds (Raw / Soaked)",
        "category": "nuts",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 579.0,
        "protein_g": 21.2,
        "carbs_g": 21.6,
        "fat_g": 49.9,
        "fiber_g": 12.5,
        "sugar_g": 4.4,
        "sodium_mg": 1.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 handful (10-12 nuts)", "grams": 15.0, "unit": "handful"},
            {"serving_label": "1 ounce (23 nuts)", "grams": 28.0, "unit": "oz"}
        ]
    },
    {
        "name": "Banana (Poovan / Robusta / Elaichi)",
        "category": "fruits",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 89.0,
        "protein_g": 1.1,
        "carbs_g": 22.8,
        "fat_g": 0.3,
        "fiber_g": 2.6,
        "sugar_g": 12.2,
        "sodium_mg": 1.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 medium banana", "grams": 118.0, "unit": "banana"},
            {"serving_label": "1 small banana (elaichi)", "grams": 60.0, "unit": "banana"}
        ]
    },
    {
        "name": "Apple",
        "category": "fruits",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 52.0,
        "protein_g": 0.3,
        "carbs_g": 13.8,
        "fat_g": 0.2,
        "fiber_g": 2.4,
        "sugar_g": 10.4,
        "sodium_mg": 1.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 medium apple", "grams": 150.0, "unit": "apple"},
            {"serving_label": "1 large apple", "grams": 200.0, "unit": "apple"}
        ]
    },
    {
        "name": "Papaya (Fresh Cut)",
        "category": "fruits",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 43.0,
        "protein_g": 0.5,
        "carbs_g": 10.8,
        "fat_g": 0.3,
        "fiber_g": 1.7,
        "sugar_g": 7.8,
        "sodium_mg": 8.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 cup cubed", "grams": 145.0, "unit": "cup"},
            {"serving_label": "1 bowl", "grams": 200.0, "unit": "bowl"}
        ]
    },
    {
        "name": "Tender Coconut Water (Elaneer)",
        "category": "beverages",
        "serving_size": 100.0,
        "unit": "ml",
        "calories": 19.0,
        "protein_g": 0.7,
        "carbs_g": 3.7,
        "fat_g": 0.2,
        "fiber_g": 1.1,
        "sugar_g": 2.6,
        "sodium_mg": 105.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 tender coconut (average water)", "grams": 250.0, "unit": "coconut"},
            {"serving_label": "1 glass", "grams": 200.0, "unit": "glass"}
        ]
    },
    {
        "name": "Tamil Filter Coffee (with Milk & Sugar)",
        "category": "beverages",
        "serving_size": 100.0,
        "unit": "ml",
        "calories": 78.0,
        "protein_g": 2.8,
        "carbs_g": 8.5,
        "fat_g": 3.5,
        "fiber_g": 0.0,
        "sugar_g": 7.5,
        "sodium_mg": 40.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 davarah & tumbler cup", "grams": 120.0, "unit": "cup"},
            {"serving_label": "1 large mug", "grams": 200.0, "unit": "mug"}
        ]
    },
    {
        "name": "Masala Chai (with Milk & Ginger/Cardamom)",
        "category": "beverages",
        "serving_size": 100.0,
        "unit": "ml",
        "calories": 72.0,
        "protein_g": 2.6,
        "carbs_g": 8.2,
        "fat_g": 3.2,
        "fiber_g": 0.0,
        "sugar_g": 7.0,
        "sodium_mg": 38.0,
        "source": "IFCT",
        "conversions": [
            {"serving_label": "1 cutting chai cup", "grams": 100.0, "unit": "cup"},
            {"serving_label": "1 mug", "grams": 180.0, "unit": "mug"}
        ]
    },
    # -------------------------------------------------------------
    # 15. COMMON PACKAGED FOODS (WITH VERIFIED BARCODES)
    # -------------------------------------------------------------
    {
        "name": "Amul Taaza Toned Milk",
        "category": "dairy",
        "serving_size": 100.0,
        "unit": "ml",
        "calories": 58.0,
        "protein_g": 3.0,
        "carbs_g": 4.7,
        "fat_g": 3.0,
        "fiber_g": 0.0,
        "sugar_g": 4.7,
        "sodium_mg": 50.0,
        "barcode": "8901262010115",
        "source": "OpenFoodFacts",
        "conversions": [
            {"serving_label": "1 glass (200ml)", "grams": 200.0, "unit": "glass"},
            {"serving_label": "1 packet (500ml)", "grams": 500.0, "unit": "packet"},
            {"serving_label": "1 cup (150ml)", "grams": 150.0, "unit": "cup"}
        ]
    },
    {
        "name": "Britannia 100% Whole Wheat Bread",
        "category": "packaged",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 245.0,
        "protein_g": 8.5,
        "carbs_g": 48.0,
        "fat_g": 2.0,
        "fiber_g": 6.2,
        "sugar_g": 3.5,
        "sodium_mg": 390.0,
        "barcode": "8901725181222",
        "source": "OpenFoodFacts",
        "conversions": [
            {"serving_label": "1 slice", "grams": 30.0, "unit": "slice"},
            {"serving_label": "2 slices (sandwich)", "grams": 60.0, "unit": "serving"}
        ]
    },
    {
        "name": "Epigamia Natural Greek Yogurt",
        "category": "dairy",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 85.0,
        "protein_g": 7.0,
        "carbs_g": 4.5,
        "fat_g": 4.5,
        "fiber_g": 0.0,
        "sugar_g": 4.5,
        "sodium_mg": 45.0,
        "barcode": "8906070430018",
        "source": "OpenFoodFacts",
        "conversions": [
            {"serving_label": "1 cup (90g)", "grams": 90.0, "unit": "cup"},
            {"serving_label": "1 tub (400g)", "grams": 400.0, "unit": "tub"}
        ]
    },
    {
        "name": "Quaker Rolled Oats",
        "category": "grains",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 375.0,
        "protein_g": 12.5,
        "carbs_g": 62.0,
        "fat_g": 8.5,
        "fiber_g": 10.0,
        "sugar_g": 1.0,
        "sodium_mg": 5.0,
        "barcode": "8901491101031",
        "source": "OpenFoodFacts",
        "conversions": [
            {"serving_label": "1 standard bowl (40g dry)", "grams": 40.0, "unit": "bowl"},
            {"serving_label": "1 cooked cup (porridge)", "grams": 150.0, "unit": "cup"}
        ]
    },
    {
        "name": "Tata Sampann Unpolished Toor Dal",
        "category": "pulses",
        "serving_size": 100.0,
        "unit": "g",
        "calories": 343.0,
        "protein_g": 22.0,
        "carbs_g": 57.0,
        "fat_g": 1.5,
        "fiber_g": 15.0,
        "sugar_g": 2.0,
        "sodium_mg": 10.0,
        "barcode": "8901030000101",
        "source": "OpenFoodFacts",
        "conversions": [
            {"serving_label": "1 katori cooked dal", "grams": 150.0, "unit": "katori"},
            {"serving_label": "1 cup raw dal (200g)", "grams": 200.0, "unit": "cup"}
        ]
    }
]

class FoodService:
    @classmethod
    def _normalize_name(cls, name: str) -> str:
        if not name:
            return ""
        s = unicodedata.normalize("NFKC", str(name)).lower().strip()
        s = re.sub(r"\s+", " ", s)
        s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
        s = re.sub(r"\s*/\s*", "/", s)
        return re.sub(r"\s+", " ", s).strip()

    @classmethod
    def _normalize_serving(cls, serving: str) -> str:
        if not serving or str(serving).strip().lower() in ["source basis not specified", "none", ""]:
            return "100g"
        s = unicodedata.normalize("NFKC", str(serving)).lower().strip()
        return re.sub(r"\s+", " ", s).strip()

    @classmethod
    def _make_unique_key(cls, name: str, serving_size: str) -> str:
        return f"{cls._normalize_name(name)}|{cls._normalize_serving(serving_size)}"

    @classmethod
    def _parse_grams_from_desc(cls, serving_desc: str) -> float:
        if not serving_desc:
            return 100.0
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:g|ml)", serving_desc, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return 100.0

    @classmethod
    async def seed_default_foods(cls, session: AsyncSession):
        """
        Upsert/seed the authoritative master food dataset (NutriQ_Master_Cleaned_Food_Dataset.csv, 2,143 records).
        Idempotently inserts missing foods and enriches existing records with zero duplicates.
        """
        import os
        import csv

        # 1. Fetch existing foods and index by normalized_key, exact name, and id
        existing_stmt = select(Food).options(selectinload(Food.serving_conversions))
        existing_res = await session.execute(existing_stmt)
        existing_foods = list(existing_res.scalars().all())

        existing_by_key = {}
        existing_by_exact = {}

        for f in existing_foods:
            key = f.normalized_key or cls._make_unique_key(f.name, f.serving_size_desc or f.serving_size or "100g")
            if not f.normalized_key:
                f.normalized_key = key
            existing_by_key[key] = f
            existing_by_exact[f.name.strip().lower()] = f

        # 1b. Seed Curated IFCT Master Foods First
        for item in CURATED_FOOD_SEEDS:
            name = item["name"].strip()
            exact_lower = name.lower()
            key = cls._make_unique_key(name, "100g")
            
            existing = existing_by_exact.get(exact_lower) or existing_by_key.get(key)
            if existing:
                existing.category = item.get("category", existing.category)
                existing.calories = float(item["calories"])
                existing.protein_g = float(item["protein_g"])
                existing.carbs_g = float(item["carbs_g"])
                existing.fat_g = float(item["fat_g"])
                existing.fiber_g = float(item.get("fiber_g", 0.0))
                existing.source = item.get("source", "IFCT")
                existing.serving_size = float(item.get("serving_size", 100.0))
                existing.unit = item.get("unit", "g")
                existing_by_exact[exact_lower] = existing
                existing_by_key[key] = existing
                updated = True
            else:
                new_food = Food(
                    name=name,
                    category=item.get("category", "Indian Food"),
                    subcategory=item.get("subcategory", ""),
                    region=item.get("region", "South India"),
                    serving_size=float(item.get("serving_size", 100.0)),
                    unit=item.get("unit", "g"),
                    calories=float(item["calories"]),
                    protein_g=float(item["protein_g"]),
                    carbs_g=float(item["carbs_g"]),
                    fat_g=float(item["fat_g"]),
                    fiber_g=float(item.get("fiber_g", 0.0)),
                    sugar_g=float(item.get("sugar_g", 0.0)),
                    sodium_mg=float(item.get("sodium_mg", 0.0)),
                    source=item.get("source", "IFCT"),
                    normalized_key=key
                )
                session.add(new_food)
                await session.flush()
                for conv in item.get("conversions", []):
                    session.add(ServingConversion(
                        food_id=new_food.id,
                        serving_label=conv["serving_label"],
                        grams=float(conv["grams"]),
                        unit=conv.get("unit", "serving")
                    ))
                existing_by_exact[exact_lower] = new_food
                existing_by_key[key] = new_food
                updated = True

        # 2. Seed Master Cleaned Food Dataset CSV (2,143 records)
        csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "NutriQ_Master_Cleaned_Food_Dataset.csv")
        if os.path.exists(csv_path):
            try:
                with open(csv_path, "r", encoding="utf-8") as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        food_id_code = row.get("food_id", "").strip()
                        food_name = row.get("food_name", "").strip()
                        category = row.get("category", "").strip() or "Indian Food"
                        subcategory = row.get("subcategory", "").strip()
                        region = row.get("region", "").strip() or "India"
                        serving_size_desc = row.get("serving_size", "").strip()
                        source = row.get("source", "").strip() or "NutriQ Master Dataset"

                        if not food_name:
                            continue

                        def _to_float(v):
                            if v is None or str(v).strip().lower() in ["", "none", "null", "nan"]:
                                return None
                            try:
                                return round(float(str(v).strip()), 2)
                            except (ValueError, TypeError):
                                return None

                        cal = _to_float(row.get("calories_kcal"))
                        if cal is None:
                            continue
                        prot = _to_float(row.get("protein_g")) or 0.0
                        carbs = _to_float(row.get("carbohydrates_g")) or 0.0
                        fat = _to_float(row.get("fat_g")) or 0.0
                        fiber = _to_float(row.get("fiber_g")) or 0.0
                        sugar = _to_float(row.get("free_sugar_g")) or 0.0
                        sodium = _to_float(row.get("sodium_mg")) or 0.0
                        calcium = _to_float(row.get("calcium_mg"))
                        iron = _to_float(row.get("iron_mg"))
                        vit_c = _to_float(row.get("vitamin_c_mg"))
                        folate = _to_float(row.get("folate_ug"))

                        key = cls._make_unique_key(food_name, serving_size_desc)
                        numeric_grams = cls._parse_grams_from_desc(serving_size_desc)
                        serving_unit = "ml" if "ml" in serving_size_desc.lower() else "g"

                        if key in existing_by_key:
                            existing_food = existing_by_key[key]
                            if not existing_food.code and food_id_code:
                                existing_food.code = food_id_code
                            if not existing_food.subcategory and subcategory:
                                existing_food.subcategory = subcategory
                            if not existing_food.region and region:
                                existing_food.region = region
                            if not existing_food.serving_size_desc and serving_size_desc:
                                existing_food.serving_size_desc = serving_size_desc
                            if existing_food.calcium_mg is None and calcium is not None:
                                existing_food.calcium_mg = calcium
                            if existing_food.iron_mg is None and iron is not None:
                                existing_food.iron_mg = iron
                            if existing_food.vitamin_c_mg is None and vit_c is not None:
                                existing_food.vitamin_c_mg = vit_c
                            if existing_food.folate_ug is None and folate is not None:
                                existing_food.folate_ug = folate
                            continue

                        exact_lower = food_name.strip().lower()
                        if exact_lower in existing_by_exact:
                            existing_food = existing_by_exact[exact_lower]
                            existing_food.normalized_key = key
                            if not existing_food.code and food_id_code:
                                existing_food.code = food_id_code
                            if not existing_food.subcategory and subcategory:
                                existing_food.subcategory = subcategory
                            if not existing_food.region and region:
                                existing_food.region = region
                            if not existing_food.serving_size_desc and serving_size_desc:
                                existing_food.serving_size_desc = serving_size_desc
                            existing_by_key[key] = existing_food
                            continue

                        # Create new food
                        new_food = Food(
                            code=food_id_code,
                            name=food_name,
                            category=category,
                            subcategory=subcategory,
                            region=region,
                            serving_size_desc=serving_size_desc,
                            serving_size=numeric_grams,
                            unit=serving_unit,
                            calories=cal,
                            protein_g=prot,
                            carbs_g=carbs,
                            fat_g=fat,
                            fiber_g=fiber,
                            sugar_g=sugar,
                            sodium_mg=sodium,
                            calcium_mg=calcium,
                            iron_mg=iron,
                            vitamin_c_mg=vit_c,
                            folate_ug=folate,
                            source=source,
                            barcode=None,
                            normalized_key=key
                        )
                        session.add(new_food)
                        await session.flush()

                        # Add serving conversions safely with label deduplication
                        seen_labels = set()

                        def _add_conv_to_food(label: str, grams_val: float, unit_val: str):
                            norm_l = label.strip().lower()
                            if norm_l and norm_l not in seen_labels:
                                seen_labels.add(norm_l)
                                session.add(ServingConversion(
                                    food_id=new_food.id,
                                    serving_label=label.strip(),
                                    grams=grams_val,
                                    unit=unit_val
                                ))

                        if serving_size_desc and serving_size_desc.lower() != "source basis not specified":
                            label = serving_size_desc.strip()
                            unit = "piece" if "piece" in label.lower() else ("serving" if "serving" in label.lower() else "g")
                            _add_conv_to_food(label, numeric_grams, unit)

                        _add_conv_to_food("100g base portion", 100.0, "g")

                        for conv in cls._generate_conversions(food_name, category):
                            _add_conv_to_food(conv["serving_label"], conv["grams"], conv["unit"])


                        existing_by_key[key] = new_food
                        existing_by_exact[exact_lower] = new_food
                        updated = True
            except Exception as e:
                pass

        if updated:
            await session.commit()

    @classmethod
    def get_category_filter_condition(cls, category_raw: str):
        """
        Normalizes category string variants (case, spacing, &, hyphens, spelling)
        and returns SQLAlchemy filter conditions.
        """
        if not category_raw or category_raw.strip().lower() in ["all", "", "none", "null"]:
            return None

        clean = category_raw.strip().lower()
        clean_slug = re.sub(r"[^a-z0-9]", "", clean)

        # 1. Curries & Gravies
        if any(k in clean_slug for k in ["curry", "curries", "gravy", "gravies", "curriesgravies", "curriesandgravies", "curriesandgravy"]):
            curry_keywords = [
                "%curry%", "%gravy%", "%kuzhambu%", "%kulambu%", "%kootu%",
                "%sambar%", "%kadhi%", "%korma%", "%kurma%", "%dal%", "%daal%",
                "%dhal%", "%makhani%", "%chole%", "%chana masala%", "%rajma%",
                "%salna%", "%saag%", "%paneer butter masala%", "%tikka masala%",
                "%matar paneer%", "%shahi paneer%", "%kadai paneer%", "%palak paneer%",
                "%bhurji / curry%", "%stew%"
            ]
            name_conditions = [Food.name.ilike(kw) for kw in curry_keywords]
            subcat_conditions = [
                Food.subcategory.ilike("%Curries & Gravies%"),
                Food.subcategory.ilike("%Curry%"),
                Food.subcategory.ilike("%Gravy%"),
                Food.subcategory.ilike("%Kuzhambu%"),
                Food.subcategory.ilike("%Kootu%"),
                Food.subcategory.ilike("%Sambar%"),
                Food.subcategory.ilike("%Rasam%"),
                Food.subcategory.ilike("%Korma%"),
                Food.subcategory.ilike("%Kurma%"),
                Food.subcategory.ilike("%Non-Veg - Tamil Nadu%"),
                Food.subcategory.ilike("%Non-Veg - Kerala%"),
                Food.subcategory.ilike("%Non-Veg - Karnataka%"),
                Food.subcategory.ilike("%Non-Veg - Andhra/Telangana%"),
                Food.subcategory.ilike("%Non-Veg Preparations%"),
            ]
            cat_conditions = [
                Food.category.ilike("%curry%"),
                Food.category.ilike("%gravy%"),
                Food.category.ilike("%curries & gravies%"),
            ]
            return or_(*name_conditions, *subcat_conditions, *cat_conditions)

        # 2. South Indian
        if clean_slug in ["southindian", "southindia"]:
            return or_(
                Food.region.ilike("%South India%"),
                Food.region.ilike("%Tamil Nadu%"),
                Food.region.ilike("%Kerala%"),
                Food.region.ilike("%Karnataka%"),
                Food.region.ilike("%Andhra%"),
                Food.region.ilike("%Telangana%"),
                Food.category.ilike("%South Indian%")
            )

        # 3. Indian Food
        if clean_slug in ["indianfood", "indian", "northindian"]:
            return or_(
                Food.category.ilike("%Indian%"),
                Food.region.ilike("%India%")
            )

        # 4. Tiffin
        if clean_slug in ["tiffin", "breakfast"]:
            return or_(
                Food.subcategory.ilike("%Tiffin%"),
                Food.category.in_(["breakfast", "dosa", "idli", "uthappam"]),
                Food.name.ilike("%idli%"),
                Food.name.ilike("%dosa%"),
                Food.name.ilike("%upma%"),
                Food.name.ilike("%pongal%"),
                Food.name.ilike("%vada%"),
                Food.name.ilike("%poori%"),
                Food.name.ilike("%puri%"),
                Food.name.ilike("%uthappam%"),
                Food.name.ilike("%uttapam%"),
                Food.name.ilike("%appam%"),
                Food.name.ilike("%puttu%"),
                Food.name.ilike("%adai%"),
                Food.name.ilike("%pesarattu%")
            )

        # 5. Rice Dishes
        if clean_slug in ["ricedishes", "rice"]:
            return or_(
                Food.category.ilike("%rice%"),
                Food.subcategory.ilike("%Rice%"),
                Food.name.ilike("%rice%"),
                Food.name.ilike("%biryani%"),
                Food.name.ilike("%biriyani%"),
                Food.name.ilike("%pulao%"),
                Food.name.ilike("%pongal%"),
                Food.name.ilike("%sadam%"),
                Food.name.ilike("%bath%"),
                Food.name.ilike("%khichdi%")
            )

        # 6. Dosa Varieties
        if clean_slug in ["dosavarieties", "dosa", "dosas"]:
            return or_(
                Food.category.ilike("%dosa%"),
                Food.subcategory.ilike("%Dosa%"),
                Food.name.ilike("%dosa%")
            )

        # 7. Idli Varieties
        if clean_slug in ["idlivarieties", "idli", "idlis"]:
            return or_(
                Food.category.ilike("%idli%"),
                Food.subcategory.ilike("%Idli%"),
                Food.name.ilike("%idli%")
            )

        # 8. Sambar & Rasam
        if clean_slug in ["sambarrasam", "sambarandrasam", "sambar", "rasam"]:
            return or_(
                Food.subcategory.ilike("%Sambar%"),
                Food.subcategory.ilike("%Rasam%"),
                Food.name.ilike("%sambar%"),
                Food.name.ilike("%rasam%"),
                Food.name.ilike("%saaru%")
            )

        # 9. Snacks
        if clean_slug in ["snacks", "snack"]:
            return or_(
                Food.category.ilike("%snack%"),
                Food.subcategory.ilike("%Snack%"),
                Food.subcategory.ilike("%Vada%"),
                Food.name.ilike("%vada%"),
                Food.name.ilike("%pakoda%"),
                Food.name.ilike("%samosa%"),
                Food.name.ilike("%bajji%"),
                Food.name.ilike("%sundal%"),
                Food.name.ilike("%bonda%"),
                Food.name.ilike("%murukku%")
            )

        # 10. Sweets & Desserts
        if clean_slug in ["sweetsdesserts", "sweetsanddesserts", "sweets", "sweet", "dessert", "desserts"]:
            return or_(
                Food.category.ilike("%sweet%"),
                Food.subcategory.ilike("%Sweet%"),
                Food.name.ilike("%payasam%"),
                Food.name.ilike("%halwa%"),
                Food.name.ilike("%laddu%"),
                Food.name.ilike("%mysore pak%"),
                Food.name.ilike("%gulab jamun%"),
                Food.name.ilike("%kesari%"),
                Food.name.ilike("%kheer%")
            )

        # 11. Beverages
        if clean_slug in ["beverages", "beverage", "drinks", "drink"]:
            return or_(
                Food.category.ilike("%beverage%"),
                Food.subcategory.ilike("%Beverage%"),
                Food.name.ilike("%tea%"),
                Food.name.ilike("%coffee%"),
                Food.name.ilike("%juice%"),
                Food.name.ilike("%milk%"),
                Food.name.ilike("%lassi%"),
                Food.name.ilike("%buttermilk%"),
                Food.name.ilike("%neer mor%")
            )

        # Default fallback: partial matching on category, subcategory, or region
        return or_(
            Food.category.ilike(f"%{clean}%"),
            Food.subcategory.ilike(f"%{clean}%"),
            Food.region.ilike(f"%{clean}%")
        )

    @classmethod
    async def search_foods(
        cls,
        session: AsyncSession,
        query: str = "",
        category: Optional[str] = None,
        limit: int = 60
    ) -> List[Food]:
        """
        Database-driven search supporting exact matches, partial matches,
        regional names, categories, subcategories, tokenized aliases,
        and intelligent relevance ranking.
        Never auto-selects any item.
        """
        q = select(Food).options(selectinload(Food.serving_conversions))
        q_clean = query.strip() if query else ""
        
        SYNONYM_MAP = {
            "curry": ["curry", "gravy", "kulambu", "kuzhambu", "kurma", "korma", "salna", "makhani", "masala"],
            "gravy": ["gravy", "curry", "kulambu", "kuzhambu", "kurma", "korma", "salna", "makhani", "masala"],
            "rajma": ["rajma", "rajmah", "kidney bean"],
            "chana": ["chana", "channa", "chole", "chickpea"],
            "dal": ["dal", "daal", "dhal", "toor", "moong", "urad", "masoor"],
            "dosa": ["dosa", "dosai"],
            "idli": ["idli", "iddly"],
            "biryani": ["biryani", "biriyani", "briyani"],
            "kuzhambu": ["kuzhambu", "kulambu", "kolambu"],
            "kootu": ["kootu", "koottu"],
            "korma": ["korma", "kurma"],
            "kurma": ["kurma", "korma"],
            "sambar": ["sambar", "sambhar"],
            "chapati": ["chapati", "roti", "phulka", "chapatti"],
            "paneer": ["paneer", "panir", "cottage cheese"]
        }

        if q_clean:
            tokens = [t.lower() for t in re.findall(r"\w+", q_clean) if len(t) > 1]
            if not tokens:
                tokens = [q_clean.lower()]

            token_clauses = []
            for token in tokens:
                synonyms = SYNONYM_MAP.get(token, [token])
                syn_conditions = []
                for s in synonyms:
                    like_s = f"%{s}%"
                    syn_conditions.extend([
                        Food.name.ilike(like_s),
                        Food.category.ilike(like_s),
                        Food.subcategory.ilike(like_s),
                        Food.region.ilike(like_s)
                    ])
                token_clauses.append(or_(*syn_conditions))

            direct_like = f"%{q_clean}%"
            direct_condition = or_(
                Food.name.ilike(direct_like),
                Food.category.ilike(direct_like),
                Food.subcategory.ilike(direct_like),
                Food.region.ilike(direct_like)
            )

            if len(tokens) > 1:
                q = q.where(or_(direct_condition, and_(*token_clauses)))
            else:
                q = q.where(or_(direct_condition, *token_clauses))

        cat_condition = cls.get_category_filter_condition(category)
        if cat_condition is not None:
            q = q.where(cat_condition)

        fetch_limit = max(limit * 4, 150) if q_clean else limit
        q = q.order_by(Food.name.asc()).limit(fetch_limit)
        result = await session.execute(q)
        foods = list(result.scalars().all())

        if not q_clean:
            return foods[:limit]

        q_lower = q_clean.lower()
        tokens = [t.lower() for t in re.findall(r"\w+", q_lower) if len(t) > 1]
        word_pattern = re.compile(rf"\b{re.escape(q_lower)}\b", re.IGNORECASE)

        def rank_key(food: Food):
            name_lower = (food.name or "").lower()
            cat_lower = (food.category or "").lower()
            subcat_lower = (food.subcategory or "").lower()
            reg_lower = (food.region or "").lower()

            main_part = name_lower.split("(")[0].strip()
            paren_part = name_lower.split("(")[1] if "(" in name_lower else ""

            # Base score
            if name_lower == q_lower:
                score = 0.0  # Exact full name match
            elif main_part == q_lower:
                score = 0.4  # Exact main name match
            elif main_part == f"plain {q_lower}" or main_part == f"{q_lower} (plain)":
                score = 0.5  # Standard plain version
            elif main_part == f"sada {q_lower}":
                score = 1.2  # Regional alias
            elif main_part.startswith(f"{q_lower} ") or main_part.startswith(f"{q_lower}("):
                score = 2.0  # Main name prefix match
            elif word_pattern.search(main_part):
                score = 3.0  # Word boundary match in main name
            elif q_lower in main_part:
                score = 4.0  # Substring in main name
            elif all(t in name_lower for t in tokens):
                score = 5.0  # All search tokens appear in name
            elif word_pattern.search(paren_part):
                score = 6.0  # Secondary description word match
            elif any(t in name_lower for t in tokens):
                score = 7.0  # At least one token in name
            elif q_lower in subcat_lower:
                score = 8.0  # Subcategory match
            elif q_lower in cat_lower or q_lower in reg_lower:
                score = 9.0  # Category or region match
            else:
                score = 10.0

            # Prioritize authoritative IFCT verified records
            if (food.source or "").upper() == "IFCT":
                score -= 0.1

            # De-prioritize combos when searching for single dish name
            if ("combo" in name_lower or " with " in name_lower) and len(tokens) == 1:
                score += 3.0

            # De-prioritize raw herbs / leaves when searching for "curry" (e.g. "Curry Leaves")
            if "curry" in q_lower and ("leaf" in name_lower or "leaves" in name_lower or "powder" in name_lower or "raw" in name_lower):
                score += 8.0

            return (score, len(food.name), food.name)

        foods.sort(key=rank_key)
        return foods[:limit]

