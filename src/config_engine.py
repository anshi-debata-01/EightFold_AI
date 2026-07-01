"""
config_engine.py
-----------------
Job: Take the fixed, internal canonical profile and "project" it
into whatever shape config.json asks for - WITHOUT changing any
code. This keeps a clean separation:

    canonical profile (internal, always the same shape)
              |
              v
        config_engine.py   <-- only this layer changes per config
              |
              v
    custom output (shape defined by config.json)

config.json format (see sample config.json for a full example):
{
  "fields": [
    {"path": "full_name"},
    {"path": "primary_email", "from": "emails[0]"},
    {"path": "skills", "from": "skills[].name"}
  ],
  "include_confidence": true,
  "on_missing": "null"   <- "null" | "omit" | "error"
}

- "path": the field name to use in the OUTPUT.
- "from": (optional) where to read the value from in the canonical
  profile, if different from "path". Supports:
    - simple dotted paths: "location.city"
    - list indexing: "emails[0]"
    - list-of-dicts field pluck: "skills[].name" (returns a list)
  If "from" is omitted, "path" is used as the lookup key too.
- "include_confidence": if true, adds "confidence" next to each
  field's value (taken from overall_confidence as a simple,
  explainable approximation) and keeps the provenance block.
- "on_missing": what to do if a field's value can't be found:
    "null"  -> include the field with a null value (default)
    "omit"  -> leave the field out of the output entirely
    "error" -> raise a clear error (caller decides how to handle it)
"""


def _get_value(profile, from_path):
    """
    Resolve a "from" path against the canonical profile dict.
    Supports: dotted paths, "field[index]", and "field[].subfield".
    Returns the resolved value, or None if it can't be found.
    """
    # Case: "skills[].name" -> pluck "name" from every item in skills
    if "[]." in from_path:
        list_field, sub_field = from_path.split("[].", 1)
        items = profile.get(list_field, [])
        if not isinstance(items, list):
            return None
        return [item.get(sub_field) for item in items if isinstance(item, dict)]

    # Case: "emails[0]" -> index into a list field
    if "[" in from_path and from_path.endswith("]"):
        field_name, index_part = from_path[:-1].split("[")
        items = profile.get(field_name)
        try:
            index = int(index_part)
            return items[index] if items and index < len(items) else None
        except (ValueError, TypeError):
            return None

    # Case: "location.city" -> dotted lookup through nested dicts
    if "." in from_path:
        current = profile
        for part in from_path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    # Simple case: top-level field name
    return profile.get(from_path)


def apply_config(profile, config):
    """
    Project ONE canonical profile into the custom shape described
    by `config` (the parsed contents of config.json).

    Returns the projected (custom) output dict for this candidate.
    """
    on_missing = config.get("on_missing", "null")
    include_confidence = config.get("include_confidence", False)

    output = {}

    for field_spec in config.get("fields", []):
        out_path = field_spec["path"]
        from_path = field_spec.get("from", out_path)

        value = _get_value(profile, from_path)

        if value in (None, [], ""):
            if on_missing == "omit":
                continue
            elif on_missing == "error":
                raise ValueError(f"Required field '{out_path}' is missing for candidate {profile.get('candidate_id')}")
            else:  # "null" (default) - keep the field, value is None
                value = None

        output[out_path] = value

    if include_confidence:
        output["confidence"] = profile.get("overall_confidence")
        output["provenance"] = profile.get("provenance")

    return output
