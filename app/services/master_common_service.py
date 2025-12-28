import pandas as pd
from io import BytesIO
from typing import List, Dict, Any, Set
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status, UploadFile
from app.core.logging import get_logger
from app.models.project_category_master import ProjectCategoryMaster
from app.models.project_stage_master import ProjectStageMaster
from app.models.funding_type_master import FundingTypeMaster
from app.models.mode_of_implementation_master import ModeOfImplementationMaster
from app.models.ownership_master import OwnershipMaster

from app.schemas.master import (
    ProjectCategoryMasterResponse,
    ProjectStageMasterResponse,
    FundingTypeMasterResponse,
    ModeOfImplementationMasterResponse,
    OwnershipMasterResponse,
)

logger = get_logger("services.master_common")


class MasterCommonService:
    """Service for common operations on master tables"""
    
    # Columns that are auto-generated or should not be set from Excel
    EXCLUDED_COLUMNS = {"id", "created_at", "updated_at"}
    
    # Mapping of table names to their models and response schemas
    TABLE_MAPPING = {
        "funding_type_master": {
            "model": FundingTypeMaster,
            "response_schema": FundingTypeMasterResponse
        },
        "mode_of_implementation_master": {
            "model": ModeOfImplementationMaster,
            "response_schema": ModeOfImplementationMasterResponse
        },
        "ownership_master": {
            "model": OwnershipMaster,
            "response_schema": OwnershipMasterResponse
        },
        "project_category_master": {
            "model": ProjectCategoryMaster,
            "response_schema": ProjectCategoryMasterResponse
        },
        "project_stage_master": {
            "model": ProjectStageMaster,
            "response_schema": ProjectStageMasterResponse
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def _validate_table_name(self, table_name: str) -> Dict[str, Any]:
        """Validate table name and return table configuration"""
        if table_name not in self.TABLE_MAPPING:
            valid_tables = ", ".join(self.TABLE_MAPPING.keys())
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid table name '{table_name}'. Valid tables are: {valid_tables}"
            )
        return self.TABLE_MAPPING[table_name]
    
    def _get_model_columns(self, model) -> Set[str]:
        """
        Get all valid column names from a SQLAlchemy model dynamically.
        Excludes auto-generated columns like id, created_at, updated_at.
        
        Args:
            model: SQLAlchemy model class
            
        Returns:
            Set of valid column names that can be set from Excel
        """
        mapper = inspect(model)
        all_columns = {column.key for column in mapper.columns}
        # Return only columns that are not excluded
        return all_columns - self.EXCLUDED_COLUMNS
    
    def get_all_by_table_name(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Generic method to get all records from a master table by table name.
        
        Args:
            table_name: Name of the master table
            
        Returns:
            List of records as dictionaries
        """
        table_config = self._validate_table_name(table_name)
        model = table_config["model"]
        response_schema = table_config["response_schema"]
        
        try:
            records = self.db.query(model).order_by(model.id).all()
            return [response_schema.model_validate(record).model_dump() for record in records]
        except Exception as e:
            logger.error(f"Error fetching records from {table_name}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch records from {table_name}: {str(e)}"
            )
    
    def bulk_insert_from_excel(
        self, 
        table_name: str, 
        file: UploadFile, 
        created_by: str = None
    ) -> Dict[str, Any]:
        """
        Bulk insert records from Excel file into the specified master table.
        Fields are read dynamically from Excel - any column in Excel that matches
        a database column will be inserted. No code changes needed when adding new columns.
        
        Args:
            table_name: Name of the master table
            file: Uploaded Excel file
            created_by: User who created the records (optional, used if not in Excel)
            
        Returns:
            Dictionary with insertion results
        """
        table_config = self._validate_table_name(table_name)
        model = table_config["model"]
        
        # Get valid database columns dynamically
        valid_db_columns = self._get_model_columns(model)
        
        # Validate file extension
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only Excel files (.xlsx, .xls) are allowed."
            )
        
        try:
            # Read Excel file
            contents = file.file.read()
            df = pd.read_excel(BytesIO(contents))
            
            # Get columns from Excel (convert to lowercase for case-insensitive matching)
            excel_columns = set(df.columns.str.strip().str.lower())
            valid_db_columns_lower = {col.lower() for col in valid_db_columns}
            
            # Find columns that exist in both Excel and database
            matching_columns = excel_columns & valid_db_columns_lower
            
            if not matching_columns:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No matching columns found between Excel file and database table. "
                           f"Valid database columns are: {', '.join(sorted(valid_db_columns))}"
                )
            
            # Create mapping from Excel column names (case-insensitive) to database column names
            column_mapping = {}
            for excel_col in df.columns:
                excel_col_lower = excel_col.strip().lower()
                if excel_col_lower in valid_db_columns_lower:
                    # Find the actual database column name (preserve case)
                    db_col = next((col for col in valid_db_columns if col.lower() == excel_col_lower), None)
                    if db_col:
                        column_mapping[excel_col] = db_col
            
            # Check if 'value' column exists (critical field for master tables)
            value_column = None
            for excel_col, db_col in column_mapping.items():
                if db_col.lower() == 'value':
                    value_column = excel_col
                    break
            
            if not value_column:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Excel file must contain a 'value' column (case-insensitive). "
                           f"Found columns: {', '.join(df.columns.tolist())}"
                )
            
            # Prepare records for insertion
            errors = []
            success_count = 0
            skipped_count = 0
            
            for index, row in df.iterrows():
                try:
                    # Create record data dynamically from Excel columns
                    record_data = {}
                    
                    # Process all matching columns from Excel
                    for excel_col, db_col in column_mapping.items():
                        value = row[excel_col]
                        
                        # Handle NaN values - skip if NaN (allow optional fields)
                        if pd.isna(value):
                            # Only raise error if it's the 'value' field (required)
                            if db_col.lower() == 'value':
                                raise ValueError(f"Required field 'value' is empty in row {index + 2}")
                            continue
                        
                        # Convert value to string and strip whitespace
                        record_data[db_col] = str(value).strip() if value else None
                    
                    # Set created_by if provided and not in Excel
                    if 'created_by' not in record_data and created_by:
                        record_data['created_by'] = created_by
                    
                    # Check for duplicate value (unique constraint)
                    value_to_check = record_data.get('value')
                    if value_to_check:
                        existing = self.db.query(model).filter(model.value == value_to_check).first()
                        if existing:
                            skipped_count += 1
                            errors.append(f"Row {index + 2}: Value '{value_to_check}' already exists (skipped)")
                            continue
                    
                    # Create new record
                    new_record = model(**record_data)
                    self.db.add(new_record)
                    success_count += 1
                    
                except ValueError as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            # Commit all records
            if success_count > 0:
                try:
                    self.db.commit()
                    logger.info(f"Successfully inserted {success_count} records into {table_name}")
                except IntegrityError as e:
                    self.db.rollback()
                    logger.error(f"Integrity error while inserting into {table_name}: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Database integrity error: {str(e)}"
                    )
            
            return {
                "total_rows": len(df),
                "success_count": success_count,
                "skipped_count": skipped_count,
                "error_count": len(errors),
                "errors": errors if errors else None,
                "columns_processed": list(column_mapping.values())
            }
            
        except HTTPException:
            raise
        except pd.errors.EmptyDataError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Excel file is empty"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing Excel file for {table_name}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process Excel file: {str(e)}"
            )
    
    def delete_all_by_table_name(self, table_name: str) -> Dict[str, Any]:
        """
        Generic method to delete all records from a master table by table name.
        
        Args:
            table_name: Name of the master table
            
        Returns:
            Dictionary with deletion results including count of deleted records
        """
        table_config = self._validate_table_name(table_name)
        model = table_config["model"]
        
        try:
            # Get count of records before deletion
            record_count = self.db.query(model).count()
            
            if record_count == 0:
                logger.info(f"No records found in {table_name} to delete")
                return {
                    "deleted_count": 0,
                    "message": f"No records found in {table_name}"
                }
            
            # Delete all records
            deleted_count = self.db.query(model).delete()
            self.db.commit()
            
            logger.info(f"Successfully deleted {deleted_count} records from {table_name}")
            
            return {
                "deleted_count": deleted_count,
                "message": f"Successfully deleted {deleted_count} record(s) from {table_name}"
            }
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error while deleting from {table_name}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete records from {table_name}. Some records are referenced by other tables. "
                       f"Original error: {str(e)}"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting records from {table_name}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete records from {table_name}: {str(e)}"
            )

