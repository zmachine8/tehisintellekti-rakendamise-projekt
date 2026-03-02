import json
from pathlib import Path
#python -m pip install tabulate
import pandas as pd


LOG_PATH = Path("out") / "vigade_log.csv"
OUT_DIR = Path("out") / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def safe_json_loads(x: str):
    try:
        return json.loads(x) if isinstance(x, str) else {}
    except Exception:
        return {}


def main():
    if not LOG_PATH.exists():
        raise SystemExit(f"Puudub logifail: {LOG_PATH}")

    df = pd.read_csv(LOG_PATH)

    # normaliseeri veeru nimed (kui sul peaksid veidi erinema)
    required = {"Aeg", "Päring", "Filtrid", "Samm", "Tulemus", "DetailidJSON"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Logifailist puuduvad veerud: {sorted(missing)}")

    bad = df[df["Tulemus"].astype(str).str.upper() == "BAD"].copy()

    # võta exception + message välja DetailidJSON-ist
    details = bad["DetailidJSON"].apply(safe_json_loads)
    bad["exception"] = details.apply(lambda d: d.get("exception", ""))
    bad["message"] = details.apply(lambda d: d.get("message", ""))

    total = len(df)
    bad_n = len(bad)

    # koond sammu kaupa
    if bad_n > 0:
        counts = bad["Samm"].value_counts().rename_axis("Samm").reset_index(name="Vigu")
        counts["% vigastest"] = (counts["Vigu"] / bad_n * 100).round(1)
    else:
        counts = pd.DataFrame(columns=["Samm", "Vigu", "% vigastest"])

    # salvesta tabelid
    counts_csv = OUT_DIR / "vigade_koond.csv"
    bad_csv = OUT_DIR / "vigased_juhtumid.csv"
    counts.to_csv(counts_csv, index=False)
    bad[["Aeg", "Päring", "Filtrid", "Samm", "exception", "message"]].to_csv(bad_csv, index=False)

    # markdown raport
    md_path = OUT_DIR / "Vigade_analuus.md"

    def md_table_from_df(x: pd.DataFrame) -> str:
        if x.empty:
            return "_(tühi)_\n"
        return x.to_markdown(index=False) + "\n"

    md = []
    md.append("# Vigade analüüs\n")
    md.append(f"- Logifail: `{LOG_PATH}`\n")
    md.append(f"- Katseid kokku: **{total}**\n")
    md.append(f"- Vigaseid (BAD): **{bad_n}**\n\n")

    md.append("## Veakoond vahesammu kaupa\n\n")
    md.append(md_table_from_df(counts))

    md.append("## Vigased juhtumid (väljavõte)\n\n")
    md.append(md_table_from_df(bad[["Aeg", "Päring", "Filtrid", "Samm", "exception"]].head(50)))

    md.append("\n## Failid\n")
    md.append(f"- Koond CSV: `{counts_csv}`\n")
    md.append(f"- Vigased juhtumid CSV: `{bad_csv}`\n")

    md_path.write_text("".join(md), encoding="utf-8")

    print(f"Valmis: {md_path}")
    print(f"Valmis: {counts_csv}")
    print(f"Valmis: {bad_csv}")


if __name__ == "__main__":
    main()