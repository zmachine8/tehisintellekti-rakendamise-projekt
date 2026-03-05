#!/usr/bin/env python3
import gc
import json
import os
import random
import re
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from collections import Counter


# -------------------------
# CONFIG
# -------------------------
NUM_TESTCASES = 25
TOP_K = 5

SEED_ENV = "TESTCASE_SEED"        # optional: reproducibility
FORCE_REBUILD_ENV = "REBUILD_EMB" # set to 1 to rebuild embeddings cache

MAX_ATTEMPTS_PER_CASE = 200

# Project paths (matches your repo layout)
BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "out"
ANALYSIS_DIR = OUT_DIR / "analysis"
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

META_PATH = OUT_DIR / "courses_metadata.csv"
DOCS_PATH = OUT_DIR / "courses_documents.csv"

# Use same cache directory name as run_chatbot.py
EMB_DIR = OUT_DIR / "emb_cache"
EMB_DIR.mkdir(parents=True, exist_ok=True)

# Columns (required-ish)
CODE_COL = "code"
CREDITS_COL = "credits"
SEM_COL = "version__target__semester__code"
LANG_COL = "version__target__language__code"
LEVEL_COL = "version__additional_info__study_levels__codes"

# Title column candidates (for prompt generation)
TITLE_COL_CANDIDATES = [
    "version__title__et",
    "version__title__en",
    "title",
    "name",
    "course_name",
    "course_title",
]

# -------------------------
# Helpers: schema detection
# -------------------------
def first_existing_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """Return first candidate column that exists in dataframe, or None."""
    for c in candidates:
        if c in df.columns:
            return c
    return None

COURSE_ID_CANDIDATES = ["course_uuid", "course_id", "id", "uuid", "course"]
TEXT_COL_CANDIDATES = ["text", "document_text", "document", "content", "chunk", "chunk_text", "page_content", "body"]
CODE_COL_CANDIDATES = ["code", "course_code"]

def find_docs_key(docs_df: pd.DataFrame) -> str:
    """Find course ID column in documents dataframe."""
    col = first_existing_col(docs_df, COURSE_ID_CANDIDATES)
    if not col:
        raise SystemExit(f"Could not find docs key column in courses_documents.csv. Expected one of: {COURSE_ID_CANDIDATES}")
    return col

def find_text_col(docs_df: pd.DataFrame) -> str:
    """Find text/document column in documents dataframe."""
    col = first_existing_col(docs_df, TEXT_COL_CANDIDATES)
    if col:
        return col
    # Fallback: first object column that looks text
    obj_cols = [c for c in docs_df.columns if docs_df[c].dtype == object]
    if not obj_cols:
        raise SystemExit(f"Could not find a text column in courses_documents.csv. Expected one of: {TEXT_COL_CANDIDATES}")
    return obj_cols[0]

def norm_credits(x) -> str:
    s = str(x).strip()
    if s.lower() in ["nan", "none", "null", ""]:
        return "ANY"
    try:
        return str(int(float(s)))
    except Exception:
        return "ANY"

def split_levels(level_codes: str) -> set[str]:
    if not isinstance(level_codes, str):
        return set()
    parts = re.split(r"[;,]", level_codes)
    return {p.strip().lower() for p in parts if p.strip()}

# -------------------------
# Filters (same meaning as app)
# -------------------------
def apply_filters(meta_df: pd.DataFrame, credits: str, sem: str, lang: str, level: str) -> pd.DataFrame:
    df = meta_df

    if credits != "ANY" and CREDITS_COL in df.columns:
        df = df[df[CREDITS_COL].apply(norm_credits) == credits]

    if sem != "ANY" and SEM_COL in df.columns:
        df = df[df[SEM_COL].astype(str).str.lower().str.strip() == sem]

    if lang != "ANY" and LANG_COL in df.columns:
        df = df[df[LANG_COL].astype(str).str.lower().str.strip() == lang]

    if level != "ANY" and LEVEL_COL in df.columns:
        lv = level.lower().strip()
        df = df[df[LEVEL_COL].fillna("").astype(str).str.lower().str.contains(lv)]

    return df

