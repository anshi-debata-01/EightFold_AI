"""
validator.py
------------
Job: Check that a canonical profile is well-formed BEFORE it gets
saved or projected through the config engine.

Rule from the assignment: validation must never crash the pipeline.
If something is missing or invalid, we just record a warning and
set that field to null - we never invent data and we never raise
an exception that kills the run.
"""

from normalizers import is_valid_email, is_valid_phone

REQUIRED_FIELDS = ["candidate_id", "full_name"]


def validate_profile(profile):
    """
    Validate a single canonical profile.

    Returns (cleaned_profile, list_of_warnings)
    - cleaned_profile: the same profile, but with invalid emails/
      phones removed (never invented, never silently kept if broken)
    - list_of_warnings: human-readable strings describing what was
      wrong, useful for debugging / the README / the demo video
    """
    warnings = []

    # 1) Required fields must exist and be non-empty
    for field in REQUIRED_FIELDS:
        if not profile.get(field):
            warnings.append(f"Missing required field: '{field}' (candidate_id={profile.get('candidate_id')})")

    # 2) Email format check - drop invalid emails instead of crashing
    valid_emails = []
    for email in profile.get("emails", []):
        if is_valid_email(email):
            valid_emails.append(email)
        else:
            warnings.append(f"Invalid email dropped: '{email}' (candidate_id={profile.get('candidate_id')})")
    profile["emails"] = valid_emails

    # 3) Phone format check - drop invalid phones instead of crashing
    valid_phones = []
    for phone in profile.get("phones", []):
        if is_valid_phone(phone):
            valid_phones.append(phone)
        else:
            warnings.append(f"Invalid phone dropped: '{phone}' (candidate_id={profile.get('candidate_id')})")
    profile["phones"] = valid_phones

    return profile, warnings
