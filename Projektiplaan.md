# 🤖 Tehisintellekti rakendamise projektiplaani mall (CRISP-DM)

## 🔴 1. Äritegevuse mõistmine
*Fookus: mis on probleem ja milline on hea tulemus?*  
Eesmärk on luua vestlusliidesega õppeainete otsingu- ja soovitussüsteem, mis kasutab Tartu Ülikooli ÕIS2 avalikke andmeid, et leida kasutaja vabatekstilisele päringule sobivad õppeained ning vajadusel küsida täpsustavaid küsimusi.

### 🔴 1.1 Kasutaja kirjeldus ja eesmärgid
**Kellel on probleem ja miks see lahendamist vajab?**  
Probleem on eelkõige Tartu Ülikooli tudengitel (ning teisejärguliselt külalistudengitel ja huvilistel), kes soovivad leida endale sobivaid valik- ja vabaaineid. ÕIS2-s on tuhandeid õppeaineid ning nende ükshaaval sirvimine on ajamahukas. Praegused filtrid ja märksõnapõhine otsing eeldavad, et kasutaja teab täpseid otsingusõnu või õigeid kategooriaid, mistõttu jäävad semantiliselt sobivad ja “avastamist” toetavad vasted sageli leidmata.

**Milline on lahenduse oodatud kasu?**  
- Õppeainete leidmine vabateksti abil (nt “praktiline andmeanalüüs kevadel, 3 EAP, inglise keeles”).  
- Paremini sobituvad soovitused kasutaja huvide, ajakava ning eelistustega.  
- Interdistsiplinaarsete ja uute valdkondade ainete lihtsam avastamine.  
- Vähem ajakulu ja frustreerivat katsetamist filtritega.

**Milline on hetkel eksisteeriv lahendus?**  
ÕIS2 standardotsing ja filtrid (märksõnad, õppeüksus, semester jne). Need toimivad hästi, kui kasutaja teab täpseid otsingusõnu, kuid ei toeta piisavalt paindlikku semantilist otsingut ega vestluslikku täpsustamist.

### 🔴 1.2 Edukuse mõõdikud
Rakendus on edukas, kui see:
1. **Leiab asjakohaseid vasteid vabatekstilistele päringutele**, sh semantilised vasted ka sõnasõnalise kattuvuseta.  
2. **Rakendab korrektselt ranged filtrid**, kui need esinevad päringus (nt semester, keel, EAP, instituut/valdkond, õppevorm).  
3. **Reastab tulemused sobivuse järgi** ja annab lühikese põhjenduse, miks iga soovitus sobib.  
4. **Ei paku ebasobivaid/teemaväliseid tulemusi** ega “väljamõeldud” aineid, mida andmestikus ei ole.  
5. **Töötab mõistliku kiirusega**, et kasutaja saaks tulemused sujuvalt kätte.

**Arenduse käigus mõõdetavad näitajad:**
- *Recall@k / nDCG@k*: kas asjakohased ained tulevad top-k hulka ja on eespool.  
- *Filtritäpsus*: kas ranged filtrid rakenduvad õigesti.  
- *Latentsus*: vastuse aeg.  
- *Kasutaja tagasiside*: 👍/👎, “leidsin sobiva aine” (jah/ei).

Pikemaajaliselt saab edukust hinnata ka õppekavaväliste ainete valimise kasvu ning kasutajate kvalitatiivse tagasiside kaudu.

### 🔴 1.3 Ressursid ja piirangud
**Ressursid:**
- Arendusaeg: ~1 kuu.  
- Eelarve tasuliste mudelite/API-de kasutuseks: ~50€ / 20 inimest (vajadusel piiratud mahus).  
- Arvutusvõimsus: eelistatult lokaalne lahendus (embeddingud + vektorotsing), et hoida kulud kontrolli all.

**Tehnilised piirangud:**
- Andmeallikas: ÕIS2 avalik API ja sellest tehtud väljavõte (CSV/DB).  
- Rakendus peab toetama regulaarset andmete uuendamist (uusimad ainekavad/versioonid).  
- Vastused peavad tuginema andmestikule (RAG / “closed-book”), et vältida valesid kursusepakkumisi.