# -------------------------
# Prompt generation from target course data
# -------------------------
STOP = set("""
ja või ning kui kas et see selle seda need neid kursus kursuse õppeaine õppeaines sissejuhatus alused i ii
the and or to of in for an a on with without from by at as is are be been being
""".split())

def keywords(text: str, k: int = 6) -> list[str]:
    """Extract keywords from text, prioritizing unique content words."""
    if not isinstance(text, str):
        return []
    text = re.sub(r"[^0-9A-Za-zÄÖÜÕäöüõŠšŽž\- ]+", " ", text)
    toks = [t.strip("-").lower() for t in text.split() if t.strip("-")]
    toks = [t for t in toks if t not in STOP and len(t) >= 3]
    # keep order but unique
    out, seen = [], set()
    for t in toks:
        if t not in seen:
            out.append(t)
            seen.add(t)
    random.shuffle(out)
    return out[:k]

PROMPT_TEMPLATES = [
    "Soovita kursust, mis aitab mul õppida {k1} ja {k2}. Tahaks, et oleks praktiline ja kataks ka {k3}.",
    "Otsin ainet teemadel {k1}, {k2} ja {k3}. Mis kursus seda kõige paremini katab?",
    "Mul on huvi {k1} vastu, aga tahan siduda selle {k2} ja {k3} rakendustega. Soovita sobiv kursus.",
    "Milline kursus õpetab {k1} ning sisaldab ka {k2} ja {k3}? Lisa lühike põhjendus.",
]

def make_prompt(title: str, doc_text: str) -> str:
    ks = keywords((title or "") + " " + (doc_text or ""), k=10)
    if len(ks) < 3:
        ks += ["andmed", "süsteemid", "analüüs", "tarkvara"]
    k1, k2, k3 = ks[0], ks[1], ks[2]
    return random.choice(PROMPT_TEMPLATES).format(k1=k1, k2=k2, k3=k3)

# -------------------------
# Embeddings cache (float16 memmap like run_chatbot.py)
# -------------------------
def docs_signature(docs_df: pd.DataFrame, text_col: str, docs_key: str) -> dict:
    p = DOCS_PATH
    st = p.stat()
    return {
        "path": str(p),
        "mtime_ns": int(st.st_mtime_ns),
        "size": int(st.st_size),
        "model": "intfloat/multilingual-e5-small",
        "text_col": str(text_col),
        "key_col": str(docs_key),
    }

