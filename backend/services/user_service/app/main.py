# backend/services/user_service/app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.preferences import (
    InstitutionPreference,
    PreferenceCreateRequest,
    PreferenceUpdateRequest,
    PreferenceResponse
)

class UserPersona(BaseModel):
    user_id: str = Field(..., description="The unique identifier for the user.")
    investment_style: Optional[str] = Field(None, description="User's preferred investment style (e.g., 'Value', 'Growth').")
    report_preference: Optional[str] = Field(None, description="User's preferred report template (e.g., 'Executive Summary', 'Deep Dive').")
    risk_tolerance: Optional[str] = Field(None, description="User's risk tolerance (e.g., 'Low', 'Medium', 'High').")

# In-memory database for simplicity
db: dict[str, UserPersona] = {}
preferences_db: dict[str, InstitutionPreference] = {}

app = FastAPI(
    title="User Service",
    description="Manages user personas and preferences.",
    version="1.0.0"
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/users/{user_id}", response_model=UserPersona)
async def create_or_update_user_persona(user_id: str, persona: UserPersona):
    """
    Create or update a user's persona.
    """
    if user_id != persona.user_id:
        raise HTTPException(status_code=400, detail="Path user_id does not match payload user_id.")
    db[user_id] = persona
    return persona

@app.get("/users/{user_id}", response_model=UserPersona)
async def get_user_persona(user_id: str):
    """
    Retrieve a user's persona.
    """
    if user_id not in db:
        # Return a default persona if user not found
        return UserPersona(user_id=user_id, investment_style="Balanced", report_preference="Deep Dive", risk_tolerance="Medium")
    return db[user_id]

@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "User Service"}


# ===== Institution Preferences API =====

@app.post("/api/v1/preferences", response_model=PreferenceResponse, tags=["Preferences"])
async def create_or_update_preference(request: PreferenceCreateRequest):
    """
    创建或更新机构投资偏好
    """
    try:
        # Create preference object
        preference = InstitutionPreference(
            user_id=request.user_id,
            investment_thesis=request.investment_thesis,
            preferred_stages=request.preferred_stages,
            focus_industries=request.focus_industries,
            excluded_industries=request.excluded_industries,
            geography_preference=request.geography_preference,
            investment_range=request.investment_range,
            min_team_size=request.min_team_size,
            require_revenue=request.require_revenue,
            require_product=request.require_product,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Store in database
        preferences_db[request.user_id] = preference
        
        return PreferenceResponse(
            success=True,
            message="偏好设置成功",
            preference=preference
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建偏好失败: {str(e)}")


@app.get("/api/v1/preferences/{user_id}", response_model=PreferenceResponse, tags=["Preferences"])
async def get_preference(user_id: str):
    """
    获取机构投资偏好
    """
    if user_id not in preferences_db:
        return PreferenceResponse(
            success=False,
            message="未找到该机构的投资偏好设置",
            preference=None
        )
    
    return PreferenceResponse(
        success=True,
        message="获取偏好成功",
        preference=preferences_db[user_id]
    )


@app.put("/api/v1/preferences/{user_id}", response_model=PreferenceResponse, tags=["Preferences"])
async def update_preference(user_id: str, request: PreferenceUpdateRequest):
    """
    更新机构投资偏好
    """
    if user_id not in preferences_db:
        raise HTTPException(status_code=404, detail="未找到该机构的偏好设置")
    
    # Get existing preference
    existing_pref = preferences_db[user_id]
    
    # Update fields if provided
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(existing_pref, field, value)
    
    # Update timestamp
    existing_pref.updated_at = datetime.utcnow()
    
    # Save
    preferences_db[user_id] = existing_pref
    
    return PreferenceResponse(
        success=True,
        message="偏好更新成功",
        preference=existing_pref
    )


@app.delete("/api/v1/preferences/{user_id}", tags=["Preferences"])
async def delete_preference(user_id: str):
    """
    删除机构投资偏好
    """
    if user_id not in preferences_db:
        raise HTTPException(status_code=404, detail="未找到该机构的偏好设置")
    
    del preferences_db[user_id]
    
    return {
        "success": True,
        "message": "偏好删除成功"
    }
