from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
from pathlib import Path
import uuid
from PIL import Image

from app.core.database import get_db, User
from app.core.auth import get_current_user_optional
from app.core.config import settings

router = APIRouter()

# Pydantic models
class MediaResponse(BaseModel):
    filename: str
    original_filename: str
    file_path: str
    file_url: str
    file_size: int
    content_type: str
    width: Optional[int] = None
    height: Optional[int] = None

class MediaListResponse(BaseModel):
    files: List[MediaResponse]
    total: int

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def get_file_extension(filename: str) -> str:
    """Get file extension in lowercase."""
    return Path(filename).suffix.lower()

def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return get_file_extension(filename) in ALLOWED_EXTENSIONS

def is_safe_filename(filename: str) -> bool:
    """Check if filename is safe (no path traversal)."""
    if not filename or '..' in filename or '/' in filename or '\\' in filename:
        return False
    if filename.startswith('.') or filename.endswith('.'):
        return False
    return len(filename) <= 255 and filename.isprintable()

def get_image_dimensions(file_path: str) -> tuple:
    """Get image dimensions."""
    try:
        with Image.open(file_path) as img:
            return img.size
    except Exception:
        return None, None

def validate_filename(filename: str) -> str:
    """Validate and sanitize filename to prevent path traversal."""
    if not filename:
        raise ValueError("Filename cannot be empty")

    # Remove any path components
    filename = os.path.basename(filename)

    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        raise ValueError("Invalid filename: path traversal detected")

    # Check for hidden files or system files
    if filename.startswith('.') or filename.startswith('~'):
        raise ValueError("Invalid filename: hidden or system files not allowed")

    return filename

