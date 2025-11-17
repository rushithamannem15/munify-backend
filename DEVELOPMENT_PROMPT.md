# API Development Prompt for Munify Backend

## Project Overview
This is a **FastAPI-based backend application** for a municipal project marketplace called **Munify**. The system handles commitments, projects, parties, users, documents, and integrations with external systems (Perdix).

## Architecture & Structure

### Directory Structure
```
app/
├── api/v1/
│   ├── api.py                 # Main router configuration
│   └── endpoints/             # API endpoint files
├── core/
│   ├── config.py              # Settings and environment variables
│   ├── database.py            # SQLAlchemy setup
│   ├── exceptions.py          # Exception handlers
│   └── logging.py             # Logging configuration
├── models/                    # SQLAlchemy ORM models
├── schemas/                   # Pydantic schemas (request/response models)
├── services/                  # Business logic layer
├── middleware/                # Request/response middleware
└── utils/                     # Utility functions
```

### Key Technologies
- **FastAPI** - Web framework
- **SQLAlchemy 2.0** - ORM
- **Pydantic 2.5** - Data validation
- **psycopg** - PostgreSQL database driver
- **Alembic** - Database migrations
- **httpx** - HTTP client for external APIs

## Core Principles

### 1. Separation of Concerns
- **Endpoints** (`app/api/v1/endpoints/`): Handle HTTP requests, authentication, response formatting
- **Services** (`app/services/`): Contain ALL business logic
- **Models** (`app/models/`): SQLAlchemy ORM models for database tables
- **Schemas** (`app/schemas/`): Pydantic models for request validation and response serialization

### 2. Service Layer Pattern
**ALL business logic MUST be in the service layer**, not in endpoints. Endpoints should:
- Extract request data
- Call service methods
- Format responses
- Handle HTTP-specific concerns

**Example:**
```python
# Endpoint (minimal logic)
@router.post("/")
def create_item(item_data: ItemCreate, db: Session = Depends(get_db)):
    service = ItemService(db)
    result = service.create_item(item_data)
    return {"status": "success", "message": "Item created", "data": result}

# Service (business logic)
class ItemService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_item(self, item_data: ItemCreate) -> ItemModel:
        # Validation
        # Business rules
        # Database operations
        # Return result
```

### 3. Database Session Management
- Use `get_db()` dependency for database sessions
- Always pass `db: Session = Depends(get_db)` to endpoint functions
- Services receive `db` session in constructor
- Use `self.db` within service methods for queries

**Pattern:**
```python
# Endpoint
def create_item(item_data: ItemCreate, db: Session = Depends(get_db)):
    service = ItemService(db)
    return service.create_item(item_data)

# Service
class ItemService:
    def __init__(self, db: Session):
        self.db = db
```

### 4. Schema Definition Pattern
- **Create Schema**: Fields required for creation (omitting id, timestamps)
- **Update Schema**: All fields optional for partial updates
- **Response Schema**: All fields required, includes id and timestamps

**Naming Convention:**
- `{Entity}Create` - For POST requests
- `{Entity}Update` - For PUT/PATCH requests
- `{Entity}` or `{Entity}Response` - For responses
- `{Entity}ListResponse` - For list endpoints

### 5. Error Handling
- Use HTTPException from FastAPI for errors
- Return proper HTTP status codes
- Include descriptive error messages
- Log errors using the logger utility

**Standard Error Responses:**
```python
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Resource not found"
)
```

**HTTP Status Codes:**
- `200` - Success (GET, PUT, PATCH)
- `201` - Created (POST)
- `204` - No Content (DELETE)
- `404` - Not Found
- `409` - Conflict (duplicate)
- `422` - Unprocessable Entity (validation)
- `500` - Internal Server Error

### 6. Logging
Use structured logging for all operations:

```python
from app.core.logging import get_logger
from app.utils.logger import log_business_event, log_error, log_database_operation

logger = get_logger("services.your_service")

# Business events
log_business_event("item_created", user_id=user_id, entity_type="item", entity_id=item.id)

# Errors
log_error("item_not_found", f"Item not found: {item_id}", item_id=item_id)

# Database operations
log_database_operation("create", "items", record_id=item.id, user_id=user_id)
```

### 7. Response Format
Use consistent response format across all endpoints:

**Success Response:**
```python
{
    "status": "success",
    "message": "Operation completed successfully",
    "data": {...},  # Optional
    "total": 100    # For list endpoints
}
```

