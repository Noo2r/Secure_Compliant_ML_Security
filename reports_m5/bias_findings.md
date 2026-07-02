# Module 5 — Bias Findings

Automatically generated findings from the computed fairness metrics.

## card6

- **[INFO]** Largest statistical parity disparity for 'card6': group 'credit' vs. reference 'debit' has SPD=0.0424 (95% CI [0.0395, 0.0453], statistically significant).
- **[INFO]** Smallest statistical parity disparity for 'card6': group 'credit' vs. reference 'debit' has SPD=0.0424.
- **[WARNING]** 1 of 1 group(s) for 'card6' show a selection-rate disparity whose 95% bootstrap CI excludes zero (statistically meaningful, not random variation): ['credit'].
- **[WARNING]** Chi Square test on the [card6 x predicted-label] contingency table: p=0.000000 (significant at alpha=0.05). Cochran's rule satisfied -- chi-square test of independence is valid.
- **[INFO]** Best-performing group for 'card6': 'credit' (F1=0.5597, recall=0.5247, precision=0.5996, n=27270).
- **[WARNING]** Worst-performing group for 'card6': 'Missing' (F1=0.3684, recall=0.4667, precision=0.3043, n=743).
- **[INFO]** Group with the highest false-positive rate for 'card6': 'credit' (FPR=0.0242, n=27270) -- legitimate transactions from this group are most often incorrectly flagged as fraud.
- **[WARNING]** Group with the highest false-negative rate for 'card6': 'debit' (FNR=0.6643, n_positive=2288) -- fraud from this group is most often missed.

## card4

- **[INFO]** Largest statistical parity disparity for 'card4': group 'discover' vs. reference 'visa' has SPD=0.0488 (95% CI [0.0348, 0.0629], statistically significant).
- **[INFO]** Smallest statistical parity disparity for 'card4': group 'mastercard' vs. reference 'visa' has SPD=0.0017.
- **[WARNING]** 1 of 3 group(s) for 'card4' show a selection-rate disparity whose 95% bootstrap CI excludes zero (statistically meaningful, not random variation): ['discover'].
- **[WARNING]** Chi Square test on the [card4 x predicted-label] contingency table: p=0.000000 (significant at alpha=0.05). Cochran's rule satisfied -- chi-square test of independence is valid.
- **[INFO]** Best-performing group for 'card4': 'mastercard' (F1=0.5140, recall=0.4537, precision=0.5930, n=38355).
- **[WARNING]** Worst-performing group for 'card4': 'Missing' (F1=0.3684, recall=0.4667, precision=0.3043, n=744).
- **[INFO]** Group with the highest false-positive rate for 'card4': 'discover' (FPR=0.0420, n=1257) -- legitimate transactions from this group are most often incorrectly flagged as fraud.
- **[WARNING]** Group with the highest false-negative rate for 'card4': 'discover' (FNR=0.6283, n_positive=113) -- fraud from this group is most often missed.

## DeviceType

- **[INFO]** Largest statistical parity disparity for 'DeviceType': group 'mobile' vs. reference 'desktop' has SPD=0.0207 (95% CI [0.0132, 0.0283], statistically significant).
- **[INFO]** Smallest statistical parity disparity for 'DeviceType': group 'mobile' vs. reference 'desktop' has SPD=0.0207.
- **[WARNING]** 1 of 1 group(s) for 'DeviceType' show a selection-rate disparity whose 95% bootstrap CI excludes zero (statistically meaningful, not random variation): ['mobile'].
- **[WARNING]** Chi Square test on the [DeviceType x predicted-label] contingency table: p=0.000000 (significant at alpha=0.05). Cochran's rule satisfied -- chi-square test of independence is valid.
- **[INFO]** Best-performing group for 'DeviceType': 'desktop' (F1=0.7079, recall=0.7153, precision=0.7005, n=13620).
- **[WARNING]** Worst-performing group for 'DeviceType': 'Missing' (F1=0.1984, recall=0.1386, precision=0.3489, n=94936).
- **[INFO]** Group with the highest false-positive rate for 'DeviceType': 'mobile' (FPR=0.0377, n=9552) -- legitimate transactions from this group are most often incorrectly flagged as fraud.
- **[WARNING]** Group with the highest false-negative rate for 'DeviceType': 'Missing' (FNR=0.8614, n_positive=1883) -- fraud from this group is most often missed.
