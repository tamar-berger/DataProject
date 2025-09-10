# Cost of Living Dataset (CamelCase Countries)

## Overview
This dataset contains cost of living indices by country.  
The original data was taken from:  
👉 [https://www.numbeo.com/cost-of-living/rankings_by_country.jsp]

## Data Processing Steps
1. **Country Name Normalization**  
   - All country names were converted to **CamelCase** format.  

2. **Final Output**  
   - The dataset is stored as a **CSV file**.  
   - The first column `country` contains the normalized country names.  
   - All other columns are preserved from the original Numbeo dataset.
   - **Number of records: 143 countries**  


## Columns
- **`country`** — Country name in CamelCase format  
- Other columns — Original cost of living indices and rankings from Numbeo

