#!/usr/bin/env python3
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

BASE = Path(__file__).parent
TESTS_PATH = BASE / "out" / "analysis" / "random_testcases.csv"
DOCS_PATH  = BASE / "out" / "courses_documents.csv"
META_PATH  = BASE / "out" / "courses_metadata.csv"
OUT_PATH   = BASE / "out" / "analysis" / "random_testcases_with_expected.csv"

# Pane siia SAMA embedding-mudel, mis su äpis
EMBED_MODEL = "intfloat/multilingual-e5-small"

TOP_K = 5
BATCH = 64

DOC_KEY_COL  = "course_uuid"
DOC_TEXT_COL = "document_text"
CODE_COL     = "code"

SEM_COL   = "version__target__semester__code"
LANG_COL  = "version__target__language__code"
LEVEL_COL = "version__additional_info__study_levels__codes"
CREDITS_COL = "credits"

def parse_filters(filters_str: str):
    out = {}
    for part in str(filters_str).split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out

def norm_credits(x):
    s = str(x).strip()
    if s.lower() in ["nan", "none", ""]:
        return None
    try:
        return int(float(s))
    except Exception:
        return None

def main():
    for p in [TESTS_PATH, DOCS_PATH, META_PATH]:
        if not p.exists():
            raise SystemExit(f"Puudub fail: {p}")

    tests = pd.read_csv(TESTS_PATH).fillna("")
    docs  = pd.read_csv(DOCS_PATH).fillna("")
    meta  = pd.read_csv(META_PATH).fillna("")

    # docs peab sisaldama neid veerge
    for col in [DOC_KEY_COL, DOC_TEXT_COL, CODE_COL, SEM_COL, LANG_COL, LEVEL_COL]:
        if col not in docs.columns:
            raise SystemExit(f"courses_documents.csv puudub veerg: {col}")

    # meta-st on vaja ainult credits (et filtrit 'credits=' kontrollida)
    if DOC_KEY_COL not in meta.columns or CREDITS_COL not in meta.columns:
        raise SystemExit("courses_metadata.csv peab sisaldama 'course_uuid' ja 'credits' veerge")

    # merge only credits to avoid suffix hell
    docs = docs.merge(
        meta[[DOC_KEY_COL, CREDITS_COL]],
        on=DOC_KEY_COL,
        how="left",
        suffixes=("", "_meta"),
    )

    # precompute embeddings once
    embedder = SentenceTransformer(EMBED_MODEL)
    texts = docs[DOC_TEXT_COL].astype(str).tolist()
    doc_embs = embedder.encode(texts, batch_size=BATCH, normalize_embeddings=True, show_progress_bar=True)
    doc_embs = np.asarray(doc_embs, dtype=np.float32)

    def filter_mask(f):
        mask = np.ones(len(docs), dtype=bool)

        if f.get("credits") and f["credits"] != "ANY":
            c = norm_credits(f["credits"])
            if c is not None:
                mask &= docs[CREDITS_COL].apply(norm_credits).to_numpy() == c

        if f.get("semester") and f["semester"] != "ANY":
            sem = f["semester"].lower()
            mask &= docs[SEM_COL].astype(str).str.lower().to_numpy() == sem

        if f.get("language") and f["language"] != "ANY":
            lang = f["language"].lower()
            mask &= docs[LANG_COL].astype(str).str.lower().to_numpy() == lang

        if f.get("level") and f["level"] != "ANY":
            lvl = f["level"].lower()
            mask &= docs[LEVEL_COL].fillna("").astype(str).str.lower().str.contains(lvl, na=False).to_numpy()

        return mask

    expected_list = []
    for _, row in tests.iterrows():
        query = str(row["Päring"])
        f = parse_filters(row["Filtrid"])
        idx = np.where(filter_mask(f))[0]

        if len(idx) == 0:
            expected_list.append("")
            continue

        q_emb = embedder.encode([query], normalize_embeddings=True)
        q_emb = np.asarray(q_emb[0], dtype=np.float32)

        scores = doc_embs[idx] @ q_emb
        top_local = np.argsort(-scores)[:TOP_K]
        top_global = idx[top_local]

        top_codes = docs.iloc[top_global][CODE_COL].fillna("").astype(str).tolist()
        seen = set()
        top_codes = [c for c in top_codes if c and not (c in seen or seen.add(c))]

        expected_list.append(", ".join(top_codes[:TOP_K]))

    out = tests.copy()
    out["Expected unique_ID (top_codes)"] = expected_list
    out.to_csv(OUT_PATH, index=False)
    print(f"Valmis: {OUT_PATH}")

if __name__ == "__main__":
    main()