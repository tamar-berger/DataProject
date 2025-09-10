 # Countries Crime Index Dataset

## Overview

This dataset combines the global list of countries with crime and safety
scores from the **Numbeo Crime Index (2025 Mid-Year)**, available at: <https://www.numbeo.com/crime/rankings_by_country.jsp>

## Data Processing Steps

1.  **Country Name Normalization**
    -   All country names were converted to **CamelCase** format,
        matching the standardized dictionary.
2.  **Merging Crime and Safety Index Scores**
    -   Countries found in the Numbeo dataset were matched to their
        normalized names.\
    -   Their corresponding **Crime Index** and **Safety Index** scores
        were added to the dataset.

## Final Output

-   The resulting dataset is stored in **CSV format**.\
-   It includes:
    -   Countries with crime and safety scores.\
    -   Corrected and standardized names to ensure full consistency.\
-   **Number of records: 148 countries.**

## Columns

-   **`country`** --- Country name in CamelCase format.\
-   **`crime_index`** --- The Numbeo Crime Index score (2025 Mid-Year).\
-   **`safety_index`** --- The Numbeo Safety Index score (2025 Mid-Year).
