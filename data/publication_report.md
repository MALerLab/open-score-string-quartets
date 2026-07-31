# OSSQ Dataset — Publication & Source-Type Analysis
- Total MuseScore entries: **122**
- Unique works (deduped by `path`): **116**
  - 4× `Mayer, Emilie / String Quartet in G minor, Op.14` are movement variants of one work
  - 4× `Mozart / String Quartet No.18 in A major, K.464` are movement variants of one work
  - All 6 Saint-Georges Op.1 Nos.1–6 are distinct works sharing one IMSLP source file

All counts below are **per unique work** unless stated.

---

## 1. Publishers (32 unique)

Canonical spellings are used (`Breitkopf und Härtel` → `Breitkopf & Härtel`; `Eulenburg` → `Ernst Eulenburg`; `Jos. Aibl` → `Joseph Aibl`; `Durand & Fils` → `Durand`).

| count | publisher |
|---|---|
| 34 | Breitkopf & Härtel |
| 21 | Ernst Eulenburg |
| 10 | Trautwein |
| 6 | Holograph manuscript *(not a real publisher — autograph sources)* |
| 6 | Sieber |
| 4 | Universal Edition |
| 3 | Augener |
| 2 | M.P. Belaieff, Durand, C.F. Peters, J. Hamelle, SNKLHU, Joseph Aibl, Lauterbach & Kuhn |
| 1 | Ph. Petit, Fundación Vizcaína Aguirre, Rózsavölgyi & Cie., A-R Editions, Pleyel, D. Rahter, Kistner, E.W. Fritzsch, N. Simrock, Novello, P. Jurgenson, Choudens, Richault et Cie., Johann André, Rob. Timm et C., J. & W. Chester, Hansen, G. Astruc |

Top-3 publishers (Breitkopf & Härtel, Ernst Eulenburg, Trautwein) cover **65 / 116 ≈ 56 %** of the dataset — both giants of 19th-century complete-edition and pocket-score publishing.

---

## 2. Publication years

### By decade

| decade | count |
|---|---|
| 1770s | 6 |
| 1780s | 1 |
| 1790s | 1 |
| 1820s | 1 |
| 1830s | 2 |
| 1840s | 10 |
| 1850s | 4 |
| 1860s | 12 |
| 1870s | 5 |
| 1880s | **19** |
| 1890s | 9 |
| 1900s | 6 |
| 1910s | 8 |
| 1920s | 9 |
| 1930s | **18** |
| 1950s | 1 |
| 1970s | 1 |
| 1990s | 1 |
| 2000s | 1 |

Bimodal distribution: peaks in the **1880s** (Breitkopf complete-edition wave) and the **1930s** (Eulenburg miniature-score reprint wave).

### All distinct years

```
1773×6  1785×1  1798×1  1824×1  1834×1  1838×1  1840×10 1850×1  1851×1
1855×1  1859×1  1861×1  1862×7  1863×3  1864×1  1870×1  1875×4  1881×6
1882×9  1884×1  1886×1  1887×1  1888×1  1890×2  1892×1  1893×1  1894×3
1895×1  1896×1  1900×1  1902×1  1903×2  1905×1  1908×1  1910×2  1911×1
1912×1  1914×1  1915×1  1916×1  1919×1  1920×2  1922×1  1923×1  1925×2
1926×3  1930×18 1955×1  1975×1  1994×1  2006×1
```

51 distinct years.

### Notable single-year clusters

- **1773 (6)** — Saint-Georges Op.1 Nos.1–6 (Sieber first edition, Paris)
- **1840 (10)** — Haydn Op.1/Op.9 reprints by Trautwein (Berlin)
- **1862 (7)** — Beethoven Op.18 set in Breitkopf *Gesammelte Ausgabe*
- **1881 (6)** — Eulenburg miniature-score launch titles
- **1882 (9)** — Mozart *Werke* (Breitkopf)
- **1930 (18)** — Eulenburg reprint wave (mostly Haydn Op.20/64/74/76)

---

## 3. Scanned-score types

Type codebook:

