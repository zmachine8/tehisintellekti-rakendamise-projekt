#!/usr/bin/env python3
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


BASE = Path(__file__).parent
DOCS_PATH = BASE / "out" / "courses_documents.csv"
OUT_DIR = BASE / "out" / "emb_cache"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Pane siia SAMA mudel, mis su rakenduses
EMBED_MODEL = "intfloat/multilingual-e5-small"

DOC_TEXT_COL = "document_text"

BATCH = 64
DTYPE = np.float16  # väiksem fail; kui tahad täpsem, pane np.float32


def main():
    if not DOCS_PATH.exists():
        raise SystemExit(f"Puudub: {DOCS_PATH}")

    docs = pd.read_csv(DOCS_PATH).fillna("")
    if DOC_TEXT_COL not in docs.columns:
        raise SystemExit(f"courses_documents.csv puudub veerg: {DOC_TEXT_COL}")

    texts = docs[DOC_TEXT_COL].astype(str).tolist()

    embedder = SentenceTransformer(EMBED_MODEL)
    embs = embedder.encode(
        texts,
        batch_size=BATCH,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    embs = np.asarray(embs, dtype=DTYPE)

    mmap_path = OUT_DIR / "doc_embs.mmap"
    meta_path = OUT_DIR / "doc_embs_meta.json"

    # kirjuta memmap
    mm = np.memmap(mmap_path, dtype=DTYPE, mode="w+", shape=embs.shape)
    mm[:] = embs[:]
    mm.flush()

    meta = {
        "model": EMBED_MODEL,
        "dtype": str(DTYPE),
        "shape": [int(embs.shape[0]), int(embs.shape[1])],
        "docs_path": str(DOCS_PATH),
        "text_col": DOC_TEXT_COL,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Valmis: {mmap_path}")
    print(f"Valmis: {meta_path}")


if __name__ == "__main__":
    main()