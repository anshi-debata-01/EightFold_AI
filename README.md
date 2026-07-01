##DEMO VIDEO LINK
[https://drive.google.com/file/d/1UQCJxM89Q4np63XWvJ7ab_lh3AS0UXwX/view?usp=sharing]

# Multi-Source Candidate Data Transformer

A simple Python pipeline that takes candidate data from two sources:

* **Recruiter CSV** (structured data)
* **Recruiter Notes TXT** (unstructured data)

It cleans, merges, validates, and converts them into one final candidate profile.

Built for the Eightfold AI Internship Assignment.

---

## Folder Structure

```text
eightfold-assignment/
│── input/
│   ├── recruiter.csv
│   ├── recruiter_notes.txt
│
│── output/
│   ├── canonical_profiles.json
│
│── src/
│   ├── loaders.py
│   ├── normalizers.py
│   ├── merger.py
│   ├── validator.py
│   ├── main.py
```

---

## Pipeline Flow

```text
LOAD → NORMALIZE → MERGE → VALIDATE → SAVE
```

### 1. Load (`loaders.py`)

Reads:

* `recruiter.csv`
* `recruiter_notes.txt`

Converts raw files into Python dictionaries/lists.

---

### 2. Normalize (`normalizers.py`)

Cleans the data:

* Convert email to lowercase
* Format phone numbers
* Convert names to Title Case
* Normalize skills

Example:

* `ANSHU@MAIL.COM` → `anshu@mail.com`
* `9876543210` → `+919876543210`

---

### 3. Merge (`merger.py`)

Combines CSV and TXT data using `candidate_id`.

Rules:

* If same field exists in both → CSV gets priority
* Skills from both sources are combined

Example:

`C001 (CSV) + C001 (TXT) → One final profile`

---

### 4. Validate (`validator.py`)

Checks:

* Valid email format
* Valid phone format
* Missing important fields

If invalid:

* Remove bad data
* Print warning

---

### 5. Save (`main.py`)

Stores final output into:

```text
output/canonical_profiles.json
```

---

## How to Run

Go to project folder:

```bash
cd eightfold-assignment
```

Run the pipeline:

```bash
python src/main.py
```

---

## Output

After running:

```text
output/canonical_profiles.json
```

This file contains the final merged candidate profiles.

---

## Example Flow

```text
CSV + TXT
   ↓
Load Data
   ↓
Normalize Data
   ↓
Merge by candidate_id
   ↓
Validate Data
   ↓
Save Final JSON
```

---

## Tech Used

* Python
* CSV module
* Regex
* JSON module

---

## Merge Strategy

* Structured CSV data is considered more reliable
* TXT notes provide extra missing details
* Final merge happens using `candidate_id`

Priority:

```text
CSV > TXT
```

---

## Error Handling

Handled cases:

* Missing files
* Invalid email
* Invalid phone
* Candidate present in only one source
* Empty fields

The pipeline never crashes and continues processing.


##DEMO VIDEO LINK
[https://drive.google.com/file/d/1UQCJxM89Q4np63XWvJ7ab_lh3AS0UXwX/view?usp=sharing]
