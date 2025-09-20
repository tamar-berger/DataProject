# Countries Natural Spaces Index Dataset

## Overview

This dataset combines the global list of countries with an environmental  
indicator describing **access to natural and protected areas**, based on  
the **World Database on Protected Areas (WDPA)**, available at:  
<https://www.protectedplanet.net/en/thematic-areas/wdpa?tab=WDPA>

## Data Processing Steps

1.  **Country Name Normalization**  
    -   All country names were converted to **CamelCase** format,  
        matching the standardized dictionary.  

2.  **Merging Natural Spaces Index**  
    -   Countries found in the WDPA dataset were matched to their  
        normalized names.  
    -   Their corresponding **Natural Spaces Index** scores were added  
        to the dataset.  

## Final Output

-   The resulting dataset is stored in **CSV format**.  
-   It includes:  
    -   Countries with natural spaces scores.  
    -   Corrected and standardized names to ensure full consistency.  
-   **Number of records: 176 countries.**

## Columns

-   **`country`** — Country name in CamelCase format.  
-   **`natural_spaces_index`** — Index score from WDPA representing  
    access to natural and protected areas.  
