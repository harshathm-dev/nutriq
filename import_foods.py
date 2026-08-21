"""
NUTRIQ — Master Food Catalog Import & Duplicate Prevention Pipeline
Root-level entrypoint redirecting to nutriq-backend/import_foods.py
"""

import os
import sys

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "nutriq-backend"))
sys.path.insert(0, BACKEND_DIR)

from import_foods import import_master_dataset

if __name__ == "__main__":
    import_master_dataset()
