"""
tests/test_pipeline.py
-----------------------
Simple unit tests using Python's built-in `unittest` module
(no extra dependencies needed). Each test checks ONE small piece
of behavior, matching how the modules themselves are small and
focused.

Run with:
    python -m unittest discover -s tests -v
(run from the project root)
"""

import os
import sys
import unittest

# Make src/ importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import normalizers
import merger
import validator
import config_engine


class TestNormalizers(unittest.TestCase):

    def test_normalize_name_title_cases(self):
        self.assertEqual(normalizers.normalize_name("john doe"), "John Doe")

    def test_normalize_name_handles_empty(self):
        self.assertIsNone(normalizers.normalize_name(""))
        self.assertIsNone(normalizers.normalize_name(None))

    def test_normalize_email_lowercases_and_strips(self):
        self.assertEqual(normalizers.normalize_email("  John.Doe@Gmail.com "), "john.doe@gmail.com")

    def test_normalize_phone_adds_country_code(self):
        self.assertEqual(normalizers.normalize_phone("9876543210"), "+919876543210")

    def test_normalize_phone_strips_spaces(self):
        self.assertEqual(normalizers.normalize_phone("98765 43222"), "+919876543222")

    def test_normalize_phone_handles_missing(self):
        self.assertIsNone(normalizers.normalize_phone(""))
        self.assertIsNone(normalizers.normalize_phone(None))

    def test_normalize_skill_maps_aliases(self):
        self.assertEqual(normalizers.normalize_skill("Py"), "python")
        self.assertEqual(normalizers.normalize_skill("ML"), "machine learning")
        self.assertEqual(normalizers.normalize_skill("AI"), "artificial intelligence")

    def test_normalize_skill_lowercases_unknown_skill(self):
        self.assertEqual(normalizers.normalize_skill("SQL"), "sql")

    def test_normalize_location_full(self):
        loc = normalizers.normalize_location("Chennai, Tamil Nadu, India")
        self.assertEqual(loc, {"city": "Chennai", "region": "Tamil Nadu", "country": "India"})

    def test_normalize_location_missing_returns_nulls(self):
        loc = normalizers.normalize_location("")
        self.assertEqual(loc, {"city": None, "region": None, "country": None})

    def test_extract_years_experience(self):
        text = "Priya Sharma - Data Scientist, has 4 years experience."
        self.assertEqual(normalizers.extract_years_experience(text), 4)

    def test_extract_skills_from_text(self):
        text = "Skills: Python, ML, Django, SQL"
        self.assertEqual(
            normalizers.extract_skills_from_text(text),
            ["python", "machine learning", "django", "sql"],
        )

    def test_is_valid_email(self):
        self.assertTrue(normalizers.is_valid_email("a@b.com"))
        self.assertFalse(normalizers.is_valid_email("not-an-email"))
        self.assertFalse(normalizers.is_valid_email(""))

    def test_is_valid_phone(self):
        self.assertTrue(normalizers.is_valid_phone("+919876543210"))
        self.assertFalse(normalizers.is_valid_phone("9876543210"))  # missing '+'
        self.assertFalse(normalizers.is_valid_phone(""))


class TestMerger(unittest.TestCase):

    def test_csv_wins_when_both_sources_have_a_value(self):
        csv_data = {"name": "John Doe", "email": "csv@example.com"}
        txt_data = {"name": "Johnny D", "email": "txt@example.com"}
        profile, _ = merger.merge_profiles("C999", csv_data, txt_data)
        self.assertEqual(profile["full_name"], "John Doe")

    def test_falls_back_to_txt_when_csv_missing(self):
        csv_data = {}
        txt_data = {"name": "Sneha Iyer"}
        profile, _ = merger.merge_profiles("C999", csv_data, txt_data)
        self.assertEqual(profile["full_name"], "Sneha Iyer")

    def test_skills_combined_from_both_sources(self):
        csv_data = {"skills": ["python"]}
        txt_data = {"skills": ["python", "sql"]}
        profile, _ = merger.merge_profiles("C999", csv_data, txt_data)
        skill_names = sorted(s["name"] for s in profile["skills"])
        self.assertEqual(skill_names, ["python", "sql"])

    def test_skill_in_both_sources_gets_averaged_confidence(self):
        csv_data = {"skills": ["python"]}
        txt_data = {"skills": ["python"]}
        profile, _ = merger.merge_profiles("C999", csv_data, txt_data)
        python_skill = next(s for s in profile["skills"] if s["name"] == "python")
        expected = round((merger.CSV_CONFIDENCE + merger.TXT_CONFIDENCE) / 2, 2)
        self.assertEqual(python_skill["confidence"], expected)

    def test_calculate_confidence_average(self):
        self.assertEqual(merger.calculate_confidence([0.9, 0.7]), 0.8)

    def test_calculate_confidence_empty_profile(self):
        self.assertEqual(merger.calculate_confidence([]), 0.0)


