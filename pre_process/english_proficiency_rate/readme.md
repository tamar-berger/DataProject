# Countries English Proficiency Dataset

## Overview
This dataset combines the global list of countries with English proficiency scores taken from the **EF English Proficiency Index (EPI)**, available at:  
👉 [https://www.ef.com/wwen/epi/]

## Data Processing Steps
1. **Country Name Normalization**  
   - All country names were converted to **CamelCase** format.  

2. **Merging EF EPI Scores**  
   - Countries found in the EF dataset were matched to their normalized names.  
   - Their corresponding **EPI score** was added to the dataset.

3. **English-Speaking Countries without a Score**  
   - Some official English-speaking countries were **not included** in the EF dataset.  
   - To ensure they appear in the final file, we added them manually (e.g., `AntiguaAndBarbuda`, `SaintLucia`, `Belize`).  
   - For these countries, we assigned the **maximum score observed in the EF dataset (636)** to reflect their high English proficiency.

## Final Output
- The resulting dataset is stored in **CSV format**.  
- It includes only:  
  - Countries with an EF EPI score.  
  - English-speaking countries (with the maximum score applied if missing).
  - **Number of records: 133 countries**  


## Columns
- **`country`** — Country name in CamelCase format.  
- **`english_score`** — The English proficiency score from EF EPI (or `636` for added English-speaking countries).
