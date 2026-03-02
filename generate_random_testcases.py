#!/usr/bin/env python3
import random
import re
from pathlib import Path

import pandas as pd

# -------------------------
# CONFIG (change here)
# -------------------------
NUM_TESTCASES = 5
SEED = 123
# -------------------------

BASE = Path(__file__).parent
META_PATH = BASE / "out" / "courses_metadata.csv"
OUT_DIR = BASE / "out" / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# required columns in your metadata
CREDITS_COL = "credits"
SEM_COL = "version__target__semester__code"
LANG_COL = "version__target__language__code"
LEVEL_COL = "version__additional_info__study_levels__codes"
CODE_COL = "code"

# optional columns (used only if present)
TITLE_COL_CANDIDATES = [
    "version__title__et",
    "version__title__en",
    "title",
    "name",
    "course_name",
    "course_title",
]
FACULTY_COL_CANDIDATES = [
    "faculty__code",
    "faculty__name",
    "version__target__faculty__code",
    "version__target__faculty__name",
]
INSTITUTE_COL_CANDIDATES = [
    "institute__code",
    "institute__name",
    "version__target__institute__code",
    "version__target__institute__name",
]

ET_STOPWORDS = {
    "ja", "või", "ning", "kui", "kas", "et", "see", "selle", "seda", "need", "neid",
    "kursus", "kursuse", "õppeaine", "õppeaines", "sissejuhatus", "alused", "i", "ii",
    "the", "and", "or", "to", "of", "in", "for", "an", "a",
}

def first_existing_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None

def pick_level(level_codes: str) -> str:
    if not isinstance(level_codes, str) or not level_codes.strip():
        return "ANY"
    parts = re.split(r"[;,]", level_codes)
    parts = [p.strip().lower() for p in parts if p.strip()]
    for cand in ["bachelor", "master", "doctoral"]:
        if cand in parts:
            return cand
    return parts[0] if parts else "ANY"

def est_language(lang: str) -> str:
    return "inglise" if lang == "en" else "eesti" if lang == "et" else "võõrkeele"

def est_semester(sem: str) -> str:
    return "sügissemester" if sem == "autumn" else "kevadsemester" if sem == "spring" else "semester"

def est_level(level: str) -> str:
    return {"bachelor": "bakalaureusele", "master": "magistrile", "doctoral": "doktoriõppele"}.get(level, "")

def norm_credits(x) -> str:
    s = str(x).strip()
    if s.lower() in ["nan", "none", ""]:
        return "ANY"
    try:
        return str(int(float(s)))
    except Exception:
        return "ANY"

def extract_keywords(title: str, k: int = 2) -> list[str]:
    if not isinstance(title, str):
        return []
    t = title.strip()
    if not t:
        return []
    t = re.sub(r"[^0-9A-Za-zÄÖÜÕäöüõŠšŽž\-]+", " ", t)
    toks = [x.strip("-").lower() for x in t.split() if x.strip("-")]
    toks = [x for x in toks if x not in ET_STOPWORDS and len(x) >= 4]
    seen = set()
    uniq = []
    for x in toks:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    if not uniq:
        return []
    random.shuffle(uniq)
    return uniq[:k]

PROMPT_TEMPLATES = [
    "Olen valimas aineid. Soovita {n} kursust{topic_part}{constraint_part} "
    "Iga soovituse juurde lisa: kood, 1–2 lauset miks see sobib, ja mida eeldatakse eelteadmistena.",
    "Palun koosta lühike shortlist: {n} sobivaimat kursust{topic_part}{constraint_part} "
    "Väldi liiga teoreetilisi aineid; eelista praktilisi.",
    "Soovita {n} kursust{topic_part}{constraint_part} Kui täpselt ei leia, paku lähimad alternatiivid ja ütle miks.",
    "Mul on vaja semestriplaani. Leia {n} kursust{topic_part}{constraint_part} nii, et töökoormus oleks mõistlik. "
    "Lisa iga kursuse juurde ka võimalik risk (nt raske matemaatika, palju rühmatööd).",
    "Soovita {n} kursust{topic_part}{constraint_part} Palun ära paku kursusi, mis on täiesti algtaseme sissejuhatused, "
    "kui on võimalik midagi sisukamat samas teemas.",
]

def build_constraint_text(credits: str, sem: str, lang: str, level: str, faculty: str | None, institute: str | None) -> str:
    parts = []
    if credits != "ANY":
        parts.append(f"{credits} EAP")
    if lang != "ANY":
        parts.append(f"{est_language(lang)} keeles")
    if sem != "ANY":
        parts.append(f"{est_semester(sem)}")
    if level != "ANY":
        lv = est_level(level)
        if lv:
            parts.append(lv)
    if faculty:
        parts.append(f"({faculty})")
    if institute:
        parts.append(f"({institute})")

    if not parts:
        return "."

    joiners = [
        " tingimustega: ",
        " filtritega: ",
        " järgmiste piirangutega: ",
        " (soovid: ",
    ]
    j = random.choice(joiners)
    tail = ", ".join(parts)
    if j.strip().endswith("("):
        return f"{j}{tail})."
    return f"{j}{tail}."

