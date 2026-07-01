"""
loaders.py
----------
Job: Read raw data from input files and turn it into simple Python
data structures (lists of dicts). This file does NOT clean or
interpret the data - it only "loads" it as-is. Cleaning happens
later in normalizers.py.

Why separate loading from cleaning?
If tomorrow we add a new source (e.g. a JSON ATS export), we only
add a new load_xxx() function here. The rest of the pipeline does
not need to change. This is "single responsibility" in practice.
"""

import csv
import re


def load_csv(file_path):
    """
    Read a recruiter CSV file and return a list of dicts.

    Each dict looks like:
    {
        "candidate_id": "C001",
        "name": "john doe",
        "email": "John.Doe@gmail.com",
        "phone": "9876543210",
        "location": "Chennai, Tamil Nadu, India"
    }

    If the file is missing, we return an empty list instead of
    crashing - the pipeline must survive a missing/garbage source.
    """
    rows = []
    try:
        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except FileNotFoundError:
        print(f"[loaders.py] WARNING: CSV file not found: {file_path}")
    return rows


def load_txt(file_path):
    """
    Read a recruiter notes TXT file and split it into per-candidate
    text blocks.

    The notes file uses this simple format (one block per candidate):

        Candidate: C001
        John is a Senior Backend Engineer with around 6 years of experience.
        Skills: Python, ML, Django, SQL
        ...

        Candidate: C002
        ...

    Returns a list of dicts:
    [
        {"candidate_id": "C001", "text": "John is a Senior Backend..."},
        {"candidate_id": "C002", "text": "..."},
    ]

    The raw "text" is handed to normalizers.py, which pulls out
    skills, years of experience, headline, email, phone, etc.
    """
    blocks = []
    try:
        with open(file_path, mode="r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"[loaders.py] WARNING: TXT file not found: {file_path}")
        return blocks

    # Split the file into chunks, one per "Candidate: <id>" marker.
    # re.split keeps the captured id because of the parentheses.
    parts = re.split(r"Candidate:\s*(\S+)", content)

    # parts[0] is whatever came before the first "Candidate:" marker
    # (usually empty), so we start at index 1 and step by 2:
    # parts[1] = candidate_id, parts[2] = text, parts[3] = next id, ...
    for i in range(1, len(parts), 2):
        candidate_id = parts[i].strip()
        text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if candidate_id:
            blocks.append({"candidate_id": candidate_id, "text": text})

    return blocks