| code | label |
|---|---|
| -1 | ignored |
| 0 | manuscript |
| 1 | scanned |
| 1\` | scanned, double column |
| 1\`\` | scanned, double column + center-stapled order |
| 2 | digitally engraved |
| 3 | 4-part scores (part-book edition, one instrument per page) |
| 4 | 1st violin only |
| 5 | 2nd violin only (not present in data) |
| 6 | viola only (not present in data) |
| 7 | cello only (not present in data) |

### Distribution (per unique work, n=116)

| type | label | count | share |
|---|---|---|---|
| 1 | scanned | 89 | 76.7 % |
| 4 | 1st violin only | 12 | 10.3 % |
| 0 | manuscript | 6 | 5.2 % |
| 3 | 4-part scores | 5 | 4.3 % |
| 1\` | scanned, double column | 2 | 1.7 % |
| 1\`\` | scanned, dbl col + stapled | 1 | 0.9 % |
| 2 | digitally engraved | 1 | 0.9 % |

No `-1` entries remain (previously-ignored Fauré Op.121, Janáček No.2, Mozart K.465 have been reclassified to type 1).

Types 5/6/7 (vln2/vla/vc-only) are in the codebook but never used — when a part-book is the source, OSSQ always picks the violin-1 book.

### Per-type era and publishers

| type | n | year range | publisher concentration |
|---|---|---|---|
| 0 (manuscript) | 6 | 1834–1870 | all "Holograph manuscript"; all by women composers (Andrée, Hensel, Maier, Mayer ×3) |
| 1 (scanned) | 89 | 1840–1994 | Breitkopf & Härtel (33), Ernst Eulenburg (20), Trautwein (10), Universal Edition (3) |
| 1\` | 2 | 1914–1922 | Augener, Universal Edition |
| 1\`\` | 1 | 1893 | Ernst Eulenburg (Stanford Op.44) |
| 2 (digital) | 1 | 2006 | Fundación Vizcaína Aguirre (Arriaga No.3) |
| 3 (4 parts) | 5 | 1798–1896 | one-off 19th-c. publishers: Pleyel, Fritzsch, Richault, C.F. Peters, Rob. Timm et C. |
| 4 (vln-1) | 12 | 1773–1920 | Sieber (6, all Saint-Georges Op.1); 6 one-offs |

### Specific entries in smaller categories

**Type 0 — manuscript (6).** All autographs, all women composers:
- Andrée, Elfrida — String Quartet in A major (1861)
- Hensel, Fanny — String Quartet in E-flat major, Op.277 (1834)
- Maier, Amanda — String Quartet in A major (1870)
- Mayer, Emilie — Quartets in A major (1855), D major (1850), E minor (1851)

**Type 3 — 4-part scores (5 unique works).**
- Boccherini, Luigi — Op.39 (Pleyel, 1798)
- Carreño, Teresa — String Quartet (E.W. Fritzsch, 1896)
- Gouvy, Théodore — Op.16 No.1 (Richault et Cie., 1859)
- Kalliwoda, J.W. — Op.90 (C.F. Peters, 1838)
- Mayer, Emilie — Op.14 (Rob. Timm et C., 1864) *(4 movement-duplicate entries in raw data)*

**Type 4 — 1st violin only (12).**
- Saint-Georges, J.B. — Op.1 Nos.1–6 (Sieber, 1773) *(6 works, single shared IMSLP file #80710)*
- Arriaga, J.C. de — No.1 in D minor (Ph. Petit, 1824)
- Bridge, Frank — No.2, H.115 (Augener, 1915)
- Gounod, Charles — No.3 in A minor (Choudens, 1895)
- Hoffmeister, F.A. — No.9 in D major (Johann André, 1785)
- Krzyżanowska, Halina — Op.44 (J. Hamelle, 1920)
- Smetana, Bedřich — No.1 (Breitkopf & Härtel, 1910)

**Type 1\` — scanned, double column (2).**
- Delius, Frederick — Quartet in E minor (Augener, 1922)
- Smyth, Ethel — Quartet in E minor (Universal Edition, 1914)

**Type 1\`\` — scanned, double column + center-stapled (1).**
- Stanford, C.V. — Op.44 (Ernst Eulenburg, 1893)

**Type 2 — digitally engraved (1).**
- Arriaga, J.C. de — No.3 in E-flat major (Fundación Vizcaína Aguirre, 2006)

---

## 4. OMR pipeline implications

| tier | types | works | notes |
|---|---|---|---|
| Full scores (direct OMR) | 1, 1\`, 1\`\`, 2 | **93 (80 %)** | engraved or digital full scores; clean OMR targets |
| Part-book sources | 3, 4 | **17 (15 %)** | single-instrument-per-page; full-score reconstruction requires supplemental part-book scans or MuseScore-side alignment |
| Manuscript | 0 | **6 (5 %)** | lowest OMR fidelity; treat as separate evaluation tier |
| Excluded | -1 | **0** | none after reclassification |

Effective usable set: **116 unique works / 122 entries**.

---

## 5. Notes on the Saint-Georges cluster

All 6 Op.1 quartets share IMSLP file **#80710** because 18th-century chamber music was published as separate **part-books** (one per player), not scores. IMSLP #80710 is the Sibley Music Library scan of the Violin 1 part-book from the 1773 Sieber first edition (`M452 S139 op.1`) — one PDF containing the violin-1 line of all 6 quartets. Sister part-books exist at IMSLP #80711/#80712/#80713 (Vln2/Vla/Vc), plus a modern re-engraved full score at #707447. OSSQ metadata stores only the violin-1 file as representative; the type label (`4 = 1st violin only`) reflects this.
