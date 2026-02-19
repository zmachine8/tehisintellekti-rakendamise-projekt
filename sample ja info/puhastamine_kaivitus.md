```bash
# Puhastamise käivitamine (lühike)

cd /path/to/tehisintellekti-rakendamise-projekt

# venv + sõltuvused
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install pandas numpy jupyter ipykernel

# jooksuta puhastus (näidisandmed)
mkdir -p out
python cleaner_configurable.py --in data/sample_30_rows.csv --config cleaner_config.json --lang both --outdir out
ls -la out

# keele valik document_text jaoks (vajadusel)
python cleaner_configurable.py --in data/sample_30_rows.csv --config cleaner_config.json --lang et   --outdir out
python cleaner_configurable.py --in data/sample_30_rows.csv --config cleaner_config.json --lang en   --outdir out
python cleaner_configurable.py --in data/sample_30_rows.csv --config cleaner_config.json --lang both --outdir out

# pärisandmed (vajadusel)
# python cleaner_configurable.py --in toorandmed_aasta.csv --config cleaner_config.json --lang both --outdir out

# configi muutmine
nano cleaner_config.json

# Jupyteris (notebooki CELL-is) kui “No module named pandas”:
# import sys
# !{sys.executable} -m pip install -U pip
# !{sys.executable} -m pip install pandas numpy