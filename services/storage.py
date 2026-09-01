import json
import os

DATA_FILE = "data/staff.json"

def load_staff():
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_staff(staff_list):
    if not os.path.exists("data"):
        os.makedirs("data")
    with open(DATA_FILE, "w") as f:
        json.dump(staff_list, f, indent=4)