**Juriidilised ja eetilised piirangud (GDPR):**
- Andmestik võib sisaldada õppejõudude isikuandmeid; avaliku rakenduse puhul tuleb hinnata nende kuvamise vajalikkust ning vajadusel eemaldada isikuandmed või taotleda luba/eetikakomitee hinnangut.  
- Logides ei säilitata isikuandmeid; päringud hoitakse anonüümselt ja minimaalselt.

**Sisu- ja turvanõuded:**
- Rakendus ei tohi anda õppeainete otsinguga mitteseotud vastuseid.  
- Prompt-injection ja muu sisendmanipulatsiooni risk tuleb maandada (reeglid, “only-from-data” vastamise põhimõte).  
- Ebakindluse korral küsib süsteem täpsustusi (nt “Kas pead silmas kevad- või sügissemestrit?”).

---

## 🟠 2. Andmete mõistmine
*Fookus: millised on meie andmed?*

### 🟠 2.1 Andmevajadus ja andmeallikad
Lahenduse toimimiseks on vaja infot Tartu Ülikoolis õpetatavate õppeainete kohta vähemalt ühe õppeaasta ulatuses (eelistatult viimase 2 aasta lõikes), sh:
- aine kood ja nimetus (ET/EN),
- EAP, tase/õppeaste, õppevorm, keel,
- semester/ajad ja versioonid,
- institutsioon/õppeüksus/valdkond,
- kirjeldus, õpiväljundid, eeltingimused (kui olemas).

Andmed pärinevad ÕIS2 API-st ning on avalikult kättesaadavad; ligipääs on tagatud.

### 🟠 2.2 Andmete kasutuspiirangud
Andmed on avalikud, kuid sisaldavad potentsiaalselt isikuandmeid (nt õppejõudude nimed).  
- Kursuse raames ja lokaalses prototüübis on kasutus risk väiksem.  
- Avaliku rakenduse korral tuleb hinnata õiguslikke/eetilisi nõudeid; soovi korral eemaldatakse isikuandmed (õppejõudude väljad) või taotletakse vajalikud kooskõlastused.

### 🟠 2.3 Andmete kvaliteet ja maht
- Formaat: CSV.  
- Maht: ~45.3 MB, 3031 rida, 223 veergu.  
- Tunnused: segatüübilised (tekst, numbrid, bool, ning JSON-kujul väljad).  
- Probleemid: dubleerivad veerud (üldinfo vs versiooni info), mitmekeelsed väljad, puuduvad väärtused, JSON väljade vajadus lahti parsida.  
- Eeltöö vajadus: mõõdukas (puhastus ja veergude valik on vajalik, kuid andmestiku maht on hallatav).

### 🟠 2.4 Andmete kirjeldamise vajadus
Andmete kirjeldamiseks ja kvaliteedi hindamiseks tuleb:
1. Kaardistada kõik 223 veeru tähendused ning valida “tuumikveerud” (otsing + filtrid + kuvamine).  
2. Tuvastada dubleerivad väljad ja otsustada, millist allikat eelistada (nt versioonipõhine info vs üldinfo).  
3. Parsida JSON väljad (nt struktuursed atribuudid) ning viia need standardkujule.  
4. Koostada kursuse kohta “dokumenditekst” semantilise otsingu jaoks (valitud tekstiväljad kokku).  
5. Analüüsida puuduvate väärtuste osakaalu ja otsustada käsitlus (eemaldus, imputatsioon, “unknown”, alternatiivne allikas).  
6. Luua lühike andmesõnastik (data dictionary) + kvaliteediraport (puuduvad väärtused, unikaalsus, väärtuste jaotus).

---

## 🟡 3. Andmete ettevalmistamine
*Fookus: toorandmete viimine tehisintellekti jaoks sobivasse formaati.*

### 🟡 3.1 Puhastamise strateegia
Peamised sammud:
1. **Veergude valik ja normaliseerimine**
   - valitakse vajalikud veerud (otsingutekst + filtrid + identifikaatorid),
   - ühtlustatakse nimetused ja väärtuste formaadid (nt semester, keeled, EAP).
