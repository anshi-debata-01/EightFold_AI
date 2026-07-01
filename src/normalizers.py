"""
normalizers.py
--------------
Job: Take messy raw values (from loaders.py) and turn them into
clean, consistent values. Also extracts structured facts (skills,
experience, headline, email, phone) out of free-text notes.

Every function here is small and does ONE thing, so each one is
easy to explain on its own in an interview.
"""

import re


# ---------------------------------------------------------------------
# Canonical skill mapping (abbreviation -> full skill name)
# ---------------------------------------------------------------------
SKILL_ALIASES = {
    "py": "python",
    "ml": "machine learning",
    "ai": "artificial intelligence",
}


def normalize_name(raw_name):
    """
    Turn a raw name into Title Case.
    "john doe" -> "John Doe"
    Handles missing/empty names safely.
    """
    if not raw_name:
        return None
    return raw_name.strip().title()


def normalize_email(raw_email):
    """
    Clean an email address:
    - strip surrounding whitespace
    - lowercase it
    Returns None if there's nothing usable.
    "  John.Doe@gmail.com " -> "john.doe@gmail.com"
    """
    if not raw_email:
        return None
    cleaned = raw_email.strip().lower()
    return cleaned if cleaned else None


def is_valid_email(email):
    """
    Very simple email format check: something@something.something
    Used by validator.py, not meant to be a full RFC validator.
    """
    if not email:
        return False
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(pattern, email) is not None


def normalize_phone(raw_phone, default_country_code="91"):
    """
    Convert a raw phone number into a simple E.164-like format:
    "9876543210"   -> "+919876543210"
    "98765 43222"  -> "+919876543222"   (spaces/dashes stripped)
    "+919876543210" -> "+919876543210"  (already normalized)

    Returns None if there aren't enough digits to form a real number.
    """
    if not raw_phone:
        return None

    # Keep only digits (and a leading + if present)
    has_plus = raw_phone.strip().startswith("+")
    digits = re.sub(r"\D", "", raw_phone)

    if not digits:
        return None

    if has_plus:
        return "+" + digits

    # If the number already includes the country code (e.g. starts
    # with "91" and is 12 digits long), don't add it again.
    if len(digits) == 12 and digits.startswith(default_country_code):
        return "+" + digits

    # Standard 10-digit local number -> add country code.
    if len(digits) == 10:
        return f"+{default_country_code}{digits}"

    # Fallback: not a recognizable length, but still return something
    # rather than silently dropping data. Mark it as best-effort.
    return "+" + digits


def is_valid_phone(phone):
    """
    Simple phone format check: "+" followed by 11-15 digits.
    Used by validator.py.
    """
    if not phone:
        return False
    pattern = r"^\+\d{11,15}$"
    return re.match(pattern, phone) is not None


def normalize_skill(raw_skill):
    """
    Clean a single skill name and map known abbreviations to their
    canonical full name.
    "Py"  -> "python"
    "ML"  -> "machine learning"
    "SQL" -> "sql"   (no alias, just lowercased)
    """
    if not raw_skill:
        return None
    cleaned = raw_skill.strip().lower()
    if not cleaned:
        return None
    return SKILL_ALIASES.get(cleaned, cleaned)


def normalize_location(raw_location):
    """
    Split a "City, Region, Country" string into a structured dict.
    "Chennai, Tamil Nadu, India" ->
        {"city": "Chennai", "region": "Tamil Nadu", "country": "India"}

    If the format doesn't match (fewer/more parts), we fill what we
    can and leave the rest as None - never crash.
    """
    empty = {"city": None, "region": None, "country": None}
    if not raw_location:
        return empty

    parts = [p.strip() for p in raw_location.split(",") if p.strip()]
    if len(parts) >= 3:
        return {"city": parts[0], "region": parts[1], "country": parts[2]}
    if len(parts) == 2:
        return {"city": parts[0], "region": None, "country": parts[1]}
    if len(parts) == 1:
        return {"city": parts[0], "region": None, "country": None}
    return empty


# ---------------------------------------------------------------------
# Free-text extraction helpers (for the TXT source)
# ---------------------------------------------------------------------

def extract_skills_from_text(text):
    """
    Find a line like "Skills: Python, ML, Django, SQL" and return
    the list of normalized skill names.
    Returns [] if no "Skills:" line is found.
    """
    match = re.search(r"Skills?:\s*(.+)", text)
    if not match:
        return []
    raw_list = match.group(1).split(",")
    skills = [normalize_skill(s) for s in raw_list]
    return [s for s in skills if s]


def extract_years_experience(text):
    """
    Find a phrase like "6 years of experience" or "4 years experience"
    and return the number as an int. Returns None if not found.
    """
    match = re.search(r"(\d+)\s*\+?\s*years?", text, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def extract_headline(text):
    """
    Pull a short "headline" (job title) out of free text.
    Looks for a known pattern like:
        "... is a Senior Backend Engineer ..."
        "... - Data Scientist, ..."
        "... works as a Product Manager ..."

    This is a simple heuristic, not full NLP - good enough for
    recruiter-style notes and easy to explain in an interview.
    """
    patterns = [
        r"is an? ([A-Z][\w\s]{2,40}?)(?:\s+with|\s*,|\.|\s+building)",
        r"-\s*([A-Z][\w\s]{2,40}?),",
        r"works as an? ([A-Z][\w\s]{2,40}?)(?:\s+with|\s*,|\.)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def extract_email_from_text(text):
    """
    Find an email address anywhere in free text, e.g. "Email: a@b.com".
    Returns None if not found.
    """
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return match.group(0) if match else None


def extract_phone_from_text(text):
    """
    Find a phone number anywhere in free text, e.g. "Phone: 9876543222".
    Returns None if not found.
    """
    match = re.search(r"Phone:\s*([\d\s\-\+]{8,15})", text)
    return match.group(1).strip() if match else None


def extract_name_from_text(text):
    """
    Best-effort guess at a candidate's name: take the first 1-3
    capitalized words at the very start of the text block.
    "Sneha Iyer works as a Product Manager..." -> "Sneha Iyer"
    Returns None if no clear name-looking pattern is found.
    """
    match = re.match(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})", text)
    return match.group(1).strip() if match else None