**Error Response:**
```python
{
    "status": "error",
    "message": "Error description",
    "errors": [...] # Optional validation errors
}
```

### 8. API Router Registration
When creating new endpoints, register them in `app/api/v1/api.py`:

```python
from app.api.v1.endpoints import your_module

api_router.include_router(your_module.router, prefix="/your-route", tags=["your-tag"])
```

## Database Patterns

### PostgreSQL-Specific Considerations
- **Database**: PostgreSQL (not MySQL)
- **Driver**: `psycopg` (async-capable PostgreSQL adapter)
- **Connection String**: `postgresql+psycopg://user:password@host:port/dbname`
- **String Types**: 
  - Use `String(255)` or `VARCHAR(n)` for fixed-length strings (PostgreSQL supports up to 10MB, but use reasonable lengths)
  - Use `Text` for unlimited-length strings (no need for `LONGTEXT` like MySQL)
- **Numeric Types**: Use `Numeric(precision, scale)` for precise decimal arithmetic (recommended for financial data)
- **Auto-increment**: Use `Integer` with `primary_key=True` (SQLAlchemy handles sequence generation) or `BIGSERIAL` in raw SQL
- **JSON Support**: PostgreSQL has excellent JSON/JSONB support - use `JSON` or `JSONB` types for flexible schemas
- **Array Support**: PostgreSQL supports native arrays - use `ARRAY` type when appropriate
- **Full-Text Search**: PostgreSQL has built-in full-text search capabilities (tsvector, tsquery)

### Model Definition
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.dialects.postgresql import JSONB  # PostgreSQL-specific JSONB type
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class YourModel(Base):
    __tablename__ = "your_table"
    
    id = Column(Integer, primary_key=True, index=True)
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # String fields
    name = Column(String(255), nullable=False)  # PostgreSQL: VARCHAR can be up to 10MB, but use reasonable lengths
    description = Column(Text, nullable=False)  # PostgreSQL: TEXT for unlimited length
    
    # Numeric fields (PostgreSQL: NUMERIC for precise decimal arithmetic)
    amount = Column(Numeric(18, 2), nullable=False)  # precision=18, scale=2 (e.g., 9999999999999999.99)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="your_items")
    
    # PostgreSQL-specific: JSONB for flexible metadata
    # metadata = Column(JSONB, nullable=True)  # Use JSONB for queryable JSON data
```


### Relationships
- Define bidirectional relationships with `back_populates`
- Use `cascade="all, delete-orphan"` for child records
- Use `joinedload()` for eager loading to avoid N+1 queries

**Example:**
```python
# In User model
projects = relationship("Project", back_populates="user")

# In Project model  
user = relationship("User", back_populates="projects")

# In query
user = db.query(UserModel).options(joinedload(UserModel.projects)).filter(UserModel.id == user_id).first()
```

## Business Logic Validation

### Service Layer Validation
All business rules and validations MUST be in the service layer:

**Validation Examples:**
```python
def _validate_user_exists(self, user_id: int) -> UserModel:
    """Validate that user exists"""
    user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

def _validate_authorization(self, user_id: int, required_role: str):
    """Validate user has required role"""
    user = self._validate_user_exists(user_id)
    if user.role != required_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User must be {required_role}"
        )
```

### Financial Calculations
Handle financial operations carefully with Decimal type (PostgreSQL NUMERIC maps to Python Decimal):

```python
from decimal import Decimal

def _calculate_funding_gap(self, funding_required: Decimal, funds_secured: Decimal = Decimal('0')) -> Decimal:
    """Calculate funding gap"""
    return funding_required - funds_secured

# Use Decimal consistently (PostgreSQL NUMERIC type ensures precision)
amount = Decimal('100.00')
funding_gap = self._calculate_funding_gap(required_amount, secured_amount)
```

**PostgreSQL Note**: The `Numeric` type in SQLAlchemy maps to PostgreSQL's `NUMERIC` type, which provides exact decimal arithmetic. This is crucial for financial calculations to avoid floating-point rounding errors.

## Transaction Management

### Database Transactions
- Always use `db.commit()` after database modifications
- Use `db.rollback()` in error handlers
- Use try-except blocks for transaction safety

**Pattern:**
```python
def create_item(self, item_data: ItemCreate):
    try:
        item = ItemModel(**item_data.dict())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
    except Exception as e:
        self.db.rollback()
        raise