2. **JSON väljade lahtiparsimine**
   - eraldatakse olulised võtmed (nt õppevorm, hindamine, õppeüksus vms),
   - salvestatakse struktureeritult (tabel/veerud).
3. **Dubleerivate ja mitmekeelsete väljade käsitlus**
   - eelistatakse kindlat hierarhiat (nt versioon > üldinfo),
   - tehakse ET ja EN kirjelduste strateegia (nt kombineeritud või kasutaja keele järgi).
4. **Puuduvate väärtuste käsitlus**
   - kriitilised filtriväljad: võimalusel täidetakse teisest allikast või märgitakse “unknown”,
   - tekstiväljad: tühjad asendatakse tühistringiga, et vältida katkiseid dokumenditekste.
5. **Andmete valideerimine**
   - kontrollitakse unikaalsus (course_uuid),
   - kontrollitakse EAP ja semestri väärtuste mõistlikkus.

Ajahinnang: ~1 nädal (sh veergude analüüs, puhastus, dokumentatsioon).

### 🟡 3.2 Tehisintellektispetsiifiline ettevalmistus
Valmistatakse ette kaks paralleelset representatsiooni:

1. **Struktuurne andmestik filtreerimiseks**
   - SQLite/PostgreSQL/pandas-tabel, kus on standardiseeritud filtriväljad:
     semester, EAP, keel, õppevorm, õppeüksus, tase jne.

2. **Dokumendid semantilise otsingu (RAG) jaoks**
   - iga kursuse kohta koostatakse “dokumenditekst”, nt:
     - pealkiri (ET/EN),
     - lühikirjeldus,
     - märksõnad/teemad,
     - õpiväljundid ja eeltingimused (kui olemas),
     - (valikuline) õppevorm/keel/EAP tekstina.
   - dokumendile lisatakse metaandmed:
     - course_uuid, kood, semester, keel, EAP, õppeüksus.

3. **Vektoriseerimine ja indeks**
   - dokumendid teisendatakse embedding-mudeli abil vektoriteks,
   - vektorid salvestatakse FAISS/Chroma indeksisse,
   - metaandmed jäävad filtrite ja tulemuste kuvamise jaoks külge.

4. **Tükeldamine (kui vaja)**
   - kui kirjeldused on pikad, tükeldatakse loogilisteks osadeks,
   - säilitatakse seos kursusega (chunk → course_uuid).

5. **Versioonihaldus**
   - andmetõmme ja indeksid seotakse kuupäeva/versiooniga, et tagada “uusim andmestik” ja reprodutseeritavus.

---

## 🟢 4. Tehisintellekti rakendamine
*Fookus: Tehisintellekti rakendamise süsteemi komponentide ja disaini kirjeldamine.*

### 🟢 4.1 Komponentide valik ja koostöö
Rakendus koosneb kahest põhiosast: **otsing + vastuse koostamine** (chatbot).

**Põhikomponendid (AI + mitte-AI):**
1. **Andmete kiht**
   - ÕIS2 API-st perioodiline tõmme (nt 1x nädalas / 1x päevas) → CSV/SQLite.
   - Puhastamise pipeline (JSON väljad lahti, dubleerivad kirjeldused kokku, keelevalik, puuduvate väljade käsitlus).
2. **Indekseerimine / otsing**
   - **Semantiline otsing**: kursuse “dokumendi” (valitud veergude tekst) vektorid + vektorandmebaas (FAISS/Chroma).
   - **Struktuurne filter**: semester, õppevorm, instituut, EAP, keel, tase jne (klassikaline filter SQL-is või pandas’is).
   - **Hübriidotsing** (soovitav): BM25 (sõnapõhine) + vektorotsing, tulemid kokku.
3. **Päringu tõlgendamine**
   - LLM/reeglid, mis tuvastavad päringust **(a)** semantilise soovi ja **(b)** ranged filtrid.
   - Näide: “tahan kevadel 3 EAP masinõppe kursust inglise keeles” → filtrid + semantiline otsing.
4. **Vastuse koostamine (chatbot)**
   - LLM genereerib vastuse **ainult leitud kursuste põhjal** (RAG).
   - Lisab lühikokkuvõtte, miks sobib, ja toob välja olulised väljad (EAP, keel, semester, vorm).