def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving extension."""
    # Validate the original filename first
    safe_filename = validate_filename(original_filename)
    ext = get_file_extension(safe_filename)
    unique_id = str(uuid.uuid4())
    return f"{unique_id}{ext}"

@router.post("/upload", response_model=MediaResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_optional)
):
    """Upload a media file."""
    
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    if not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Stream file directly to disk to avoid memory issues
    user_dir = settings.MEDIA_DIR / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    unique_filename = generate_unique_filename(file.filename)
    file_path = user_dir / unique_filename

    # Stream file to disk with size checking
    file_size = 0
    try:
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(8192)  # 8KB chunks
                if not chunk:
                    break

                file_size += len(chunk)

                # Check size limit during streaming
                if file_size > MAX_FILE_SIZE:
                    buffer.close()
                    file_path.unlink()  # Delete partial file
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
                    )

                buffer.write(chunk)
    except Exception as e:
        # Clean up partial file on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        ) from e

    # Validate file content for security (read first chunk for validation)
    with open(file_path, "rb") as f:
        first_chunk = f.read(8192)

    from app.core.security import validate_file_upload
    if not validate_file_upload(first_chunk, file.filename):
        file_path.unlink()  # Delete the file
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file content or potentially malicious file"
        )

    # Save original filename metadata
    meta_path = file_path.with_suffix(file_path.suffix + ".meta")
    try:
        with open(meta_path, "w", encoding="utf-8") as meta_file:
            meta_file.write(file.filename)
    except Exception:
        # If metadata save fails, continue anyway
        pass
    
    # Get image dimensions
    width, height = get_image_dimensions(str(file_path))
    
    # Create response
    file_url = f"/media/{current_user.id}/{unique_filename}"
    
    return MediaResponse(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_url=file_url,
        file_size=file_size,
        content_type=file.content_type or "image/jpeg",
        width=width,
        height=height
    )

@router.get("/files", response_model=MediaListResponse)
async def list_files(
    current_user: User = Depends(get_current_user_optional)
):
    """List all uploaded files for the current user."""
    
    user_dir = settings.MEDIA_DIR / str(current_user.id)
    
    if not user_dir.exists():
        return MediaListResponse(files=[], total=0)
    
    files = []
    for file_path in user_dir.iterdir():
        if file_path.is_file() and is_allowed_file(file_path.name) and not file_path.name.endswith('.meta'):
            try:
                stat = file_path.stat()
                width, height = get_image_dimensions(str(file_path))

                # Try to read original filename from metadata
                meta_path = file_path.with_suffix(file_path.suffix + ".meta")
                original_filename = file_path.name
                if meta_path.exists():
                    try:
                        with open(meta_path, "r", encoding="utf-8") as meta_file:
                            original_filename = meta_file.read().strip()
                    except Exception:
                        original_filename = file_path.name

                # Determine proper content type
                import mimetypes
                content_type, _ = mimetypes.guess_type(file_path.name)
                if content_type is None:
                    content_type = "application/octet-stream"

                file_url = f"/media/{current_user.id}/{file_path.name}"

                files.append(MediaResponse(
                    filename=file_path.name,
                    original_filename=original_filename,
                    file_path=str(file_path),
                    file_url=file_url,
                    file_size=stat.st_size,
                    content_type=content_type,
                    width=width,
                    height=height
                ))
            except Exception:
                continue  # Skip files that can't be processed
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: os.path.getmtime(x.file_path), reverse=True)
    
    return MediaListResponse(files=files, total=len(files))

@router.get("/files/{filename}")
async def get_file(
    filename: str,
    current_user: User = Depends(get_current_user_optional)
):
    """Get a specific file."""

    # Validate filename to prevent path traversal
    if not is_safe_filename(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )

    user_dir = settings.MEDIA_DIR / str(current_user.id)
    file_path = user_dir / filename

    # Ensure the resolved path is within the user directory
    try:
        file_path = file_path.resolve()
        user_dir = user_dir.resolve()
        if not str(file_path).startswith(str(user_dir)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    except (OSError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    if not is_allowed_file(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type not allowed"
        )

    import mimetypes

    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type is None:
        mime_type = "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=mime_type
    )

@router.delete("/files/{filename}")
async def delete_file(
    filename: str,
    current_user: User = Depends(get_current_user_optional)
):
    """Delete a file."""

    # Validate filename to prevent path traversal
    if not is_safe_filename(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )

    user_dir = settings.MEDIA_DIR / str(current_user.id)
    file_path = user_dir / filename

    # Ensure the resolved path is within the user directory
    try:
        file_path = file_path.resolve()
        user_dir = user_dir.resolve()
        if not str(file_path).startswith(str(user_dir)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    except (OSError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    try:
        file_path.unlink()
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )

@router.post("/process-image")
async def process_image(
    filename: str = Form(...),
    operation: str = Form(...),  # resize, crop, convert
    width: Optional[int] = Form(None),
    height: Optional[int] = Form(None),
    x: Optional[int] = Form(None),
    y: Optional[int] = Form(None),
    format: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user_optional)
):
    """Process an image (resize, crop, convert format)."""
    
    user_dir = settings.MEDIA_DIR / str(current_user.id)
    file_path = user_dir / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    try:
        with Image.open(file_path) as img:
            processed_img = img.copy()
            
            if operation == "resize" and width and height:
                processed_img = processed_img.resize((width, height), Image.Resampling.LANCZOS)
            
            elif operation == "crop" and width and height and x is not None and y is not None:
                processed_img = processed_img.crop((x, y, x + width, y + height))
            
            elif operation == "convert" and format:
                # Format conversion will be handled during save
                pass
            
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid operation or missing parameters"
                )
            
            # Generate new filename
            base_name = file_path.stem
            ext = f".{format.lower()}" if format else file_path.suffix
            new_filename = f"{base_name}_processed_{operation}{ext}"
            new_file_path = user_dir / new_filename
            
            # Save processed image
            save_format = format.upper() if format else img.format
            if save_format == "JPG":
                save_format = "JPEG"
            
            processed_img.save(new_file_path, format=save_format, quality=95)
            
            # Get dimensions of processed image
            proc_width, proc_height = processed_img.size
            
            file_url = f"/media/{current_user.id}/{new_filename}"
            
            return MediaResponse(
                filename=new_filename,
                original_filename=filename,
                file_path=str(new_file_path),
                file_url=file_url,
                file_size=new_file_path.stat().st_size,
                content_type=f"image/{format.lower()}" if format else "image/jpeg",
                width=proc_width,
                height=proc_height
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image: {str(e)}"
        )
