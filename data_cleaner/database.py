"""
Database Management Module

Handles:
1. SQLite database creation and schema management
2. Data insertion with foreign key constraints
3. Index creation for performance
4. Database validation and integrity checks
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages SQLite database operations for country indicator data.
    
    Creates normalized schema with countries and indicators tables,
    handles data insertion with proper foreign key relationships,
    and provides validation and query capabilities.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection = None
        
        # Define schema for single country_indicators table
        self.indicator_columns = {
            'country_id': 'INTEGER',
            'country_name': 'TEXT',
            'crime_rate': 'REAL',
            'safety_rate': 'REAL',
            'english_score_rate': 'REAL',
            'health_care_rate': 'REAL',
            'cost_of_living_rate': 'REAL',
            'cultural_accessibility_rate': 'REAL',
            'public_transport_rate': 'REAL',
            'tourism_arrivals_rate': 'REAL',
            'natural_spaces_rate': 'REAL'
        }
        
        # Single table name
        self.table_name = "country_indicators"
        
        # Track database statistics
        self.db_stats = {}
    
    def connect(self) -> sqlite3.Connection:
        """
        Establish database connection with foreign key support.
        
        Returns:
            SQLite connection object
        """
        if self.connection is None:
            self.connection = sqlite3.connect(str(self.db_path))
            # Enable foreign key constraints
            self.connection.execute("PRAGMA foreign_keys = ON")
            # Enable WAL mode for better performance
            self.connection.execute("PRAGMA journal_mode = WAL")
            logger.info(f"Connected to database: {self.db_path}")
        
        return self.connection
    
    def disconnect(self):
        """Close database connection safely."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def create_schema(self, drop_existing: bool = False):
        """
        Create single country_indicators table schema.
        
        Args:
            drop_existing: Whether to drop existing tables first
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # Drop existing tables if requested
            if drop_existing:
                cursor.execute(f"DROP TABLE IF EXISTS {self.table_name}")
                cursor.execute("DROP TABLE IF EXISTS indicators")  # Legacy
                cursor.execute("DROP TABLE IF EXISTS countries")   # Legacy
                cursor.execute("DROP TABLE IF EXISTS processing_log")
                logger.info("Dropped existing tables")
            
            # Build single table creation SQL with NOT NULL constraints
            column_definitions = []
            for col_name, col_type in self.indicator_columns.items():
                if col_name == 'country_id':
                    column_definitions.append(f"{col_name} {col_type} PRIMARY KEY NOT NULL")
                elif col_name == 'country_name':
                    column_definitions.append(f"{col_name} {col_type} NOT NULL")
                else:
                    column_definitions.append(f"{col_name} {col_type} NOT NULL")
            
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    {', '.join(column_definitions)},
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create processing log table for audit trail
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    process_type TEXT NOT NULL,
                    filename TEXT,
                    records_processed INTEGER,
                    records_inserted INTEGER,
                    records_rejected INTEGER,
                    processing_time_seconds REAL,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            self._create_indexes(cursor)
            
            conn.commit()
            logger.info(f"Single table schema created successfully: {self.table_name}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create schema: {str(e)}")
            raise
    
    def _create_indexes(self, cursor: sqlite3.Cursor):
        """
        Create database indexes for optimal query performance.
        
        Args:
            cursor: SQLite cursor object
        """
        # Index on country_name for fast lookups
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_name 
            ON {self.table_name}(country_name)
        """)
        
        # Indexes on common indicator columns for filtering
        important_indicators = ['crime_rate', 'safety_rate', 'english_score_rate', 'health_care_rate']
        for indicator in important_indicators:
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_{indicator} 
                ON {self.table_name}({indicator})
            """)
        
        # Composite index for multi-column queries
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_multi 
            ON {self.table_name}(crime_rate, english_score_rate, health_care_rate)
        """)
        
        # Index on processing log for audit queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_processing_log_created_at 
            ON processing_log(created_at)
        """)
        
        logger.debug("Database indexes created")
    
    def insert_country_indicators_batch(self, indicators_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Insert complete country indicators into single table with comprehensive imputation.
        
        Args:
            indicators_df: DataFrame with country and indicator columns
            
        Returns:
            Dictionary with insertion statistics
        """
        logger.info(f"Inserting {len(indicators_df)} country indicator records")
        
        # Add comprehensive imputation
        df_clean = self._apply_comprehensive_imputation(indicators_df.copy())
        
        # Add country_id as auto-incrementing integer
        df_clean = df_clean.reset_index(drop=True)
        df_clean['country_id'] = df_clean.index + 1
        
        # Rename columns to match schema
        df_clean = self._standardize_column_names(df_clean)
        
        conn = self.connect()
        cursor = conn.cursor()
        
        # Statistics tracking
        records_processed = len(df_clean)
        records_inserted = 0
        records_rejected = 0
        
        try:
            # Build parameterized insert SQL
            columns = list(self.indicator_columns.keys())
            placeholders = ', '.join(['?' for _ in columns])
            
            insert_sql = f"""
                INSERT OR REPLACE INTO {self.table_name} 
                ({', '.join(columns)}, updated_at)
                VALUES ({placeholders}, CURRENT_TIMESTAMP)
            """
            
            # Insert all records
            for _, row in df_clean.iterrows():
                try:
                    values = [row.get(col) for col in columns]
                    cursor.execute(insert_sql, values)
                    records_inserted += 1
                except Exception as row_error:
                    records_rejected += 1
                    logger.error(f"Failed to insert row for {row.get('country_name', 'unknown')}: {row_error}")
            
            conn.commit()
            
            # Log processing results
            self._log_processing_result(
                cursor, 'single_table_insert', 'merged_dataset',
                records_processed, records_inserted, records_rejected
            )
            conn.commit()
            
            logger.info(f"Successfully inserted {records_inserted}/{records_processed} records")
            
        except Exception as e:
            conn.rollback()
            error_msg = f"Batch insert failed: {str(e)}"
            logger.error(error_msg)
            raise
        
        return {
            'records_processed': records_processed,
            'records_inserted': records_inserted,
            'records_rejected': records_rejected
        }
    
    def _apply_comprehensive_imputation(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply comprehensive imputation to eliminate all NULL values.
        
        Args:
            df: DataFrame with potential NULL values
            
        Returns:
            DataFrame with no NULL values
        """
        logger.info("Applying comprehensive imputation to eliminate NULLs")
        
        df_imputed = df.copy()
        
        # Get all numeric columns (exclude country)
        numeric_columns = [col for col in df.columns if col != 'country' and df[col].dtype in ['float64', 'int64']]
        
        for column in numeric_columns:
            missing_count = df_imputed[column].isna().sum()
            
            if missing_count > 0:
                # Calculate median for imputation
                median_value = df_imputed[column].median()
                
                # If median is NaN (all values missing), use reasonable defaults
                if pd.isna(median_value):
                    if 'tourism' in column.lower():
                        median_value = 0.0  # No tourism arrivals
                    elif 'natural' in column.lower():
                        median_value = 0.1  # Minimal natural spaces
                    else:
                        median_value = 0.5  # Neutral middle value
                
                # Fill missing values
                df_imputed[column] = df_imputed[column].fillna(median_value)
                logger.info(f"Imputed {missing_count} values in {column} with {median_value:.3f}")
        
        # Verify no NULLs remain
        remaining_nulls = df_imputed.isnull().sum().sum()
        if remaining_nulls > 0:
            raise ValueError(f"CRITICAL: {remaining_nulls} NULL values remain after imputation")
        
        return df_imputed
    
    def _standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize column names to match target schema.
        
        Args:
            df: DataFrame with original column names
            
        Returns:
            DataFrame with standardized column names
        """
        # Column mapping from original to target schema
        column_mapping = {
            'country': 'country_name',
            'crime_index': 'crime_rate',
            'safety_index': 'safety_rate',
            'english_score': 'english_score_rate',
            'health_care_index': 'health_care_rate',
            'cost_of_living_index': 'cost_of_living_rate',
            'cultural_accessibility_score': 'cultural_accessibility_rate',
            'public_transport_quality': 'public_transport_rate',
            'tourism_arrivals': 'tourism_arrivals_rate',
            'natural_spaces_index': 'natural_spaces_rate'
        }
        
        # Apply mapping
        df_renamed = df.copy()
        rename_dict = {}
        
        for original_col in df.columns:
            if original_col in column_mapping:
                rename_dict[original_col] = column_mapping[original_col]
        
        if rename_dict:
            df_renamed = df_renamed.rename(columns=rename_dict)
            logger.debug(f"Renamed columns: {rename_dict}")
        
        return df_renamed
    
    
    
    def _log_processing_result(self, cursor: sqlite3.Cursor, process_type: str,
                              filename: str, processed: int, inserted: int, 
                              rejected: int, error_message: str = None):
        """
        Log processing results for audit trail.
        
        Args:
            cursor: SQLite cursor
            process_type: Type of processing operation
            filename: Source filename
            processed: Number of records processed
            inserted: Number of records inserted
            rejected: Number of records rejected
            error_message: Error message if any
        """
        cursor.execute("""
            INSERT INTO processing_log 
            (process_type, filename, records_processed, records_inserted, 
             records_rejected, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (process_type, filename, processed, inserted, rejected, error_message))
    
    def validate_database_integrity(self) -> Dict[str, Any]:
        """
        Validate single table database integrity and generate statistics.
        
        Returns:
            Dictionary with validation results and statistics
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # Basic table counts
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            total_records = cursor.fetchone()[0]
            
            # Check for NULL values (should be zero)
            null_checks = {}
            for indicator in self.indicator_columns.keys():
                if indicator not in ['country_id', 'country_name']:
                    cursor.execute(f"SELECT COUNT(*) FROM {self.table_name} WHERE {indicator} IS NULL")
                    null_count = cursor.fetchone()[0]
                    null_checks[indicator] = null_count
            
            total_nulls = sum(null_checks.values())
            
            # Calculate data completeness (should be 100%)
            completeness_stats = {}
            for indicator in self.indicator_columns.keys():
                if indicator not in ['country_id', 'country_name']:
                    cursor.execute(f"""
                        SELECT 
                            COUNT(*) as total,
                            COUNT({indicator}) as non_null,
                            ROUND(CAST(COUNT({indicator}) AS FLOAT) / COUNT(*) * 100, 2) as completeness_pct
                        FROM {self.table_name}
                    """)
                    result = cursor.fetchone()
                    completeness_stats[indicator] = {
                        'total_records': result[0],
                        'non_null_records': result[1],
                        'completeness_percentage': result[2]
                    }
            
            # Get processing log summary
            cursor.execute("""
                SELECT 
                    process_type,
                    COUNT(*) as operation_count,
                    SUM(records_processed) as total_processed,
                    SUM(records_inserted) as total_inserted,
                    SUM(records_rejected) as total_rejected
                FROM processing_log 
                GROUP BY process_type
            """)
            
            processing_summary = {}
            for row in cursor.fetchall():
                processing_summary[row[0]] = {
                    'operation_count': row[1],
                    'total_processed': row[2],
                    'total_inserted': row[3],
                    'total_rejected': row[4]
                }
            
            validation_result = {
                'database_path': str(self.db_path),
                'total_records': total_records,
                'null_value_check': {
                    'total_nulls': total_nulls,
                    'null_counts_per_column': null_checks,
                    'zero_null_compliance': total_nulls == 0
                },
                'data_completeness': completeness_stats,
                'processing_summary': processing_summary,
                'integrity_status': 'valid' if total_nulls == 0 else 'invalid',
                'validation_timestamp': pd.Timestamp.now().isoformat()
            }
            
            self.db_stats = validation_result
            return validation_result
            
        except Exception as e:
            logger.error(f"Database validation failed: {str(e)}")
            return {
                'validation_status': 'error',
                'error_message': str(e)
            }
    
    def export_data_for_analysis(self, output_path: str = None) -> pd.DataFrame:
        """
        Export complete dataset for analysis and modeling.
        
        Args:
            output_path: Optional path to save CSV file
            
        Returns:
            DataFrame with countries and all indicators
        """
        conn = self.connect()
        
        # Build comprehensive query for single table
        query = f"""
            SELECT 
                {', '.join(self.indicator_columns.keys())}
            FROM {self.table_name}
            ORDER BY country_name
        """
        
        df = pd.read_sql_query(query, conn)
        
        if output_path:
            df.to_csv(output_path, index=False)
            logger.info(f"Data exported to: {output_path}")
        
        return df
    
    def get_database_summary(self) -> str:
        """
        Generate human-readable database summary.
        
        Returns:
            Formatted string with database statistics
        """
        if not self.db_stats:
            self.validate_database_integrity()
        
        stats = self.db_stats
        
        summary = f"""
Database Summary: {stats['database_path']}
=====================================
Total Records: {stats['total_records']}
Integrity Status: {stats['integrity_status']}
NULL Values: {stats['null_value_check']['total_nulls']}

Data Completeness:
"""
        
        for indicator, comp_stats in stats['data_completeness'].items():
            summary += f"  {indicator}: {comp_stats['completeness_percentage']}% ({comp_stats['non_null_records']}/{comp_stats['total_records']})\n"
        
        if stats['processing_summary']:
            summary += "\nProcessing History:\n"
            for process_type, proc_stats in stats['processing_summary'].items():
                summary += f"  {process_type}: {proc_stats['total_inserted']} inserted, {proc_stats['total_rejected']} rejected\n"
        
        return summary