5. **Kasutajaliides**
   - Veebirakendus (nt React/Next.js või Flask/FastAPI + HTML).
   - “Chat” vaade + filtrite paneel + tulemite nimekiri.
6. **Logimine ja hindamine**
   - Päringud, valitud tulemused, tagasiside (👍/👎, “liiga ebatäpne”, “vale semester”, jne).
   - Teststsenaariumite jooksutamine (offline evaluation).

**Koostööloogika (voog):**
Kasutaja päring → päringu tõlgendamine (filtrid + otsingutekst) → struktuurne filter → semantiline/hübriidotsing → top-N kursust → LLM vastus koos viidetega (kursuse kood/uuid) → UI.

---

### 🟢 4.2 Tehisintellekti lahenduste valik
**Soovitus: 2-režiimiline lahendus** (odav + vajadusel täpsem).

**(A) Embedding + RAG (peamine)**
- **Embedding mudel**: tasuta ja lokaalne (nt sentence-transformers tüüpi mudel), või API kui eelarve lubab.
- **Vektorbaas**: FAISS (lihtne, lokaalne) või Chroma (lihtne dev).
- Eelis: leiab semantilisi vasteid ka siis, kui sõnad ei kattu.

**(B) LLM päringu mõistmiseks ja vastuse koostamiseks**
- **Lokaalne väike LLM** (ressursside piires) või **tasuline API** piiratud kasutusega (50€ / 20 inimest).
- LLM roll on piiratud:
  1) ekstraktida filtrid,
  2) koostada kokkuvõtlik vastus leitud kursustest,
  3) mitte “välja mõelda” kursuseid.

**(C) Baseline ilma LLM-ita (kohustuslik võrdluseks)**
- Ainult BM25 + filtrid + lihtne templitatud vastus.
- Kasulik mõõtmaks, kas LLM/RAG päriselt lisab väärtust.

---

### 🟢 4.3 Kuidas hinnata rakenduse headust?
**Offline mõõdikud (teststsenaariumid)**
- Koostatakse 30–100 tüüpilist päringut (nt “andmeteadus algajale”, “bioinformaatika valikaine kevadel”, “veebiarendus inglise keeles”).
- Iga päringu jaoks käsitsi “asjakohaste” kursuste komplekt (või vähemalt top-5 ootused).
- Mõõdikud:
  - **Recall@k** (kas õiged kursused tulevad top-k hulka)
  - **Precision@k / nDCG@k** (kui hästi reastab)
  - **Filtritäpsus** (kas ranged filtrid rakenduvad korrektselt)

**Online/UX mõõdikud (kasutajate pealt)**
- Kasutaja tagasiside: 👍/👎, “leidsin sobiva aine” (jah/ei).
- “Time-to-first-relevant” (mitu sammu kuni sobiva leidmiseni).
- Logidest: milliseid tulemusi klikitakse/valitakse.

**Kvalitatiivne kontroll**
- Hallutsinatsioonitest: kas chatbot viitab kursustele, mida pole tulemis.
- “Ebavajalikud soovitused”: kui sageli pakub täiesti teise valdkonna aineid.

---

### 🟢 4.4 Rakenduse arendus
Iteratiivne parendustsükkel (väikeste sammudega):

1. **MVP 1: Filtrid + sõnapõhine otsing**
   - CSV/SQLite, lihtsad filtrid, BM25.
2. **MVP 2: Semantiline otsing**
   - Kursuse dokumentide koostamine, embeddingud, FAISS/Chroma.
3. **MVP 3: Hübriidotsing ja reastus**
   - BM25 + vektorotsingu kombineerimine, paremad “rank” heuristikad.
4. **MVP 4: Chatbot (RAG)**
   - LLM vastused ainult top-N kursuste põhjal.
   - Vastuse struktuur: 3–7 soovitust + miks + olulised väljad.
5. **MVP 5: Päringu filtreerija**
   - Filtrite ekstraktsioon (reeglid → vajadusel LLM).
6. **MVP 6: Tagasiside ja õppiv parendus**
   - Tagasiside kogumine → teststsenaariumite täiendamine → prompt/indekseerimise parendus.

---

