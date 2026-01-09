import pandas as pd
from io import BytesIO
from typing import List, Dict, Any, Set, Type
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status, UploadFile
from app.core.logging import get_logger
from app.core.database import Base
from app.models.master_table_list import MasterTableList

logger = get_logger("services.master_common")


class MasterCommonService:
    """Service for common operations on master tables - fully dynamic based on master_table_list"""
    
    # Columns that are auto-generated or should not be set from Excel
    EXCLUDED_COLUMNS = {"id", "created_at", "updated_at"}
    
    def __init__(self, db: Session):
        self.db = db
    
    def _validate_table_exists_in_list(self, table_name: str) -> None:
        """
        Validate that the table name exists in master_table_list.
        
        Args:
            table_name: Name of the master table
            
        Raises:
            HTTPException: If table name is not found in master_table_list
        """
        table_record = self.db.query(MasterTableList).filter(
            MasterTableList.table_name == table_name
        ).first()
        
        if not table_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table '{table_name}' not found in master table list. "
                       f"Please add it to master_table_list first."
            )
    
    def _get_model_by_table_name(self, table_name: str) -> Type:
        """
        Dynamically get model class by table name from SQLAlchemy registry.
        
        Args:
            table_name: Name of the database table
            
        Returns:
            SQLAlchemy model class
            
        Raises:
            HTTPException: If model is not found
        """
        # First validate table exists in master_table_list
        self._validate_table_exists_in_list(table_name)
        
        # Search through all registered models in SQLAlchemy registry
        for mapper in Base.registry.mappers:
            model_class = mapper.class_
            # Check if this model's table name matches
            if hasattr(model_class, '__tablename__') and model_class.__tablename__ == table_name:
                return model_class
        
        # If not found, raise exception
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model for table '{table_name}' not found in SQLAlchemy registry. "
                   f"Ensure the model is properly imported and registered."
        )
    
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
    
    def _get_required_columns(self, model) -> Set[str]:
        """
        Get all required (non-nullable) column names from a SQLAlchemy model dynamically.
        Excludes auto-generated columns like id, created_at, updated_at.
        
        Args:
            model: SQLAlchemy model class
            
        Returns:
            Set of required column names that must be provided
        """
        mapper = inspect(model)
        required_columns = {
            column.key for column in mapper.columns 
            if not column.nullable and column.key not in self.EXCLUDED_COLUMNS
        }
        return required_columns
    
    def get_all_by_table_name(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Generic method to get all records from a master table by table name.
        Dynamically discovers the model from SQLAlchemy registry.
        
        Args:
            table_name: Name of the master table
            
        Returns:
            List of records as dictionaries
        """
        try:
            # Dynamically get model class
            model = self._get_model_by_table_name(table_name)
            
            # Query all records
            records = self.db.query(model).order_by(model.id).all()
            
            # Convert records to dictionaries dynamically
            result = []
            mapper = inspect(model)
            for record in records:
                record_dict = {}
                for column in mapper.columns:
                    record_dict[column.key] = getattr(record, column.key)
                result.append(record_dict)
            
            return result
            
        except HTTPException:
            raise
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
        Model is discovered dynamically from SQLAlchemy registry.
        
        Args:
            table_name: Name of the master table
            file: Uploaded Excel file
            created_by: User who created the records (optional, used if not in Excel)
            
        Returns:
            Dictionary with insertion results
        """
        try:
            # Dynamically get model class
            model = self._get_model_by_table_name(table_name)
        except HTTPException:
            raise
        
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
            
            # Get required (non-nullable) columns dynamically from the model
            required_columns = self._get_required_columns(model)
            required_columns_lower = {col.lower() for col in required_columns}
            
            # Check if all required columns are present in Excel
            mapped_db_columns_lower = {db_col.lower() for db_col in column_mapping.values()}
            missing_required_columns = required_columns_lower - mapped_db_columns_lower
            
            if missing_required_columns:
                # Find the actual column names (preserve case) for error message
                missing_columns = [
                    next((col for col in required_columns if col.lower() == missing_lower), missing_lower)
                    for missing_lower in missing_required_columns
                ]
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Excel file must contain all required columns: {', '.join(sorted(missing_columns))}. "
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
                            # Check if this is a required field
                            if db_col.lower() in required_columns_lower:
                                raise ValueError(f"Required field '{db_col}' is empty in row {index + 2}")
                            continue
                        
                        # Convert value to string and strip whitespace
                        record_data[db_col] = str(value).strip() if value else None
                    
                    # Set created_by if provided and not in Excel
                    if 'created_by' not in record_data and created_by:
                        record_data['created_by'] = created_by
                    
                    # Check for duplicates based on unique constraints
                    # Try to find a unique identifier field (commonly 'value' for master tables)
                    # If 'value' exists, use it; otherwise, check if there's a unique constraint
                    unique_check_field = None
                    if 'value' in record_data:
                        unique_check_field = 'value'
                    elif hasattr(model, 'value'):
                        # Model has value field but it's not in Excel data
                        pass
                    else:
                        # For tables without 'value', check if there are unique constraints
                        # We'll let the database handle unique constraint violations
                        pass
                    
                    if unique_check_field and record_data.get(unique_check_field):
                        value_to_check = record_data[unique_check_field]
                        if hasattr(model, unique_check_field):
                            existing = self.db.query(model).filter(
                                getattr(model, unique_check_field) == value_to_check
                            ).first()
                            if existing:
                                skipped_count += 1
                                errors.append(f"Row {index + 2}: {unique_check_field.title()} '{value_to_check}' already exists (skipped)")
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
        Model is discovered dynamically from SQLAlchemy registry.
        
        Args:
            table_name: Name of the master table
            
        Returns:
            Dictionary with deletion results including count of deleted records
        """
        try:
            # Dynamically get model class
            model = self._get_model_by_table_name(table_name)
        except HTTPException:
            raise
        
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

