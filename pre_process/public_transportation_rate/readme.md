# Countries Public Transport Quality Dataset

## Overview

This dataset combines the global list of countries with public transport quality
scores from the **Global Economy Railroad Quality Ranking**, available at: <https://www.theglobaleconomy.com/rankings/railroad_quality/?utm_source=chatgpt.com>

## Data Processing Steps

1.  **Country Name Normalization**
    -   All country names were converted to **CamelCase** format,
        matching the standardized dictionary.

2.  **Merging Public Transport Scores**
    -   Countries found in the Global Economy dataset were matched to their normalized names.
    -   Their corresponding **Railroad Quality** scores were added to the dataset.

## Final Output

-   The resulting dataset is stored in **CSV format**.  
-   It includes:
    -   Countries with public transport quality scores.  
    -   Corrected and standardized names to ensure full consistency.  
-   **Number of records: 100 countries.**

## Columns

-   **`country`** — Country name in CamelCase format.  
-   **`public_transport_quality`** — The Global Economy Railroad Quality score (1 decimal place).  