### 🟢 4.5 Riskijuhtimine
**Hallutsinatsioonid**
- RAG “closed-book”: LLM saab kasutada ainult retrieved-kursuseid.
- Vastuses peab olema kursuse kood/uuid; kui ei leidu, chatbot ütleb “ei leidnud”.

**Kallutatus / ebaõiglane reastus**
- Reastuse läbipaistvus: näita “miks sobib” (märksõnad/filtrid).
- Väldi varjatud eelistusi (nt “populaarsed” ilma põhjenduseta).

**Turvalisus**
- Input sanitization (XSS, prompt-injection).
- Prompt-injection kaitse: ignoreeri kasutaja katseid muuta süsteemireegleid (“ära reegleid muuda”).
- Rate limiting (kui API mudel).

**Privaatsus**
- Õppejõudude isikuandmed: avaliku versiooni puhul eemaldada nimed või küsida luba.
- Logides mitte hoida isikuandmeid; päringud anonüümselt.

**Andmete ajakohasus**
- Automaatne andmete uuendus (cron), versioonihaldus.
- Indeksi uuendamine koos andmetõmbega.

---

## 🔵 5. Tulemuste hindamine
*Fookus: kuidas hinnata loodud lahenduse rakendatavust ettevõttes/probleemilahendusel?*

### 🔵 5.1 Vastavus eesmärkidele
Rakendus loetakse eesmärkidele vastavaks, kui:

1. **Asjakohasus**
   - Teststsenaariumites saavutab nt Recall@10 ≥ kokkulepitud lävi (nt 0.7) ja nDCG@10 paraneb võrreldes baseline’iga.
2. **Filtrite korrektsus**
   - Ranged filtrid (semester, keel, EAP, instituut) rakenduvad õigesti ≥ nt 95% juhtudest testides.
3. **Hallutsinatsioonide puudumine**
   - 0 juhtumit, kus pakutakse kursust, mida andmestikus pole (või mis ei ole retrieved hulgas).
4. **Kiirus**
   - Päringu vastus mõistliku ajaga (nt < 2–3 s lokaalselt; kui LLM API, siis < 5–8 s).
5. **Kasutaja rahulolu**
   - Pilottestis enamus kasutajaid leiab “vähemalt ühe sobiva aine” (nt ≥ 60–70% sessioonidest).

---

## 🟣 6. Juurutamine
*Fookus: kuidas hinnata loodud lahenduse rakendatavust ettevõttes/probleemilahendusel?*

### 🟣 6.1 Integratsioon
**Kasutusliides**
- Veebirakendus: chat + filtrid + tulemuste kaartide loetelu.
- Iga tulemi juures link ÕIS2 kursuse lehele (kui avalik URL olemas) või vähemalt kood/pealkiri.

**Integreerimine töövoogu**
- Tudeng: otsib → salvestab “lemmikutesse” → ekspordib nimekirja (CSV/tekst) oma kava planeerimiseks.
- (Valikuline) “Jaga linki” päringu tulemustele.

**Tehniline paigutus (kursuse raames)**
- Lokaalne käivitus: Docker compose (API + UI + vektorbaas failid).
- Hiljem: lihtne pilvehost (Render/Fly/VM), kui lubatud.

---

### 🟣 6.2 Rakenduse elutsükkel ja hooldus
**Vastutus**
- Projekti raames: tiim hooldab repo, dokumentatsiooni, andmetõmbe skripte.
- Hilisemalt: kui avalik, vaja “omanikku” (nt instituut/õppeinfosüsteemi tiim) või jätkutiimi.

**Uuendused**
- Andmed:
  - automaatne tõmme (nt kord nädalas) + indeksite rebuild.
- Mudelid:
  - embedding mudeli vahetus testide põhjal (regressioonitest).
  - promptid ja reastusloogika versioonihalduse all.
- Monitooring:
  - logid (error rate, latency),
  - päringute maht,
  - kasutaja tagasiside trendid.

**Kulud**
- Lokaalne: praktiliselt 0€ (arvutusvõimsus tiimi masinatel).
- API mudel: kulupiirang + rate limit + fallback baseline’ile.
- Pikaajaline: hostingu + domeeni kulu (kui vaja), indeksite uuendamise ressursid.
