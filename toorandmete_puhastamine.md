# Toorandmete puhastamine (ÕIS2 kursused)

## Eesmärk
Valmistada ette ÕIS2 kursuste toorandmestik nii, et:
- **metadata** sobib **hard-filteriks** (nt semester, keel, hindamisskaala, linn, õppeaste),
- **document_text** sobib **RAG** jaoks (kirjeldus + eesmärgid + õpiväljundid + eeldusained),
- veerud jäävad **paindlikuks** (ei kasuta ranget whitelist’i).

## Failide struktuur (soovitus)
tehisintellekti-rakendamise-projekt/
cleaner_configurable.py
cleaner_config.json
data/
sample_30_rows.csv # näidis
toorandmed_aasta.csv # pärisandmed
notebooks/
cleaning.ipynb
out/ # genereeritud väljundid


## Puhastusloogika

### 1) Eelfiltrid (read eemaldatakse datasetist)
- Päevaõpe: `version__target__study_type__code == "fulltime"`
- Kestus: `additional_info__duration_in_semesters <= 1`
- Katkestatud/removed/draft: eemaldatakse read, kus `state__code` või `version__state__code`
  sobib mustriga (nt `cancel/deleted/removed/...`)

### 2) JSON väljade “lihtsustamine” (flatten)
- Skript tuvastab JSON-string veerud (auto) ja/või võtab configist käsitsi määratud JSON veerud.
- Iga JSON veeru kohta lisatakse 3 uut veergu:
  - `<col>__codes`
  - `<col>__names`
  - `<col>__count`

Näide: `version__additional_info__study_levels` →  
`version__additional_info__study_levels__codes` (nt `bachelor;master`)

### 3) Metadata (hard-filteri jaoks)
`courses_metadata.csv` sisaldab:
- `additional_info__assessment_scale__code` (eristav/mitteeristav)
- `version__target__semester__code` (kevad/sügis)
- `version__target__language__code` (keel)
- `version__target__faculty__city` (linn)
- õppeastmed (`study_levels__codes` või `...study_levels__codes`)
- + võtmeväljad (nt `course_uuid`, `version__uuid`, `code`, jne)

Täpne väljade nimekiri on `cleaner_config.json` → `metadata.base_fields`.

### 4) Document text (RAG jaoks)
`courses_documents.csv` sisaldab `document_text`, mis pannakse kokku valitud keele(de)ga:
- pealkiri
- kirjeldus
- eesmärgid
- õpiväljundid
- eeldusained

Tekst kasutab “fallback” loogikat: eelistab `version__...` veerge, muidu võtab “general” veeru.

Keele valik:
- `--lang et` / `--lang en` / `--lang both`

## Väljundfailid
Skript kirjutab `out/` kausta:
- `courses_cleaned_full.csv` – puhastatud read, kõik veerud (paindlik)
- `courses_metadata.csv` – hard-filteri metadata
- `courses_documents.csv` – `document_text` + võtmeväljad + (valikuliselt) metadata võtmed
- `clean_report.json` – eemaldatud ridade loendus + JSON flatten info + missing + kategoorilised + tekstipikkuse statistika

## Märkused
- Kui skript jookseb erroriga ja mainib `add_block(... missing argument ...)`, kontrolli, et
  `learning_outcomes` ET plokis oleks rida:
  `add_block("Õpiväljundid", lo_et)`