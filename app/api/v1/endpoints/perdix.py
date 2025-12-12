from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from app.schemas.perdix import PerdixQueryRequest
from app.services.perdix_service import query_perdix

router = APIRouter()


@router.post("/query", status_code=status.HTTP_200_OK)
def query_perdix_endpoint(query_request: PerdixQueryRequest):
    """
    Execute a dynamic query against Perdix API.
    
    This endpoint allows you to execute any Perdix query by providing:
    - identifier: The query identifier (e.g., 'childBranch.list')
    - parameters: Optional query parameters as key-value pairs
    - limit: Pagination limit (default: 0 = no limit)
    - offset: Pagination offset (default: 0)
    - skip_relogin: Skip relogin flag (default: 'yes')
    
    Example for fetching child branches:
    {
        "identifier": "childBranch.list",
        "parameters": {
            "parent_branch_id": 94
        }
    }
    """
    try:
        body, status_code, is_json = query_perdix(query_request)
        return JSONResponse(
            content=body if is_json else {"raw": body},
            status_code=status_code
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute Perdix query: {str(e)}"
        )

