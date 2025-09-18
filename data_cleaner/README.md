# Data Cleaner Module

A comprehensive data cleaning pipeline for the Country Recommendation System that transforms raw CSV files into a standardized SQLite database suitable for machine learning algorithms.

## Overview

The Data Cleaner module processes country indicator datasets from multiple sources, standardizes country names, normalizes data values, and creates a unified database. It implements robust data cleaning strategies including winsorization, missing value imputation, and fuzzy country name matching.

**Key Features:**
- Automated CSV discovery and validation
- 3-step country name normalization (deterministic → fuzzy → rejection with suggestions)
- Tiered missing value imputation strategy
- Robust data normalization with outlier handling
- Comprehensive SQLite database with foreign key constraints
- Detailed processing reports and audit trails

## Data Processing Pipeline

### 1. **Discovery & Validation**
- Recursively scans input folder for CSV files
- Validates file structure and content quality
- Auto-detects indicator types and country columns
- Generates quality assessment reports

### 2. **Country Name Normalization**

**Strategy**: 3-step resolution ensures reproducible matching without data loss:

1. **Deterministic Mapping**: Clean string normalization (trim, lowercase, punctuation removal) against standard dictionary
2. **Fuzzy Matching**: Token-set ratio with configurable threshold (default ≥90%)
3. **Rejection Logging**: Unmatched countries logged with top 3 suggestions for dictionary expansion

**Example mappings:**
```
"United States of America" → "UnitedStates" (deterministic)
"U.S.A." → "UnitedStates" (fuzzy, score: 92)
"Nonexistent Country" → REJECTED (logged with suggestions)
```

### 3. **Missing Value Imputation**

**Tiered Strategy** based on missing data percentage:

- **≤10% missing**: Global median imputation (robust, simple)
- **10-40% missing**: Regional median (if available) or global median
- **>40% missing**: Leave as NULL, flag for recommender to handle

**Rationale**: Preserves data integrity while enabling downstream algorithms to make informed decisions about incomplete features.

### 4. **Data Normalization**

**Robust Min-Max Scaling** with outlier protection:

1. **Winsorization**: Cap values at configurable percentiles (default: 1st/99th)
2. **Scaling**: `norm = (x - p1) / (p99 - p1)`, clipped to [0,1]
3. **Directional Correction**: Invert "lower is better" indicators (crime, cost of living)

**Outlier Policy**: Bounded normalization prevents extreme values from dominating similarity calculations while maintaining meaningful variance.

### 5. **Database Creation**

**Schema Design**:
```sql
-- Normalized structure with foreign key constraints
CREATE TABLE countries (
    country_id INTEGER PRIMARY KEY,
    country_name TEXT UNIQUE NOT NULL
);

CREATE TABLE indicators (
    country_id INTEGER PRIMARY KEY,
    crime_index REAL,
    safety_index REAL,
    english_score REAL,
    health_care_index REAL,
    cost_of_living_index REAL,
    cultural_accessibility_score REAL,
    public_transport_quality REAL,
    tourism_arrivals REAL,
    natural_spaces_index REAL,
    FOREIGN KEY (country_id) REFERENCES countries(country_id)
);
```

**Indices**: Optimized for recommendation queries with indices on country names and key indicators.

## Installation & Dependencies

```bash
# Required packages
pip install pandas numpy sqlite3 fuzzywuzzy python-levenshtein

# For enhanced string matching performance
pip install python-levenshtein-wheels
```

## Usage

### Command Line Interface

**Basic Usage:**
```bash
# Process CSV files into database
python -m data_cleaner.cli \
    --input /path/to/csv/folder \
    --output countries.db \
    --countries pre_process/all_countries_dict.py
```

**Advanced Configuration:**
```bash
# Custom winsorization and fuzzy matching settings
python -m data_cleaner.cli \
    --input pre_process/ \
    --output cleaned_countries.db \
    --countries pre_process/all_countries_dict.py \
    --winsor-lower 2.5 \
    --winsor-upper 97.5 \
    --fuzzy-threshold 85 \
    --log-level DEBUG \
    --log-file cleaning.log \
    --report-json report.json \
    --report-text summary.txt
```

**Validation Only:**
```bash
# Validate CSV files without processing
python -m data_cleaner.cli --input pre_process/ --validate-only
```

**Database Operations:**
```bash
# Export processed data to CSV
python -m data_cleaner.cli --export-db countries.db --export-csv analysis_data.csv

# Show database information
python -m data_cleaner.cli --db-info countries.db
```

### Python API

```python
from data_cleaner import DataCleaner
from pre_process.all_countries_dict import countries

# Initialize cleaner
cleaner = DataCleaner(
    country_dict=countries,
    output_db_path="countries.db",
    winsor_percentiles=(1.0, 99.0),
    fuzzy_threshold=90
)

# Process all files
results = cleaner.process_all_files(
    input_folder="pre_process/",
    log_level="INFO"
)

# Save detailed reports
cleaner.save_report("cleaning_report.json", format="json")
cleaner.save_report("cleaning_summary.txt", format="text")
```

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `winsor_lower` | 1.0 | Lower percentile for outlier capping |
| `winsor_upper` | 99.0 | Upper percentile for outlier capping |
| `fuzzy_threshold` | 90 | Minimum fuzzy match score (0-100) |
| `log_level` | INFO | Logging verbosity (DEBUG/INFO/WARNING/ERROR) |

## Output Structure

### Database Tables
- **`countries`**: Normalized country names with unique IDs
- **`indicators`**: All country indicators with foreign key relationships
- **`processing_log`**: Audit trail of all processing operations

### Reports
- **JSON Report**: Complete processing statistics, validation results, and configuration
- **Text Report**: Human-readable summary with key metrics and data quality indicators
- **Rejection Log**: Unmatched countries with fuzzy match suggestions for dictionary expansion

## Extending the System

### Adding New CSV Files
1. Place CSV in input folder with country column and numeric indicators
2. Module automatically detects and processes new files
3. Column names are fuzzy-matched to standard indicator names

### Adding New Indicators
1. **Update Schema**: Add new column to `indicator_columns` in `database.py`
2. **Update Normalization**: Add directional mapping in `normalizers.py` if "lower is better"
3. **Update CLI**: No changes needed - automatic detection and processing

### Custom Country Mappings
1. **Extend Dictionary**: Add entries to `all_countries_dict.py`
2. **Review Rejections**: Check processing reports for suggested matches
3. **Iterative Improvement**: Use fuzzy suggestions to expand dictionary coverage

## Data Quality Guarantees

- **No Silent Data Loss**: All unmatched countries logged with suggestions
- **Reproducible Processing**: Deterministic normalization with detailed configuration logging
- **Audit Trail**: Complete processing history in database logs
- **Integrity Validation**: Foreign key constraints and completeness verification
- **Bounded Normalization**: All indicators scaled to [0,1] with consistent direction

## Performance Characteristics

- **Memory Efficient**: Streaming processing for large datasets
- **Fast Queries**: Optimized indices for recommendation algorithms
- **Batch Operations**: Efficient bulk insertions with transaction management
- **Scalable**: Handles hundreds of countries and multiple indicators efficiently

## Error Handling

- **Graceful Degradation**: Individual file failures don't stop pipeline
- **Comprehensive Logging**: All errors logged with context and suggestions
- **Recovery Options**: Partial processing results preserved and reportable
- **Validation Gates**: Multiple validation steps prevent corrupted data propagation