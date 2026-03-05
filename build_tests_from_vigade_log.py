#!/usr/bin/env python3
import os, json
import pandas as pd

IN_LOG = "out/vigade_log.csv"                 # change if needed
OUT_DIR = "out/analysis"
OUT_IN  = os.path.join(OUT_DIR, "in_tests.csv")
OUT_EXP = os.path.join(OUT_DIR, "expected_snapshot.csv")

# "first" = freeze earliest baseline; "last" = freeze latest baseline
BASELINE_MODE = "first"

def main():
    df = pd.read_csv(IN_LOG)

    # keep only final step successes
    if "Samm" in df.columns:
        df = df[df["Samm"].astype(str).str.strip().eq("llm_generate")]
    if "Tulemus" in df.columns:
        df = df[df["Tulemus"].astype(str).str.strip().eq("OK")]

    # parse DetailidJSON safely
    def parse_detail(s):
        try:
            return json.loads(s) if isinstance(s, str) and s.strip() else {}
        except Exception:
            return {}

    details = df["DetailidJSON"].apply(parse_detail) if "DetailidJSON" in df.columns else [{}]*len(df)
    df = df.copy()
    df["top_codes"] = details.apply(lambda d: d.get("top_codes", []))
    df["top_k"] = details.apply(lambda d: d.get("top_k", None))
    df["filtered_count"] = details.apply(lambda d: d.get("filtered_count", None))
    df["docs_scored"] = details.apply(lambda d: d.get("docs_scored", None))

    # normalize key fields
    df["Päring"] = df["Päring"].astype(str).str.strip()
    df["Filtrid"] = df["Filtrid"].astype(str).str.strip()

    # de-duplicate by (query, filters)
    if BASELINE_MODE == "first":
        df = df.sort_values("Aeg", ascending=True)
    else:
        df = df.sort_values("Aeg", ascending=False)

    df_u = df.drop_duplicates(subset=["Päring", "Filtrid"], keep="first").reset_index(drop=True)

    os.makedirs(OUT_DIR, exist_ok=True)

    # in_tests: what you will rerun in the app
    in_tests = df_u[["Päring", "Filtrid"]].rename(columns={"Päring":"query","Filtrid":"filters_str"})
    in_tests.to_csv(OUT_IN, index=False)

    # expected snapshot: what retrieval *should* return (baseline)
    exp = df_u[["Päring","Filtrid","top_k","filtered_count","docs_scored","top_codes","Aeg"]].copy()
    exp.rename(columns={"Päring":"query","Filtrid":"filters_str","Aeg":"baseline_time"}, inplace=True)

    # store top_codes as JSON string in CSV
    exp["expected_top_codes_json"] = exp["top_codes"].apply(lambda x: json.dumps(x, ensure_ascii=False))
    exp.drop(columns=["top_codes"], inplace=True)

    exp.to_csv(OUT_EXP, index=False)

    print(f"OK: wrote {len(in_tests)} unique tests")
    print(f"- {OUT_IN}")
    print(f"- {OUT_EXP}")

if __name__ == "__main__":
    main()