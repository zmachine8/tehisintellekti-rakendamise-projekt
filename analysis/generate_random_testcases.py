#!/usr/bin/env python3
import json
import os
import random
import re
import time
from pathlib import Path

import pandas as pd

# -------------------------
# CONFIG (change here)
# -------------------------
NUM_TESTCASES = 5

# Reproducible only if you set env TESTCASE_SEED=123
# Otherwise a fresh seed is used every run.
SEED_ENV = "TESTCASE_SEED"

# Ensure we don't generate duplicates inside one run
MAX_ATTEMPTS_PER_CASE = 200
# -------------------------

BASE = Path(__file__).resolve().parent.parent
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

def extract_keywords(title: str, k: int = 3) -> list[str]:
    """
    Make keywords much less likely to be empty.
    - allow length >= 3 instead of >= 4
    - allow digits/short tech tokens (e.g., "sql", "api")
    """
    if not isinstance(title, str):
        return []
    t = title.strip()
    if not t:
        return []
    t = re.sub(r"[^0-9A-Za-zÄÖÜÕäöüõŠšŽž\-]+", " ", t)
    toks = [x.strip("-").lower() for x in t.split() if x.strip("-")]
    toks = [x for x in toks if x not in ET_STOPWORDS and len(x) >= 3]
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
    "Eelista praktilisi aineid ning maini, milline oskus igast kursusest kaasa tuleb.",

    "Soovita {n} kursust{topic_part}{constraint_part} Kui täpselt ei leia, paku lähimad alternatiivid ja ütle miks.",

    "Mul on vaja semestriplaani. Leia {n} kursust{topic_part}{constraint_part} nii, et töökoormus oleks mõistlik. "
    "Lisa iga kursuse juurde ka võimalik risk (nt raske matemaatika, palju rühmatööd).",

    "Soovita {n} kursust{topic_part}{constraint_part} Palun ära paku täiesti algtaseme sissejuhatusi, "
    "kui on olemas sisukamad samateemalised kursused.",

    "Otsin {n} kursust{topic_part}{constraint_part} Tee valik nii, et kursused oleksid omavahel võimalikult erinevad.",
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

    # Keep faculty/institute sometimes, but also avoid always repeating them
    if faculty and random.random() < 0.6:
        parts.append(f"({faculty})")
    if institute and random.random() < 0.4:
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

    kws = extract_keywords(title or "", k=random.choice([2, 3]))
    topic_part = ""
    if kws:
        topic_part = random.choice([
            f" teemal '{' / '.join(kws)}'",
            f" mis seostuvad teemadega {', '.join(kws)}",
            f" valdkonnas {', '.join(kws)}",
        ])
    else:
        # fallback topic to avoid empty topic_part repeating too often
        topic_part = random.choice([
            " informaatika/andmeteaduse suunal",
            " ettevõtluse ja digilahenduste suunal",
            " praktilise IT suunal",
            " analüüsi ja modelleerimise suunal",
        ])

    constraint_part = build_constraint_text(credits, sem, lang, level, faculty, institute)
    template = random.choice(PROMPT_TEMPLATES)
    return template.format(n=n, topic_part=topic_part, constraint_part=constraint_part)

def main():
    seed_str = os.environ.get(SEED_ENV)

    # Always keep seed compatible with pandas/numpy random_state: 0 .. 2**32-1
    if seed_str is not None and seed_str.strip():
        run_seed = int(seed_str) % (2**32 - 1)
    else:
        run_seed = int(time.time_ns() % (2**32 - 1))

    random.seed(run_seed)

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

    # sample without replacement to avoid repeated constraints coming from same/similar rows
    take = min(NUM_TESTCASES * 3, len(candidates))
    sampled_pool = candidates.sample(n=take, replace=False, random_state=run_seed).reset_index(drop=True)

    seen = set()
    rows = []
    i = 1
    pool_idx = 0

    while i <= NUM_TESTCASES:
        # if pool exhausted, reshuffle a new pool
        if pool_idx >= len(sampled_pool):
            sampled_pool = candidates.sample(n=take, replace=False, random_state=random.randint(0, 2**32 - 1)).reset_index(drop=True)
            pool_idx = 0

        r = sampled_pool.iloc[pool_idx]
        pool_idx += 1

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

        # Build expected from metadata under same filters (as before)
        df = meta
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

        # Make query; retry if duplicates happen
        ok = False
        for _ in range(MAX_ATTEMPTS_PER_CASE):
            query = make_query(credits, sem, lang, level, title, faculty, institute)
            key = (query.strip(), filters.strip())
            if key not in seen:
                seen.add(key)
                ok = True
                break

        if not ok:
            # last resort: add a nonce to force uniqueness
            query = query + f" (test-{i}-{random.randint(1000,9999)})"
            seen.add((query.strip(), filters.strip()))

        rows.append({
            "ID": f"R{i:02d}",
            "Päring": query,
            "Filtrid": filters,
            "Expected unique_ID (top_codes)": ", ".join(top_codes),
            "Tulemus (PASS/FAIL)": "",
            "Märkus": "Expected on valitud metadata-st sama filtrikombinatsiooni alt (mitte LLM output).",
        })
        i += 1

    out_csv = OUT_DIR / "random_testcases.csv"
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    print(f"Valmis: {out_csv}")
    print(f"Seed: {run_seed} (set {SEED_ENV} to reproduce)")

if __name__ == "__main__":
    main()