```

## Integration with External APIs

### External Service Pattern
For integrations with external APIs (e.g., Perdix):

```python
import httpx
from fastapi import HTTPException, status
from app.core.config import settings

def call_external_api(payload: dict) -> tuple:
    """Call external API and return (body, status_code, is_json)"""
    url = f"{settings.EXTERNAL_BASE_URL}/endpoint"
    
    headers = {
        "content-type": "application/json",
        "authorization": f"JWT {settings.JWT_TOKEN}",
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, 
            detail=str(exc)
        )
    
    try:
        return response.json(), response.status_code, True
    except ValueError:
        return response.text, response.status_code, False
```

## Database Migrations

### Alembic Usage
- All schema changes MUST go through Alembic migrations
- Never modify models without creating a migration
- Use descriptive migration messages

**Creating Migrations:**
```bash
alembic revision -m "your_descriptive_message"
alembic upgrade head
```

## Security Considerations

### Password Hashing
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)
```

### Input Validation
- Use Pydantic schemas for all request/response validation
- Validate foreign key references exist before use
- Sanitize user inputs
- Check authorization before operations

## Testing & Code Quality

### Before Implementing Changes:
1. **Analyze Dependencies**: Check which other APIs/models might be affected
2. **Check Relationships**: Ensure foreign key relationships are preserved
3. **Review Business Logic**: Understand existing validation rules
4. **Identify Impact**: List all potentially affected endpoints/modules

### Code Review Checklist:
- [ ] Business logic is in service layer
- [ ] Endpoints are thin and focused on HTTP concerns
- [ ] Proper error handling with appropriate HTTP status codes
- [ ] Database transactions are properly managed
- [ ] Logging is implemented for important operations
- [ ] Response format is consistent with existing APIs
- [ ] Relationships and foreign keys are handled correctly
- [ ] Financial calculations use Decimal type
- [ ] External API calls have proper error handling
- [ ] Schema definitions follow naming conventions

## API Development Workflow

### When Adding a New API Endpoint:

1. **Define Schemas** (`app/schemas/`):
   - Create {Entity}Create, {Entity}Update, {Entity}Response schemas

2. **Create Model** (if new entity) (`app/models/`):
   - Define SQLAlchemy model with proper fields and relationships

3. **Create Service** (`app/services/`):
   - Implement all business logic
   - Add validation methods
   - Handle database operations

4. **Create Endpoint** (`app/api/v1/endpoints/`):
   - Keep logic minimal
   - Call service methods
   - Format responses

5. **Register Router** (`app/api/v1/api.py`):
   - Add router to api_router

6. **Create Migration** (if model changed):
   - Generate Alembic migration
   - Review migration file
   - Apply migration

7. **Test**:
   - Test happy path
   - Test error cases
   - Test validation
   - Test business rules

## Impact Analysis Framework

### When Making Changes, Consider:

1. **Direct Dependencies**:
   - What other models reference this entity?
   - What foreign keys point to this entity?
   - What cascade rules are in place?

2. **Business Logic Dependencies**:
   - What other services call this service?
   - What validation rules depend on this entity?
   - What calculated fields reference this data?

3. **API Dependencies**:
   - What endpoints use this entity?
   - What response schemas include this entity?
   - What nested queries might break?

4. **External Integrations**:
   - Does this entity sync with external APIs?
   - Are there webhooks or callbacks?
   - Any background jobs processing this data?

### Warning Indicators:
⚠️ **If any of these apply, warn about potential impacts:**

- Modifying a model with multiple foreign key references
- Changing a field used in calculations (especially financial)
- Modifying validation logic in a service used by multiple endpoints
- Updating cascade delete behavior
- Changing response schema structure
- Modifying external API integration logic
- Adding/removing required fields in existing schemas

## Example: Complete Implementation Pattern

Here's a complete example following all patterns:

### 1. Schema (`app/schemas/item.py`):
```python
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime

class ItemCreate(BaseModel):
    user_id: int
    name: str
    amount: Decimal

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[Decimal] = None

class ItemResponse(BaseModel):
    id: int
    user_id: int
    name: str
    amount: Decimal
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
```

### 2. Model (`app/models/item.py`):
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)  # PostgreSQL: Use VARCHAR with reasonable length
    amount = Column(Numeric(18, 2), nullable=False)  # PostgreSQL: NUMERIC for precise decimal arithmetic
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="items")
```

### 3. Service (`app/services/item_service.py`):
```python
from sqlalchemy.orm import Session
from app.models.item import Item as ItemModel
from app.schemas.item import ItemCreate, ItemUpdate
from app.core.logging import get_logger
from fastapi import HTTPException, status

