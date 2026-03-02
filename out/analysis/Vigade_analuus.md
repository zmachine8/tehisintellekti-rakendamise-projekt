# Vigade analüüs
- Logifail: `out/vigade_log.csv`
- Katseid kokku: **25**
- Vigaseid (BAD): **5**

## Veakoond vahesammu kaupa

| Samm              |   Vigu |   % vigastest |
|:------------------|-------:|--------------:|
| llm_generate      |      3 |            60 |
| rag_vector_search |      1 |            20 |
| meta_filter       |      1 |            20 |
## Vigased juhtumid (väljavõte)

| Aeg                 | Päring                                              | Filtrid                                                 | Samm              | exception                                                                                                                                      |
|:--------------------|:----------------------------------------------------|:--------------------------------------------------------|:------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------|
| 2026-03-02 09:15:43 | minu eriala on informaatika                         | credits=3, semester=spring, language=en, level=bachelor | llm_generate      | Object of type DataFrame is not JSON serializable                                                                                              |
| 2026-03-02 09:19:32 | õpin informaatika erialal, mul on vaja 3eap kursust | credits=3, semester=spring, language=et, level=bachelor | rag_vector_search | matmul: Input operand 1 has a mismatch in its core dimension 0, with gufunc signature (n?,k),(k,m?)->(n?,m?) (size 384 is different from 1024) |
| 2026-03-02 09:29:27 | 1. jahj                                             | credits=ANY, semester=ANY, language=ANY, level=ANY      | llm_generate      | Object of type DataFrame is not JSON serializable                                                                                              |
| 2026-03-02 09:34:48 | kas HVEE.05.030 on 2 eap                            | credits=2, semester=autumn, language=et, level=bachelor | llm_generate      | Object of type DataFrame is not JSON serializable                                                                                              |
| 2026-03-02 10:20:48 | mis kursused on selle eap                           | credits=8, semester=spring, language=et, level=bachelor | meta_filter       |                                                                                                                                                |

## Failid
- Koond CSV: `out/analysis/vigade_koond.csv`
- Vigased juhtumid CSV: `out/analysis/vigased_juhtumid.csv`
