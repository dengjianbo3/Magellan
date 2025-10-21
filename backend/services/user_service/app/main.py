# backend/services/user_service/app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

class UserPersona(BaseModel):
    user_id: str = Field(..., description="The unique identifier for the user.")
    investment_style: Optional[str] = Field(None, description="User's preferred investment style (e.g., 'Value', 'Growth').")
    report_preference: Optional[str] = Field(None, description="User's preferred report template (e.g., 'Executive Summary', 'Deep Dive').")
    risk_tolerance: Optional[str] = Field(None, description="User's risk tolerance (e.g., 'Low', 'Medium', 'High').")

# In-memory database for simplicity
db: dict[str, UserPersona] = {}

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
