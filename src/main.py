
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import loaders
import normalizers
import merger
import validator
import config_engine


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(PROJECT_ROOT, "input", "recruiter.csv")
TXT_PATH = os.path.join(PROJECT_ROOT, "input", "recruiter_notes.txt")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

CSV_SOURCE_NAME = "recruiter.csv"
TXT_SOURCE_NAME = "recruiter_notes.txt"


def normalize_csv_row(row):
    """
    Step 2 (CSV side): turn one raw CSV row into a clean dict of
    fields ready for merging.
    """
    return {
        "name": normalizers.normalize_name(row.get("name")),
        "email": normalizers.normalize_email(row.get("email")),
        "phone": normalizers.normalize_phone(row.get("phone")),
        "location": normalizers.normalize_location(row.get("location")),
    }


def normalize_txt_block(block_text):
    """
    Step 2 (TXT side): extract + clean fields out of one free-text
    block ready for merging.
    """
    raw_skills = normalizers.extract_skills_from_text(block_text)
    return {
        "name": normalizers.normalize_name(normalizers.extract_name_from_text(block_text)),
        "email": normalizers.normalize_email(normalizers.extract_email_from_text(block_text)),
        "phone": normalizers.normalize_phone(normalizers.extract_phone_from_text(block_text)),
        "headline": normalizers.extract_headline(block_text),
        "years_experience": normalizers.extract_years_experience(block_text),
        "skills": raw_skills,  # already normalized inside extract_skills_from_text
    }


def build_canonical_profiles():
    """
    Steps 1-4: load both sources, normalize them, merge per
    candidate_id, then validate. Returns a list of clean canonical
    profiles plus a list of all validation warnings collected.
    """
    # 1) LOAD
    csv_rows = loaders.load_csv(CSV_PATH)
    txt_blocks = loaders.load_txt(TXT_PATH)

    # Index both sources by candidate_id so we can merge per-candidate.
    csv_by_id = {row["candidate_id"]: row for row in csv_rows if row.get("candidate_id")}
    txt_by_id = {block["candidate_id"]: block["text"] for block in txt_blocks}

    # A candidate can appear in CSV only, TXT only, or both.
    all_ids = sorted(set(csv_by_id.keys()) | set(txt_by_id.keys()))

    all_warnings = []
    profiles = []

    for candidate_id in all_ids:
        # 2) NORMALIZE
        csv_data = normalize_csv_row(csv_by_id[candidate_id]) if candidate_id in csv_by_id else {}
        txt_data = normalize_txt_block(txt_by_id[candidate_id]) if candidate_id in txt_by_id else {}

        # 3) MERGE + CONFIDENCE
        profile, field_confidences = merger.merge_profiles(
            candidate_id, csv_data, txt_data, CSV_SOURCE_NAME, TXT_SOURCE_NAME
        )
        profile["overall_confidence"] = merger.calculate_confidence(field_confidences)

        # 4) VALIDATE
        profile, warnings = validator.validate_profile(profile)
        all_warnings.extend(warnings)

        profiles.append(profile)

    return profiles, all_warnings


def run_pipeline():
    """
    Step 5-6: build canonical profiles, then project them through
    config.json, then save BOTH the canonical output and the
    custom-config output to the output/ folder.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    profiles, warnings = build_canonical_profiles()

    # Save the canonical (default schema) output
    canonical_path = os.path.join(OUTPUT_DIR, "canonical_profiles.json")
    with open(canonical_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2)
    print(f"Saved canonical profiles -> {canonical_path}")

    # Load config.json and project each profile through it
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"[main.py] WARNING: config.json not found at {CONFIG_PATH}, skipping custom output.")
        config = None

    if config:
        custom_output = [config_engine.apply_config(p, config) for p in profiles]
        custom_path = os.path.join(OUTPUT_DIR, "custom_output.json")
        with open(custom_path, "w", encoding="utf-8") as f:
            json.dump(custom_output, f, indent=2)
        print(f"Saved custom-config output -> {custom_path}")

    # Print warnings so they're visible in the demo video / terminal
    if warnings:
        print(f"\n{len(warnings)} validation warning(s):")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("\nNo validation warnings.")

    print(f"\nDone. Processed {len(profiles)} candidate(s).")


if __name__ == "__main__":
    run_pipeline()
