import json
import os

DATA_FILE = "data/staff.json"

def load_staff():
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        return []
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_staff(staff_list):
    if not os.path.exists("data"):
        os.makedirs("data")
    with open(DATA_FILE, "w") as f:
        json.dump(staff_list, f, indent=4)
