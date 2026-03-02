#!/usr/bin/env python3
import random
import re
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
META_PATH = BASE / "out" / "courses_metadata.csv"
OUT_DIR = BASE / "out" / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N = 5
SEED = 42

# columns in your metadata (matches your dataset)
CREDITS_COL = "credits"
SEM_COL = "version__target__semester__code"
LANG_COL = "version__target__language__code"
LEVEL_COL = "version__additional_info__study_levels__codes"
CODE_COL = "code"


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


def make_query(credits: str, sem: str, lang: str, level: str) -> str:
    parts = []
    if credits != "ANY":
        parts.append(f"{credits} EAP")
    if lang != "ANY":
        parts.append(f"{est_language(lang)} keeles")
    if sem != "ANY":
        parts.append(f"{est_semester(sem)}")
    if level != "ANY":
        parts.append(est_level(level))
    middle = " ".join([p for p in parts if p])
    return f"Soovita kursusi: {middle}." if middle else "Soovita üks kursus."


def norm_credits(x) -> str:
    s = str(x).strip()
    if s.lower() in ["nan", "none", ""]:
        return "ANY"
    try:
        return str(int(float(s)))
    except Exception:
        return "ANY"


def main():
    meta = pd.read_csv(META_PATH)

    for col in [CREDITS_COL, SEM_COL, LANG_COL, LEVEL_COL, CODE_COL]:
        if col not in meta.columns:
            raise SystemExit(f"Puudub veerg '{col}' failis {META_PATH}")

    random.seed(SEED)

    # candidates: rows with minimum fields
    candidates = meta.dropna(subset=[CREDITS_COL, SEM_COL, LANG_COL, CODE_COL]).copy()
    if len(candidates) == 0:
        raise SystemExit("Ei leidnud ridu, millel oleks credits+semester+language+code.")

    rows = []
    for i in range(1, N + 1):
        # sample a seed row to define the filter combo
        r = candidates.sample(1, random_state=SEED + i).iloc[0]

        credits = norm_credits(r[CREDITS_COL])
        sem = str(r[SEM_COL]).strip().lower()
        lang = str(r[LANG_COL]).strip().lower()
        level = pick_level(str(r.get(LEVEL_COL, "")))

        sem = sem if sem in ["autumn", "spring"] else "ANY"
        lang = lang if lang in ["et", "en"] else "ANY"
        level = level if level in ["bachelor", "master", "doctoral"] else "ANY"

        # filter meta by these values (ANY means no filter)
        df = meta.copy()
        if credits != "ANY":
            df = df[df[CREDITS_COL].apply(norm_credits) == credits]
        if sem != "ANY":
            df = df[df[SEM_COL].astype(str).str.lower() == sem]
        if lang != "ANY":
            df = df[df[LANG_COL].astype(str).str.lower() == lang]
        if level != "ANY":
            df = df[df[LEVEL_COL].fillna("").astype(str).str.lower().str.contains(level)]

        codes = df[CODE_COL].dropna().astype(str).unique().tolist()
        random.shuffle(codes)
        top_codes = codes[:5]  # expected "top_codes" as 5 valid codes under same filters

        filters = f"credits={credits}, semester={sem}, language={lang}, level={level}"
        query = make_query(credits, sem, lang, level)

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
    print("Järgmine samm: käivita need päringud rakenduses samade filtritega, et tekiks vigade_log.csv read.")
    print("Siis jooksuta: python3 build_testjuhtumid_from_log.py")

if __name__ == "__main__":
    main()