logger = get_logger("services.item")

class ItemService:
    def __init__(self, db: Session):
        self.db = db
    
    def _validate_user(self, user_id: int):
        """Validate user exists"""
        user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    
    def create_item(self, item_data: ItemCreate) -> ItemModel:
        """Create a new item"""
        logger.info(f"Creating item for user {item_data.user_id}")
        
        # Validate user exists
        self._validate_user(item_data.user_id)
        
        # Create item
        item = ItemModel(**item_data.dict())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        
        logger.info(f"Item {item.id} created successfully")
        return item
    
    def get_item_by_id(self, item_id: int) -> ItemModel:
        """Get item by ID"""
        item = self.db.query(ItemModel).filter(ItemModel.id == item_id).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        return item
    
    def update_item(self, item_id: int, item_data: ItemUpdate) -> ItemModel:
        """Update an item"""
        item = self.get_item_by_id(item_id)
        
        update_data = item_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)
        
        self.db.commit()
        self.db.refresh(item)
        return item
    
    def delete_item(self, item_id: int) -> None:
        """Delete an item"""
        item = self.get_item_by_id(item_id)
        self.db.delete(item)
        self.db.commit()
```

### 4. Endpoint (`app/api/v1/endpoints/items.py`):
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse
from app.services.item_service import ItemService

router = APIRouter()

@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item_data: ItemCreate, db: Session = Depends(get_db)):
    """Create a new item"""
    service = ItemService(db)
    db_item = service.create_item(item_data)
    return {
        "status": "success",
        "message": "Item created successfully",
        "data": db_item
    }

@router.get("/{item_id}", response_model=ItemResponse, status_code=status.HTTP_200_OK)
def get_item(item_id: int, db: Session = Depends(get_db)):
    """Get item by ID"""
    service = ItemService(db)
    db_item = service.get_item_by_id(item_id)
    return {
        "status": "success",
        "message": "Item fetched successfully",
        "data": db_item
    }

@router.put("/{item_id}", response_model=ItemResponse, status_code=status.HTTP_200_OK)
def update_item(item_id: int, item_data: ItemUpdate, db: Session = Depends(get_db)):
    """Update an item"""
    service = ItemService(db)
    db_item = service.update_item(item_id, item_data)
    return {
        "status": "success",
        "message": "Item updated successfully",
        "data": db_item
    }

@router.delete("/{item_id}", status_code=status.HTTP_200_OK)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Delete an item"""
    service = ItemService(db)
    service.delete_item(item_id)
    return {
        "status": "success",
        "message": "Item deleted successfully"
    }
```

### 5. Register Router (`app/api/v1/api.py`):
```python
from app.api.v1.endpoints import items

api_router.include_router(items.router, prefix="/items", tags=["items"])
```

---

## How to Use This Prompt

**For specific API development tasks, combine this prompt with your requirements:**

```
[This prompt]

+ Your specific API requirement:
"I need to create a new API for managing suppliers..."

+ Specific requirements:
- Endpoint: POST /suppliers
- Fields: name, contact_email, address
- Business rule: email must be unique
- Relations: linked to projects table
```

## API Testing with Karate

Use Karate to write end-to-end API tests against FastAPI endpoints.

### Test Project Structure
```
tests/
  karate/
    karate-config.js
    features/
      items/
        create_item.feature
```

### Sample Feature (`tests/karate/features/items/create_item.feature`)
```gherkin
Feature: Items API

  Background:
    * url baseUrl

  Scenario: Create item successfully
    Given path 'api/v1/items'
    And request { user_id: 1, name: 'Book', amount: 100.00 }
    When method post
    Then status 201
    And match response.status == 'success'
```

### Karate Config (`tests/karate/karate-config.js`)
```javascript
function fn() {
  return { baseUrl: java.lang.System.getenv('BASE_URL') || 'http://localhost:8000' };
}
```

### Run Tests
- With standalone JAR (no Java project setup required):
```bash
# Download once: https://github.com/karatelabs/karate/releases (karate-<ver>.jar)
java -jar karate-*.jar -p tests/karate/features -e dev
```

- With Maven (if you prefer a Java runner):
```bash
mvn -q -Dtest=KarateRunner test
```

Tip: Ensure the FastAPI app is running locally (e.g., `uvicorn app.main:app --reload`) and set `BASE_URL` accordingly.

