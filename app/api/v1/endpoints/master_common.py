from fastapi import APIRouter, Depends, status, UploadFile, File, Query, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.services.master_common_service import MasterCommonService
from app.schemas.master import MasterListResponse, BulkInsertResponse, BulkDeleteResponse

router = APIRouter()


@router.get("/", response_model=MasterListResponse, status_code=status.HTTP_200_OK)
def get_master_data_by_table(
    table_name: str = Query(..., description="Name of the master table"),
    db: Session = Depends(get_db)
):
    """
    Common GET endpoint to retrieve all data from any master table.
    
    **Dynamic Table Discovery**: This endpoint works with any table that:
    1. Is registered in the `master_table_list` table
    2. Has a corresponding SQLAlchemy model in the codebase
    
    To add a new master table:
    1. Create the SQLAlchemy model with the table name
    2. Add a record to `master_table_list` with the table name
    3. No code changes needed - the system will automatically discover it!
    
    The table name must match exactly the `__tablename__` attribute of the model.
    """
    service = MasterCommonService(db)
    data = service.get_all_by_table_name(table_name)
    return {
        "status": "success",
        "message": f"Data fetched successfully from {table_name}",
        "data": data
    }


@router.post("/upload", response_model=BulkInsertResponse, status_code=status.HTTP_201_CREATED)
def bulk_insert_from_excel(
    table_name: str = Query(..., description="Name of the master table"),
    file: UploadFile = File(..., description="Excel file (.xlsx or .xls)"),
    db: Session = Depends(get_db),
    created_by: Optional[str] = Header(None, alias="X-Created-By")
):
    """
    Common POST endpoint to bulk insert data from Excel file into master tables.
    
    **Dynamic Field Mapping**: Fields are read dynamically from Excel. Any column in Excel 
    that matches a database column name (case-insensitive) will be automatically processed.
    No code changes needed when adding new columns to Excel - just add them to the Excel file!
    
    **Required Columns**: 
    - All non-nullable columns in the database table must be present in Excel
    - The system automatically detects which columns are required based on the table schema
    - Common required columns: 'value' (for simple master tables), 'state' and 'municipality' (for mapping tables), etc.
    
    **Optional Columns** (automatically detected if present in Excel):
    - 'created_by' (String) - If not in Excel, uses X-Created-By header if provided
    - 'updated_by' (String)
    - Any other columns that exist in the database table
    
    **Excluded Columns** (auto-generated, cannot be set from Excel):
    - 'id' - Auto-generated primary key
    - 'created_at' - Auto-generated timestamp
    - 'updated_at' - Auto-generated timestamp
    
    **Dynamic Table Discovery**: This endpoint works with any table that:
    1. Is registered in the `master_table_list` table
    2. Has a corresponding SQLAlchemy model in the codebase
    
    To add a new master table:
    1. Create the SQLAlchemy model with the table name
    2. Add a record to `master_table_list` with the table name
    3. No code changes needed - the system will automatically discover it!
    
    Note: Column names are case-insensitive. 'Value', 'VALUE', or 'value' all work.
    """
    service = MasterCommonService(db)
    result = service.bulk_insert_from_excel(table_name, file, created_by=created_by)
    
    message = (
        f"Successfully inserted {result['success_count']} records into {table_name}. "
        f"Skipped {result['skipped_count']} duplicates. "
        f"Errors: {result['error_count']}"
    )
    
    return {
        "status": "success",
        "message": message,
        "data": result
    }


@router.delete("/", response_model=BulkDeleteResponse, status_code=status.HTTP_200_OK)
def delete_all_master_data_by_table(
    table_name: str = Query(..., description="Name of the master table"),
    db: Session = Depends(get_db)
):
    """
    Common DELETE endpoint to delete all records from any master table.
    
    **Warning**: This operation will delete ALL records from the specified master table.
    This action cannot be undone. Use with caution.
    
    **Note**: If records from this master table are referenced by other tables through
    foreign key constraints, the deletion will fail with a 409 Conflict error.
    
    **Dynamic Table Discovery**: This endpoint works with any table that:
    1. Is registered in the `master_table_list` table
    2. Has a corresponding SQLAlchemy model in the codebase
    
    To add a new master table:
    1. Create the SQLAlchemy model with the table name
    2. Add a record to `master_table_list` with the table name
    3. No code changes needed - the system will automatically discover it!
    """
    service = MasterCommonService(db)
    result = service.delete_all_by_table_name(table_name)
    
    return {
        "status": "success",
        "message": result["message"],
        "data": {
            "deleted_count": result["deleted_count"],
            "table_name": table_name
        }
    }

