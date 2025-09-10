# Countries Health Care Index Dataset

## Overview

This dataset combines the global list of countries with health care
quality scores from the **Numbeo Health Care Index (2025 Mid‑Year)**,
available at:\
👉 <https://www.numbeo.com/health-care/rankings_by_country.jsp>

## Data Processing Steps

1.  **Country Name Normalization**
    -   All country names were converted to **CamelCase** format,
        matching the standardized dictionary.
2.  **Merging Health Care Index Scores**
    -   Countries found in the Numbeo dataset were matched to their
        normalized names.\
    -   Their corresponding **Health Care Index** score was added to the
        dataset.

## Final Output

-   The resulting dataset is stored in **CSV format**.\
-   It includes:
    -   Countries with a health care quality score.\
    -   Corrected and standardized names to ensure full consistency.\
-   **Number of records: 96 countries.**

## Columns

-   **`country`** - Country name in CamelCase format.\
-   **`health_care_index`** - The Numbeo Health Care Index score (2025
    Mid‑Year).
>>>>>>> 3c5fcaed838de9384a5034be067c1455035a6357
