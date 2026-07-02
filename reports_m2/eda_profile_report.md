# Module 2 — Pre-Engineering Dataset Profile

- Rows: 590,540
- Columns (ML-ready, post encrypted-column blocklist): 422
- Numeric columns: 384
- Categorical columns: 29
- ID-like high-cardinality numeric columns: ['card1', 'card2', 'card3', 'card5', 'addr1', 'addr2']
- Target distribution: {'0': 0.9650099908558268, '1': 0.03499000914417313}
- Columns with >5% missing: 310

## Top 20 numeric columns by |correlation| with isFraud

| Column | Correlation |
|---|---|
| V257 | 0.3831 |
| V246 | 0.3669 |
| V244 | 0.3641 |
| V242 | 0.3606 |
| V201 | 0.3280 |
| V200 | 0.3188 |
| V189 | 0.3082 |
| V188 | 0.3036 |
| V258 | 0.2972 |
| V45 | 0.2818 |
| V158 | 0.2781 |
| V156 | 0.2760 |
| V149 | 0.2733 |
| V228 | 0.2689 |
| V44 | 0.2604 |
| V86 | 0.2518 |
| V87 | 0.2517 |
| V170 | 0.2498 |
| V147 | 0.2429 |
| V52 | 0.2395 |

## Redundant column pairs (|corr| > 0.95)

Found 572 pairs. First 20 shown:

| Column A | Column B | |corr| |
|---|---|---|
| D12 | D4 | 1.0000 |
| V322 | V95 | 0.9999 |
| V323 | V96 | 0.9999 |
| V324 | V97 | 0.9999 |
| V322 | V101 | 0.9997 |
| V322 | V279 | 0.9996 |
| V101 | V95 | 0.9996 |
| V293 | V279 | 0.9996 |
| C12 | C7 | 0.9995 |
| V324 | V280 | 0.9995 |
| V322 | V293 | 0.9994 |
| V177 | V167 | 0.9994 |
| V324 | V103 | 0.9993 |
| V329 | V105 | 0.9991 |
| V293 | V101 | 0.9989 |
| V323 | V102 | 0.9988 |
| V324 | V295 | 0.9988 |
| V103 | V97 | 0.9988 |
| V279 | V95 | 0.9987 |
| V295 | V280 | 0.9986 |