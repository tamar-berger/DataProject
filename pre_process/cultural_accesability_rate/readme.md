# Countries Cultural Accessibility Dataset

## Overview
This dataset combines the global list of countries with cultural accessibility scores taken from the **2024 Cultural Accessibility Report**, available at: <https://data360.worldbank.org/en/indicator/WEF_TTDI_TTDI_D_13?view=bar>  

## Data Processing Steps
1. **Country Name Normalization**  
   - All country names were converted to **CamelCase** format, matching the standardized dictionary.  

2. **Merging Cultural Accessibility Scores**  
   - Countries found in the cultural accessibility dataset were matched to their normalized names.  
   - Their corresponding **cultural accessibility score** was added to the dataset.  

## Final Output
- The resulting dataset is stored in **CSV format**.  
- It includes:  
  - Countries with a cultural accessibility score.  
  - Corrected and standardized names to ensure consistency.  
- **Number of records: 117 countries**  

## Columns
- **`country`** — Country name in CamelCase format.  
- **`cultural_accessibility_score`** — The cultural accessibility score from the 2024 dataset.  