class TestValidator(unittest.TestCase):

    def test_missing_required_field_produces_warning(self):
        profile = {"candidate_id": "C999", "full_name": None, "emails": [], "phones": []}
        _, warnings = validator.validate_profile(profile)
        self.assertTrue(any("full_name" in w for w in warnings))

    def test_invalid_email_is_dropped_not_crashed(self):
        profile = {"candidate_id": "C999", "full_name": "Test", "emails": ["not-an-email"], "phones": []}
        cleaned, warnings = validator.validate_profile(profile)
        self.assertEqual(cleaned["emails"], [])
        self.assertTrue(any("Invalid email" in w for w in warnings))

    def test_valid_profile_has_no_warnings(self):
        profile = {
            "candidate_id": "C999",
            "full_name": "Test User",
            "emails": ["test@example.com"],
            "phones": ["+919876543210"],
        }
        _, warnings = validator.validate_profile(profile)
        self.assertEqual(warnings, [])


class TestConfigEngine(unittest.TestCase):

    def setUp(self):
        self.profile = {
            "candidate_id": "C001",
            "full_name": "John Doe",
            "emails": ["john@example.com"],
            "phones": [],
            "location": {"city": "Chennai", "region": "Tamil Nadu", "country": "India"},
            "skills": [{"name": "python", "confidence": 0.9, "sources": ["recruiter.csv"]}],
            "overall_confidence": 0.85,
            "provenance": [],
        }

    def test_simple_field_selection(self):
        config = {"fields": [{"path": "full_name"}], "on_missing": "null"}
        output = config_engine.apply_config(self.profile, config)
        self.assertEqual(output, {"full_name": "John Doe"})

    def test_field_rename_with_from(self):
        config = {"fields": [{"path": "name", "from": "full_name"}], "on_missing": "null"}
        output = config_engine.apply_config(self.profile, config)
        self.assertEqual(output, {"name": "John Doe"})

    def test_list_index_lookup(self):
        config = {"fields": [{"path": "primary_email", "from": "emails[0]"}], "on_missing": "null"}
        output = config_engine.apply_config(self.profile, config)
        self.assertEqual(output, {"primary_email": "john@example.com"})

    def test_pluck_list_of_dicts(self):
        config = {"fields": [{"path": "skill_names", "from": "skills[].name"}], "on_missing": "null"}
        output = config_engine.apply_config(self.profile, config)
        self.assertEqual(output, {"skill_names": ["python"]})

    def test_on_missing_null_keeps_field_as_none(self):
        config = {"fields": [{"path": "primary_phone", "from": "phones[0]"}], "on_missing": "null"}
        output = config_engine.apply_config(self.profile, config)
        self.assertIsNone(output["primary_phone"])

    def test_on_missing_omit_drops_field(self):
        config = {"fields": [{"path": "primary_phone", "from": "phones[0]"}], "on_missing": "omit"}
        output = config_engine.apply_config(self.profile, config)
        self.assertNotIn("primary_phone", output)

    def test_on_missing_error_raises(self):
        config = {"fields": [{"path": "primary_phone", "from": "phones[0]"}], "on_missing": "error"}
        with self.assertRaises(ValueError):
            config_engine.apply_config(self.profile, config)

    def test_include_confidence_adds_confidence_and_provenance(self):
        config = {"fields": [{"path": "full_name"}], "include_confidence": True, "on_missing": "null"}
        output = config_engine.apply_config(self.profile, config)
        self.assertEqual(output["confidence"], 0.85)
        self.assertIn("provenance", output)


if __name__ == "__main__":
    unittest.main()
