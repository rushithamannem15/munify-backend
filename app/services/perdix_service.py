import httpx
from fastapi import HTTPException, status
from app.core.config import settings
from app.schemas.perdix import PerdixQueryRequest


def query_perdix(query_request: PerdixQueryRequest) -> tuple:
    """
    Execute a dynamic query against Perdix API /api/query endpoint.
    
    This is a general-purpose function that can execute any Perdix query
    by passing the identifier and parameters. The query is executed in the
    Perdix database based on the identifier.
    
    Args:
        query_request: PerdixQueryRequest containing identifier, parameters, etc.
    
    Returns:
        tuple: (response_body, status_code, is_json)
    """
    base_url = settings.PERDIX_BASE_URL.rstrip("/")
    url = f"{base_url}/api/query"
    
    if not settings.PERDIX_JWT:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Perdix JWT is not configured"
        )
    
    # Build payload from request
    payload = {
        "identifier": query_request.identifier,
        "limit": query_request.limit,
        "offset": query_request.offset,
        "skip_relogin": query_request.skip_relogin
    }
    
    # Add parameters if provided
    if query_request.parameters:
        payload["parameters"] = query_request.parameters
    
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"JWT {settings.PERDIX_JWT}",
        "content-type": "application/json;charset=UTF-8",
        "origin": settings.PERDIX_ORIGIN,
        "page_uri": settings.PERDIX_PAGE_URI,
        "referer": f"{settings.PERDIX_ORIGIN}/perdix-client/",
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Perdix API: {str(exc)}"
        )
    
    # Return raw Perdix response body and status for the caller to forward
    try:
        body = response.json()
        return body, response.status_code, True
    except ValueError:
        return response.text, response.status_code, False

