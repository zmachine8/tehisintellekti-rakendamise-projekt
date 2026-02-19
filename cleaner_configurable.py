import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


# -------------------------
# Utils
# -------------------------
def read_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_json_loads(x):
    if x is None:
        return None
    if isinstance(x, (dict, list)):
        return x
    s = str(x).strip()
    if not s or s.lower() == "nan":
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def normalize_text(x) -> str:
    if x is None:
        return ""
    s = str(x)
    if s.lower() == "nan":
        return ""
    s = re.sub(r"\s+", " ", s).strip()
    return s


def pick_first_existing(row, candidates):
    """
    candidates: list of column names
    returns first non-empty string value among existing columns
    """
    for col in candidates:
        if col in row.index:
            val = normalize_text(row[col])
            if val:
                return val
    return ""


# -------------------------
# Prefilters
# -------------------------
def apply_prefilters(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    report = {"dropped": {}, "kept_rows": None}

    # 1) day studies only (fulltime)
    study_type_col = cfg["prefilters"]["study_type_col"]
    day_code = cfg["prefilters"]["day_study_code"]
    if study_type_col in df.columns:
        before = len(df)
        df = df[df[study_type_col].astype(str) == day_code].copy()
        report["dropped"]["not_day_study"] = before - len(df)
    else:
        report["dropped"]["not_day_study"] = 0

    # 2) duration <= N semester
    dur_col = cfg["prefilters"]["duration_col"]
    max_sem = cfg["prefilters"]["max_duration_semesters"]
    if dur_col in df.columns:
        before = len(df)
        dur = pd.to_numeric(df[dur_col], errors="coerce")
        df = df[dur.notna() & (dur <= max_sem)].copy()
        report["dropped"]["duration_gt_max_or_missing"] = before - len(df)
    else:
        report["dropped"]["duration_gt_max_or_missing"] = 0

    # 3) remove canceled/deleted/etc
    state_cols = cfg["prefilters"]["state_cols"]
    bad_state_regex = re.compile(cfg["prefilters"]["bad_state_regex"], re.IGNORECASE)

    def row_is_bad_state(r):
        for c in state_cols:
            if c in r.index:
                s = normalize_text(r[c])
                if s and bad_state_regex.search(s):
                    return True
        return False

    before = len(df)
    mask_bad = df.apply(row_is_bad_state, axis=1)
    df = df[~mask_bad].copy()
    report["dropped"]["bad_state"] = before - len(df)

    report["kept_rows"] = len(df)
    return df, report


# -------------------------
# JSON flatten (auto + manual)
# -------------------------
def looks_like_json_series(s: pd.Series, sample_n: int = 30) -> bool:
    vals = s.dropna().astype(str).head(sample_n).tolist()
    if not vals:
        return False
    hits = 0
    for v in vals:
        t = v.strip()
        if not t:
            continue
        if (t.startswith("{") and t.endswith("}")) or (t.startswith("[") and t.endswith("]")):
            try:
                json.loads(t)
                hits += 1
            except Exception:
                pass
    return hits >= max(2, min(5, len(vals) // 3))


def flatten_json_value(v):
    """
    Return simplified:
      - codes: ';' joined unique codes/ids/uuids
      - names: ';' joined unique names/titles/labels/values/text
      - count: number of elements (list) or 1 for dict/primitive
    """
    obj = safe_json_loads(v)
    if obj is None:
        return "", "", 0

    def grab(item):
        code = ""
        name = ""
        if isinstance(item, dict):
            for k in ["code", "id", "uuid"]:
                if item.get(k) is not None and str(item.get(k)).strip():
                    code = str(item.get(k)).strip()
                    break
            for k in ["name", "title", "label", "value", "text"]:
                if item.get(k) is not None and str(item.get(k)).strip():
                    name = str(item.get(k)).strip()
                    break
        else:
            name = str(item).strip()
        return code, name

    codes, names = [], []

    if isinstance(obj, list):
        for it in obj:
            c, n = grab(it)
            if c:
                codes.append(c)
            if n:
                names.append(n)
        return ";".join(sorted(set(codes))), ";".join(sorted(set(names))), len(obj)

    if isinstance(obj, dict):
        c, n = grab(obj)
        if not n:
            flat_bits = []
            for k, vv in obj.items():
                if isinstance(vv, (str, int, float)) and str(vv).strip():
                    flat_bits.append(f"{k}={vv}")
            if flat_bits:
                n = ";".join(flat_bits)
        return c, n, 1

    n = str(obj).strip()
    return "", n, 1


def flatten_json_columns(df: pd.DataFrame, json_cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in json_cols:
        codes, names, counts = [], [], []
        for v in out[col].tolist():
            c, n, cnt = flatten_json_value(v)
            codes.append(c)
            names.append(n)
            counts.append(cnt)
        out[f"{col}__codes"] = codes
        out[f"{col}__names"] = names
        out[f"{col}__count"] = counts
    return out


# -------------------------
# Metadata build
# -------------------------
def build_metadata(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    base_fields = cfg["metadata"]["base_fields"]
    keep = [c for c in base_fields if c in df.columns]
    meta = df[keep].copy()

    # Derived: study_levels__codes (optional legacy)
    derived = cfg["metadata"].get("derived", {})
    sl = derived.get("study_levels_codes", {})
    if sl.get("enabled", False):
        src = sl.get("source_col")
        out = sl.get("output_col", "study_levels__codes")
        if src in df.columns:
            # prefer already flattened codes if present
            if f"{src}__codes" in df.columns:
                meta[out] = df[f"{src}__codes"]
            else:
                # fallback: parse list[dict(code)] like earlier
                def to_codes(v):
                    obj = safe_json_loads(v)
                    if not obj:
                        return ""
                    if isinstance(obj, list):
                        codes = []
                        for item in obj:
                            if isinstance(item, dict) and item.get("code"):
                                codes.append(str(item["code"]))
                        return ";".join(sorted(set(codes)))
                    if isinstance(obj, dict) and obj.get("code"):
                        return str(obj["code"])
                    return ""
                meta[out] = df[src].apply(to_codes)

    return meta


# -------------------------
# Documents build (RAG text)
# -------------------------
def build_documents(df: pd.DataFrame, meta: pd.DataFrame, cfg: dict, lang: str) -> pd.DataFrame:
    doc_cfg = cfg["documents"]
    keys = [k for k in doc_cfg["keys"] if k in df.columns]
    docs = df[keys].copy()

    # copy metadata subset into docs
    keys_from_meta = [k for k in doc_cfg.get("keys_from_metadata", []) if k in meta.columns]
    for k in keys_from_meta:
        docs[k] = meta[k].values

    include_sections = doc_cfg["include_sections"]
    section_fields = doc_cfg["section_fields"]

    def build_text(row):
        parts = []

        def add_block(label, content):
            content = normalize_text(content)
            if content:
                parts.append(f"{label}: {content}")

        if "title" in include_sections:
            title_et = pick_first_existing(row, section_fields["title"].get("et", []))
            title_en = pick_first_existing(row, section_fields["title"].get("en", []))
            if lang == "et":
                add_block("Pealkiri", title_et)
            elif lang == "en":
                add_block("Title", title_en)
            else:
                if title_et:
                    add_block("Pealkiri", title_et)
                if title_en:
                    add_block("Title", title_en)

        if "description" in include_sections:
            desc_et = pick_first_existing(row, section_fields["description"].get("et", []))
            desc_en = pick_first_existing(row, section_fields["description"].get("en", []))
            if lang == "et":
                add_block("Kirjeldus", desc_et)
            elif lang == "en":
                add_block("Description", desc_en)
            else:
                if desc_et:
                    add_block("Kirjeldus", desc_et)
                if desc_en:
                    add_block("Description", desc_en)

        if "objectives" in include_sections:
            obj_et = pick_first_existing(row, section_fields["objectives"].get("et", []))
            obj_en = pick_first_existing(row, section_fields["objectives"].get("en", []))
            if lang == "et":
                add_block("Eesmärgid", obj_et)
            elif lang == "en":
                add_block("Objectives", obj_en)
            else:
                if obj_et:
                    add_block("Eesmärgid", obj_et)
                if obj_en:
                    add_block("Objectives", obj_en)

        if "learning_outcomes" in include_sections:
            lo_et = pick_first_existing(row, section_fields["learning_outcomes"].get("et", []))
            lo_en = pick_first_existing(row, section_fields["learning_outcomes"].get("en", []))
            if lang == "et":
                add_block("Õpiväljundid", lo_et)
            elif lang == "en":
                add_block("Learning outcomes", lo_en)
            else:
                if lo_et:
                    add_block("Õpiväljundid", lo_et)
                if lo_en:
                    add_block("Learning outcomes", lo_en)

        if "prerequisites" in include_sections:
            pre_et = pick_first_existing(row, section_fields["prerequisites"].get("et", []))
            pre_en = pick_first_existing(row, section_fields["prerequisites"].get("en", []))
            if lang == "et":
                add_block("Eeldusained", pre_et)
            elif lang == "en":
                add_block("Prerequisites", pre_en)
            else:
                if pre_et:
                    add_block("Eeldusained", pre_et)
                if pre_en:
                    add_block("Prerequisites", pre_en)

        return "\n".join(parts).strip()

    docs["document_text"] = df.apply(build_text, axis=1)
    return docs


# -------------------------
# Reports for notebook + json
# -------------------------
def categorical_report(df: pd.DataFrame, cols: list[str], topn: int = 20) -> dict:
    rep = {}
    for c in cols:
        if c not in df.columns:
            continue
        s = df[c].fillna("").astype(str).str.strip()
        vc = s.value_counts(dropna=False)
        rep[c] = {
            "unique": int(vc.shape[0]),
            "top": [{"value": str(k), "count": int(v)} for k, v in vc.head(topn).items()],
        }
    return rep


def missing_report(df: pd.DataFrame, topn: int = 200) -> dict:
    miss = df.isna().sum().sort_values(ascending=False)
    total = len(df)
    out = {}
    for c, m in miss.head(topn).items():
        out[c] = {"missing": int(m), "missing_pct": float(round((m / total) * 100, 3)) if total else 0.0}
    return out


def text_len_stats(s: pd.Series) -> dict:
    lens = s.fillna("").astype(str).str.len()
    desc = lens.describe(percentiles=[0.25, 0.5, 0.75, 0.9, 0.95, 0.99]).to_dict()
    # make json-friendly
    return {k: float(v) for k, v in desc.items()}


# -------------------------
# Main
# -------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Input CSV path")
    ap.add_argument("--config", required=True, help="Config JSON path")
    ap.add_argument("--lang", choices=["et", "en", "both"], default="both")
    ap.add_argument("--outdir", default=".", help="Output directory")
    args = ap.parse_args()

    cfg = read_config(args.config)

    df = pd.read_csv(args.inp)
    input_rows = len(df)

    # prefilters
    df_filt, report = apply_prefilters(df, cfg)
    report["input_rows"] = input_rows
    report["lang"] = args.lang

    # JSON flatten (auto + manual)
    jf = cfg.get("json_flatten", {})
    auto_detect = bool(jf.get("auto_detect", True))
    manual_cols = jf.get("columns", [])

    json_cols = []
    if auto_detect:
        for c in df_filt.columns:
            if df_filt[c].dtype == "object" and looks_like_json_series(df_filt[c]):
                json_cols.append(c)

    for c in manual_cols:
        if c in df_filt.columns and c not in json_cols:
            json_cols.append(c)

    if json_cols:
        df_filt = flatten_json_columns(df_filt, json_cols)
    report["json_flattened_cols"] = json_cols

    # metadata + docs
    meta = build_metadata(df_filt, cfg)
    docs = build_documents(df_filt, meta, cfg, args.lang)

    # extra reports
    mr = cfg.get("missing_report", {})
    report["missing_by_column_top"] = missing_report(df_filt, topn=int(mr.get("topn", 200)))

    cr = cfg.get("categorical_report", {})
    report["categoricals"] = categorical_report(
        df_filt,
        cols=cr.get("columns", []),
        topn=int(cr.get("topn", 20)),
    )

    report["document_text_length_stats"] = text_len_stats(docs["document_text"])

    # write outputs
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    full_path = outdir / cfg["outputs"]["full_cleaned"]
    meta_path = outdir / cfg["outputs"]["metadata"]
    docs_path = outdir / cfg["outputs"]["documents"]
    rep_path = outdir / cfg["outputs"]["report"]

    df_filt.to_csv(full_path, index=False)
    meta.to_csv(meta_path, index=False)
    docs.to_csv(docs_path, index=False)

    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("Wrote:")
    print(" -", full_path)
    print(" -", meta_path)
    print(" -", docs_path)
    print(" -", rep_path)


if __name__ == "__main__":
    main()
