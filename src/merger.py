"""
merger.py
---------
Job: Combine the normalized CSV row and TXT block for ONE candidate
into a single canonical profile. Also computes confidence scores
and records provenance (where each field's value came from).

Design choice (merge policy):
- CSV is "structured" and recruiter-entered directly, so we trust
  it more: CSV confidence = 0.9
- TXT is "unstructured" free text, parsed with regex, so we trust
  it less: TXT confidence = 0.7
- For single-value fields (name, email, phone, location, headline,
  years_experience): if both sources have a value, CSV wins, but
  we still record that TXT *had* a value via provenance.
- For multi-value fields (skills): we COMBINE values from both
  sources instead of picking a winner, and average the confidence
  if a skill appears in both.
"""

CSV_CONFIDENCE = 0.9
TXT_CONFIDENCE = 0.7


def _pick_field(field_name, csv_value, txt_value, csv_source, txt_source, provenance):
    """
    Helper: choose a value for a single-value field.
    CSV wins if both are present. Records provenance either way.
    Returns (chosen_value, confidence_for_this_field) or (None, 0.0).
    """
    if csv_value not in (None, ""):
        provenance.append({"field": field_name, "source": csv_source, "method": "direct"})
        return csv_value, CSV_CONFIDENCE

    if txt_value not in (None, ""):
        provenance.append({"field": field_name, "source": txt_source, "method": "extracted"})
        return txt_value, TXT_CONFIDENCE

    return None, 0.0


def _merge_skills(csv_skills, txt_skills, csv_source, txt_source, provenance):
    """
    Combine skills from both sources into the canonical skills list:
    [{"name": "python", "confidence": 0.9, "sources": ["recruiter.csv"]}, ...]

    If a skill appears in BOTH sources, its confidence is the
    average of CSV_CONFIDENCE and TXT_CONFIDENCE, and both sources
    are listed.
    """
    skill_map = {}  # name -> {"confidences": [...], "sources": [...]}

    for skill in csv_skills:
        skill_map.setdefault(skill, {"confidences": [], "sources": []})
        skill_map[skill]["confidences"].append(CSV_CONFIDENCE)
        skill_map[skill]["sources"].append(csv_source)

    for skill in txt_skills:
        skill_map.setdefault(skill, {"confidences": [], "sources": []})
        skill_map[skill]["confidences"].append(TXT_CONFIDENCE)
        skill_map[skill]["sources"].append(txt_source)

    result = []
    for name, info in skill_map.items():
        avg_confidence = round(sum(info["confidences"]) / len(info["confidences"]), 2)
        result.append({
            "name": name,
            "confidence": avg_confidence,
            "sources": info["sources"],
        })
        provenance.append({
            "field": f"skills.{name}",
            "source": "+".join(info["sources"]),
            "method": "merged" if len(info["sources"]) > 1 else "direct/extracted",
        })

    # Sort alphabetically so output is deterministic (same input -> same output)
    result.sort(key=lambda s: s["name"])
    return result


def merge_profiles(candidate_id, csv_data, txt_data, csv_source="recruiter.csv", txt_source="recruiter_notes.txt"):
    """
    Build ONE canonical profile for a single candidate.

    csv_data: dict of normalized CSV fields for this candidate (or {} if absent)
        e.g. {"name": ..., "email": ..., "phone": ..., "location": {...}}

    txt_data: dict of normalized/extracted TXT fields for this candidate (or {} if absent)
        e.g. {"name": ..., "email": ..., "phone": ..., "headline": ...,
              "years_experience": ..., "skills": [...]}

    Returns a tuple: (profile_dict, provenance_list)
    The profile_dict matches the canonical schema (minus overall_confidence,
    which merger.calculate_confidence fills in afterwards).
    """
    provenance = []
    field_confidences = []

    # --- full_name ---
    full_name, conf = _pick_field(
        "full_name", csv_data.get("name"), txt_data.get("name"),
        csv_source, txt_source, provenance,
    )
    if full_name:
        field_confidences.append(conf)

    # --- emails (collect all unique, non-empty values seen) ---
    emails = []
    for email, src, method in [
        (csv_data.get("email"), csv_source, "direct"),
        (txt_data.get("email"), txt_source, "extracted"),
    ]:
        if email and email not in emails:
            emails.append(email)
            provenance.append({"field": "emails", "source": src, "method": method})
            field_confidences.append(CSV_CONFIDENCE if src == csv_source else TXT_CONFIDENCE)

    # --- phones (collect all unique, non-empty values seen) ---
    phones = []
    for phone, src, method in [
        (csv_data.get("phone"), csv_source, "direct"),
        (txt_data.get("phone"), txt_source, "extracted"),
    ]:
        if phone and phone not in phones:
            phones.append(phone)
            provenance.append({"field": "phones", "source": src, "method": method})
            field_confidences.append(CSV_CONFIDENCE if src == csv_source else TXT_CONFIDENCE)

    # --- location (CSV is the only source that provides this today) ---
    location = csv_data.get("location") or {"city": None, "region": None, "country": None}
    if csv_data.get("location"):
        provenance.append({"field": "location", "source": csv_source, "method": "direct"})
        field_confidences.append(CSV_CONFIDENCE)

    # --- headline (TXT-only field in this version) ---
    headline, conf = _pick_field(
        "headline", csv_data.get("headline"), txt_data.get("headline"),
        csv_source, txt_source, provenance,
    )
    if headline:
        field_confidences.append(conf)

    # --- years_experience (TXT-only field in this version) ---
    years_experience, conf = _pick_field(
        "years_experience", csv_data.get("years_experience"), txt_data.get("years_experience"),
        csv_source, txt_source, provenance,
    )
    if years_experience is not None:
        field_confidences.append(conf)

    # --- skills (combined from both sources) ---
    skills = _merge_skills(
        csv_data.get("skills", []), txt_data.get("skills", []),
        csv_source, txt_source, provenance,
    )
    field_confidences.extend([s["confidence"] for s in skills])

    profile = {
        "candidate_id": candidate_id,
        "full_name": full_name,
        "emails": emails,
        "phones": phones,
        "location": location,
        "links": {"linkedin": None, "github": None, "portfolio": None, "other": []},
        "headline": headline,
        "years_experience": years_experience,
        "skills": skills,
        "experience": [],
        "education": [],
        "provenance": provenance,
    }

    return profile, field_confidences


def calculate_confidence(field_confidences):
    """
    Overall confidence = simple average of every individual field's
    confidence score that was actually populated.
    Returns 0.0 if nothing was populated (fully empty profile).
    """
    if not field_confidences:
        return 0.0
    return round(sum(field_confidences) / len(field_confidences), 2)
