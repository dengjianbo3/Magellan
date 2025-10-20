# backend/services/file_service/app/main.py
import os
import shutil
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException

# Define a shared volume path that will be mounted in the Docker container.
# This allows other services to access the uploaded files.
SHARED_VOLUME_PATH = "/var/uploads"

app = FastAPI(
    title="File Ingestion Service",
    description="Handles file uploads and saves them to a shared volume.",
    version="1.0.0"
)

@app.on_event("startup")
def startup_event():
    """Ensure the shared upload directory exists on startup."""
    os.makedirs(SHARED_VOLUME_PATH, exist_ok=True)

@app.post("/upload", response_model=dict)
async def upload_file(file: UploadFile = File(...)):
    """
    Receives a file, saves it to the shared volume with a unique ID,
    and returns the generated file ID.
    """
    try:
        # Generate a unique filename to avoid collisions
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(SHARED_VOLUME_PATH, unique_filename)

        with open(file_path, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

        # The unique filename serves as the file_id
        return {"file_id": unique_filename, "original_filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "File Service"}