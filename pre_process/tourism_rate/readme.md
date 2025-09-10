# Countries International Tourism Dataset

## Overview

This dataset combines the global list of countries with **International
Tourism Arrivals (2020)**, available at: <https://data.worldbank.org/indicator/ST.INT.ARVL?end=2020&most_recent_value_desc=false&start=2020&view=bar>

## Data Processing Steps

1.  **Removing Year Column**  
    -   The year column was dropped, leaving only the country name and
        the tourism arrivals value.

2.  **Country Name Normalization**  
    -   All country names were converted to **CamelCase** format,
        matching the standardized dictionary.


## Final Output

-   The resulting dataset is stored in **CSV format**.  
-   It includes:  
    -   Countries with international tourism arrival values (2020).  
    -   Corrected and standardized names to ensure full consistency.  
-   **Number of records: 183 countries.**

## Columns

-   **`country`** - Country name in CamelCase format.  
-   **`tourism_arrivals`** - The number of international tourism arrivals
    (2020, World Bank).