def make_query(credits: str, sem: str, lang: str, level: str, title: str | None, faculty: str | None, institute: str | None) -> str:
    n = random.choice([2, 3, 4, 5])
    kws = extract_keywords(title or "", k=random.choice([1, 2]))
    topic_part = ""
    if kws:
        topic_part = random.choice([
            f" teemal '{' / '.join(kws)}'",
            f" mis seostuvad teemadega {', '.join(kws)}",
            f" valdkonnas {', '.join(kws)}",
        ])
    constraint_part = build_constraint_text(credits, sem, lang, level, faculty, institute)
    template = random.choice(PROMPT_TEMPLATES)
    return template.format(n=n, topic_part=topic_part, constraint_part=constraint_part)

def main():
    random.seed(SEED)

    meta = pd.read_csv(META_PATH)

    for col in [CREDITS_COL, SEM_COL, LANG_COL, LEVEL_COL, CODE_COL]:
        if col not in meta.columns:
            raise SystemExit(f"Puudub veerg '{col}' failis {META_PATH}")

    title_col = first_existing_col(meta, TITLE_COL_CANDIDATES)
    faculty_col = first_existing_col(meta, FACULTY_COL_CANDIDATES)
    institute_col = first_existing_col(meta, INSTITUTE_COL_CANDIDATES)

    candidates = meta.dropna(subset=[CREDITS_COL, SEM_COL, LANG_COL, CODE_COL]).copy()
    if len(candidates) == 0:
        raise SystemExit("Ei leidnud ridu, millel oleks credits+semester+language+code.")

    rows = []
    for i in range(1, NUM_TESTCASES + 1):
        # deterministic-ish sampling: SEED + i
        r = candidates.sample(1, random_state=SEED + i).iloc[0]

        credits = norm_credits(r[CREDITS_COL])
        sem = str(r[SEM_COL]).strip().lower()
        lang = str(r[LANG_COL]).strip().lower()
        level = pick_level(str(r.get(LEVEL_COL, "")))

        sem = sem if sem in ["autumn", "spring"] else "ANY"
        lang = lang if lang in ["et", "en"] else "ANY"
        level = level if level in ["bachelor", "master", "doctoral"] else "ANY"

        title = str(r[title_col]) if title_col and pd.notna(r.get(title_col)) else None
        faculty = str(r[faculty_col]).strip() if faculty_col and pd.notna(r.get(faculty_col)) else None
        institute = str(r[institute_col]).strip() if institute_col and pd.notna(r.get(institute_col)) else None

        df = meta.copy()
        if credits != "ANY":
            df = df[df[CREDITS_COL].apply(norm_credits) == credits]
        if sem != "ANY":
            df = df[df[SEM_COL].astype(str).str.lower() == sem]
        if lang != "ANY":
            df = df[df[LANG_COL].astype(str).str.lower() == lang]
        if level != "ANY":
            df = df[df[LEVEL_COL].fillna("").astype(str).str.lower().str.contains(level)]

        # optionally apply faculty/institute filters if they exist and won’t shrink too much
        if faculty_col and faculty and random.random() < 0.5:
            df2 = df[df[faculty_col].astype(str).str.strip() == faculty]
            if len(df2) >= 5:
                df = df2
        if institute_col and institute and random.random() < 0.3:
            df2 = df[df[institute_col].astype(str).str.strip() == institute]
            if len(df2) >= 5:
                df = df2

        codes = df[CODE_COL].dropna().astype(str).unique().tolist()
        random.shuffle(codes)
        top_codes = codes[:5]

        filters = f"credits={credits}, semester={sem}, language={lang}, level={level}"
        if faculty_col and faculty:
            filters += f", faculty={faculty}"
        if institute_col and institute:
            filters += f", institute={institute}"

        query = make_query(credits, sem, lang, level, title, faculty, institute)

        rows.append({
            "ID": f"R{i:02d}",
            "Päring": query,
            "Filtrid": filters,
            "Expected unique_ID (top_codes)": ", ".join(top_codes),
            "Tulemus (PASS/FAIL)": "",
            "Märkus": "Expected on valitud metadata-st sama filtrikombinatsiooni alt (mitte LLM output).",
        })

    out_csv = OUT_DIR / "random_testcases.csv"
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    print(f"Valmis: {out_csv}")

if __name__ == "__main__":
    main()