def load_or_build_embeddings(docs_df: pd.DataFrame, text_col: str, docs_key: str):
    # Local import so running without sentence_transformers gives clear error only when needed
    from sentence_transformers import SentenceTransformer

    meta_path = EMB_DIR / "emb_meta.json"
    emb_path = EMB_DIR / "doc_embs_f16.dat"
    ids_path = EMB_DIR / "doc_ids.json"

    sig = docs_signature(docs_df, text_col, docs_key)

    force = os.environ.get(FORCE_REBUILD_ENV, "").strip() == "1"

    def have_valid_cache() -> bool:
        if force:
            return False
        if not (meta_path.exists() and emb_path.exists() and ids_path.exists()):
            return False
        try:
            old = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        return old == sig

    embedder = SentenceTransformer("intfloat/multilingual-e5-small")

    if not have_valid_cache():
        texts = docs_df[text_col].fillna("").astype(str).tolist()
        ids = docs_df[docs_key].astype(str).tolist()

        # discover dim
        batch0 = texts[:64] if len(texts) >= 64 else texts
        e0 = embedder.encode(batch0, normalize_embeddings=True)
        dim = int(e0.shape[1])

        if emb_path.exists():
            try:
                emb_path.unlink()
            except Exception:
                pass

        mm = np.memmap(emb_path, mode="w+", dtype=np.float16, shape=(len(texts), dim))
        mm[: len(e0)] = e0.astype(np.float16)

        bs = 128
        for start in range(len(e0), len(texts), bs):
            end = min(start + bs, len(texts))
            emb = embedder.encode(texts[start:end], normalize_embeddings=True)
            mm[start:end] = emb.astype(np.float16)
            gc.collect()

        mm.flush()
        ids_path.write_text(json.dumps(ids, ensure_ascii=False), encoding="utf-8")
        meta_path.write_text(json.dumps(sig, ensure_ascii=False), encoding="utf-8")

    ids = json.loads(ids_path.read_text(encoding="utf-8"))
    n = len(ids)
    emb_bytes = (EMB_DIR / "doc_embs_f16.dat").stat().st_size
    dim = int(emb_bytes // (2 * n)) if n > 0 else 0
    mm = np.memmap(emb_path, mode="r", dtype=np.float16, shape=(n, dim))
    id_to_idx = {cid: i for i, cid in enumerate(ids)}

    return embedder, mm, ids, id_to_idx

# -------------------------
# Semantic oracle: expected top-k from PROMPT + FILTERS
# -------------------------
def expected_top_codes(prompt: str,
                       meta_df: pd.DataFrame,
                       docs_df: pd.DataFrame,
                       docs_key: str,
                       embedder,
                       doc_mm: np.memmap,
                       id_to_idx: dict[str, int],
                       credits: str, sem: str, lang: str, level: str,
                       top_k: int) -> list[str]:

    # 1) filter metadata to allowed course ids
    filtered_meta = apply_filters(meta_df, credits, sem, lang, level)
    meta_id_col = first_existing_col(filtered_meta, COURSE_ID_CANDIDATES)
    if not meta_id_col:
        raise SystemExit(f"Could not find course id column in metadata. Expected one of: {COURSE_ID_CANDIDATES}")
    allowed_ids = set(filtered_meta[meta_id_col].astype(str))

    # 2) docs indices that are both in allowed set and have embeddings
    doc_ids = []
    doc_idxs = []
    for cid in docs_df[docs_key].astype(str).tolist():
        if cid in allowed_ids:
            idx = id_to_idx.get(cid)
            if idx is not None:
                doc_ids.append(cid)
                doc_idxs.append(idx)

    if not doc_idxs:
        return []

    # 3) embed query and score
    q = embedder.encode([prompt], normalize_embeddings=True)[0].astype(np.float32)
    embs = doc_mm[np.array(doc_idxs, dtype=np.int64)].astype(np.float32)
    scores = embs @ q

    # 4) stable ranking with deterministic tie-break: (-score, doc_id)
    order = np.lexsort((np.array(doc_ids, dtype=object), -scores))
    ranked_ids = [doc_ids[i] for i in order]

    # 5) map to course codes and dedup by code
    # build id -> code map from metadata
    id_col = first_existing_col(meta_df, COURSE_ID_CANDIDATES)
    if not id_col:
        return []

    id_to_code = dict(zip(meta_df[id_col].astype(str), meta_df[CODE_COL].astype(str)))

    out = []
    seen = set()
    for cid in ranked_ids:
        code = id_to_code.get(str(cid))
        if not code:
            continue
        if code in seen:
            continue
        seen.add(code)
        out.append(code)
        if len(out) >= top_k:
            break
    return out

# -------------------------
# Main
# -------------------------
def main():
    seed_str = os.environ.get(SEED_ENV)
    if seed_str and seed_str.strip():
        run_seed = int(seed_str) % (2**32 - 1)
    else:
        run_seed = int(time.time_ns() % (2**32 - 1))
    random.seed(run_seed)
    np.random.seed(run_seed)

    meta_df = pd.read_csv(META_PATH)
    docs_df = pd.read_csv(DOCS_PATH)

    # detect schema
    docs_key = find_docs_key(docs_df)
    text_col = find_text_col(docs_df)
    title_col = first_existing_col(meta_df, TITLE_COL_CANDIDATES)

    # build embeddings cache
    embedder, doc_mm, _, id_to_idx = load_or_build_embeddings(docs_df, text_col, docs_key)

    # candidate pool for picking filter combos
    base_pool = meta_df.copy()
    for col in [CODE_COL, CREDITS_COL, SEM_COL, LANG_COL]:
        if col not in base_pool.columns:
            raise SystemExit(f"Missing required column '{col}' in {META_PATH}")

    base_pool = base_pool.dropna(subset=[CODE_COL, CREDITS_COL, SEM_COL, LANG_COL])

    rows = []
    seen_cases = set()

    i = 1
    while i <= NUM_TESTCASES:
        # sample a random row to define filter constraints
        r = base_pool.sample(n=1, random_state=random.randint(0, 2**32 - 1)).iloc[0]

        credits = norm_credits(r[CREDITS_COL])
        sem = str(r[SEM_COL]).strip().lower()
        lang = str(r[LANG_COL]).strip().lower()

        # normalize constraint enums
        sem = sem if sem in ["autumn", "spring"] else "ANY"
        lang = lang if lang in ["et", "en"] else "ANY"

        # choose level sometimes, otherwise ANY
        level = "ANY"
        if LEVEL_COL in base_pool.columns and random.random() < 0.6:
            levels = sorted(split_levels(str(r.get(LEVEL_COL, ""))))
            level = random.choice(levels) if levels else "ANY"
            level = level if level in ["bachelor", "master", "doctoral"] else "ANY"

        # apply filters and ensure enough candidates
        fmeta = apply_filters(meta_df, credits, sem, lang, level)
        if len(fmeta) < 10:
            continue

        # pick target course from filtered meta
        tgt = fmeta.sample(n=1, random_state=random.randint(0, 2**32 - 1)).iloc[0]
        tgt_col = first_existing_col(fmeta, COURSE_ID_CANDIDATES)
        if not tgt_col:
            continue
        tgt_id = str(tgt[tgt_col])

        # pick a doc chunk/text for that course id (if multiple, choose one random)
        doc_subset = docs_df[docs_df[docs_key].astype(str) == tgt_id]
        if len(doc_subset) == 0:
            continue
        doc_row = doc_subset.sample(n=1, random_state=random.randint(0, 2**32 - 1)).iloc[0]
        doc_text = str(doc_row[text_col]) if pd.notna(doc_row[text_col]) else ""

        title = ""
        if title_col and title_col in meta_df.columns and pd.notna(tgt.get(title_col)):
            title = str(tgt.get(title_col))

        prompt = make_prompt(title, doc_text)

        # compute expected from prompt (semantic oracle)
        top_codes = expected_top_codes(
            prompt, meta_df, docs_df, docs_key,
            embedder, doc_mm, id_to_idx,
            credits, sem, lang, level,
            TOP_K
        )
        if len(top_codes) < TOP_K:
            continue

        filters_str = f"credits={credits}, semester={sem}, language={lang}, level={level}"

        key = (prompt.strip(), filters_str.strip())
        if key in seen_cases:
            continue
        seen_cases.add(key)

        rows.append({
            "ID": f"R{i:03d}",
            "Päring": prompt,
            "Filtrid": filters_str,
            "Target_code": str(tgt.get(CODE_COL, "")),
            "Expected unique_ID (top_codes)": ", ".join(top_codes),
            "Tulemus (PASS/FAIL)": "",
            "Märkus": "Expected arvutatud semantilise otsingu järgi (prompt->embed->score->topk) samade filtritega.",
        })
        i += 1

    out_csv = ANALYSIS_DIR / "random_testcases_semantic.csv"
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    print(f"Valmis: {out_csv}")
    print(f"Seed: {run_seed} (set {SEED_ENV} to reproduce)")

if __name__ == "__main__":
    main()