**Põhierinevus on, kui “tark” ja kuidas ta infot kasutab.**

### app1.py
- Ei kasuta LLM-i.
- Lihtne Streamlit chat UI + “dummy” automaatvastus.
- Eesmärk: saada Streamlit tööle ja näha, et vestlusajalugu toimib.

### app2.py
- Lisab päris LLM-i ühenduse **OpenRouteri kaudu**.
- Kasutab mudelit **`google/gemma-3-27b-it`**.
- Vastus tuleb “streaminguna” (tekst jookseb ekraanile).

### app3.py
- Sama mis app2, aga lisab LLM-ile **andmekonteksti**: loeb `puhtad_andmed.csv` **10 esimest rida** ja paneb need system prompti.
- See ei ole veel RAG: mudel näeb ainult neid 10 rida, mitte “otsingut kogu tabelis”.

### app4.py
- Esimene “päris” RAG samm.
- Kasutab `puhtad_andmed_embeddings.pkl` embeddinguid ja teeb **semantilise otsingu** (cosine similarity) kogu andmestikus.
- LLM saab prompti juurde ainult **top N** kõige sarnasemad kursuseread (mitte kogu csv).

### app5.py
- Sama RAG mis app4, aga enne semantilist otsingut teeb **metaandmete filtri** (nt semester, EAP vms).
- Eesmärk: vähendada otsinguruumi ja hoida tulemused täpsemad (“otsi ainult filtrile vastavatest kursustest”).