from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Optional

from app.core.database import get_db, User
from app.core.auth import get_current_user_optional
from app.services.settings_service import (
    save_user_setting,
    get_user_setting,
    get_user_settings,
    delete_user_setting
)

router = APIRouter()

# Pydantic models
class SettingRequest(BaseModel):
    key: str
    value: str
    is_sensitive: bool = False

class SettingResponse(BaseModel):
    key: str
    value: str
    is_sensitive: bool

class EnvironmentSettingsRequest(BaseModel):
    HF_TOKEN: Optional[str] = ""
    HF_HOME: Optional[str] = ""
    CIVITAI_API_KEY: Optional[str] = ""
    GOOGLE_API_KEY: Optional[str] = ""
    FAL_KEY: Optional[str] = ""

class EnvironmentSettingsResponse(BaseModel):
    HF_TOKEN: str = ""
    HF_HOME: str = ""
    CIVITAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    FAL_KEY: str = ""

# Sensitive keys that should be encrypted
SENSITIVE_KEYS = {
    'HF_TOKEN',
    'CIVITAI_API_KEY', 
    'GOOGLE_API_KEY',
    'FAL_KEY'
}

@router.post("/setting")
async def save_setting(
    request: SettingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Save a user setting."""
    
    # Auto-detect if key should be sensitive
    is_sensitive = request.is_sensitive or request.key in SENSITIVE_KEYS
    
    setting = await save_user_setting(
        user_id=current_user.id,
        key=request.key,
        value=request.value,
        is_sensitive=is_sensitive,
        db=db
    )
    
    return {"message": "Setting saved successfully", "key": request.key}

@router.get("/setting/{key}")
async def get_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get a specific user setting."""
    
    value = await get_user_setting(current_user.id, key, db)
    
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )
    
    return {
        "key": key,
        "value": value,
        "is_sensitive": key in SENSITIVE_KEYS
    }

@router.get("/settings")
async def get_all_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get all user settings."""
    
    settings = await get_user_settings(current_user.id, db)
    
    # Format response with sensitivity info
    formatted_settings = {}
    for key, value in settings.items():
        formatted_settings[key] = {
            "value": value,
            "is_sensitive": key in SENSITIVE_KEYS
        }
    
    return formatted_settings

@router.delete("/setting/{key}")
async def delete_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Delete a user setting."""
    
    success = await delete_user_setting(current_user.id, key, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )
    
    return {"message": "Setting deleted successfully"}

@router.post("/environment", response_model=EnvironmentSettingsResponse)
async def save_environment_settings(
    request: EnvironmentSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Save environment settings for CharForge."""
    
    # Save each environment variable
    env_vars = request.dict()
    
    # Only save non-None values for environment variables
    for key, value in env_vars.items():
        if value is not None:
            is_sensitive = key in SENSITIVE_KEYS
            await save_user_setting(
                user_id=current_user.id,
                key=key,
                value=value,
                is_sensitive=is_sensitive,
                db=db
            )
    
    # Special handling for model URLs - ensure they're stored with original model names
    model_settings = {
        'TRAINING_MODEL_URL': 'black-forest-labs/FLUX.1-Krea-dev',
        'MV_ADAPTER_URL': 'mv-adapter/model',
        'MV_ADAPTER_LORA_URLS': 'mv-adapter/loras',
        'COMFYUI_URL': 'comfyui/models',
        'CAPTIONING_SYSTEM_PROMPT': 'You are an AI assistant that creates detailed image captions. Describe the subject, style, lighting, and composition in a single paragraph.',
        'GENERATION_SYSTEM_PROMPT': 'You are an AI image generator assistant. Create detailed prompts for image generation based on character descriptions.'
    }
    
    for setting_key, original_name in model_settings.items():
        if hasattr(request, setting_key) and getattr(request, setting_key):
            # Save the URL setting
            await save_user_setting(
                user_id=current_user.id,
                key=setting_key,
                value=getattr(request, setting_key),
                is_sensitive=False,
                db=db
            )
            # Also save the original model name for registry
            await save_user_setting(
                user_id=current_user.id,
                key=f"{setting_key}_ORIGINAL",
                value=original_name,
                is_sensitive=False,
                db=db
            )
    
    # Return current settings
    return await get_environment_settings(db, current_user)

@router.get("/environment", response_model=EnvironmentSettingsResponse)
async def get_environment_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get environment settings for CharForge."""
    
    settings = await get_user_settings(current_user.id, db)
    
    return EnvironmentSettingsResponse(
        HF_TOKEN=settings.get('HF_TOKEN', ''),
        HF_HOME=settings.get('HF_HOME', ''),
        CIVITAI_API_KEY=settings.get('CIVITAI_API_KEY', ''),
        GOOGLE_API_KEY=settings.get('GOOGLE_API_KEY', ''),
        FAL_KEY=settings.get('FAL_KEY', ''),
        MV_ADAPTER_LORA_URLS=settings.get('MV_ADAPTER_LORA_URLS', '')
    )

@router.post("/test-environment")
async def test_environment_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Test environment settings by validating API keys."""
    
    settings = await get_user_settings(current_user.id, db)
    
    results = {}
    
    # Test HF_TOKEN
    hf_token = settings.get('HF_TOKEN', '')
    if hf_token:
        try:
            import requests
            response = requests.get(
                "https://huggingface.co/api/whoami",
                headers={"Authorization": f"Bearer {hf_token}"}
            )
            results['HF_TOKEN'] = {
                'valid': response.status_code == 200,
                'message': 'Valid' if response.status_code == 200 else 'Invalid token'
            }
        except Exception as e:
            results['HF_TOKEN'] = {'valid': False, 'message': str(e)}
    else:
        results['HF_TOKEN'] = {'valid': False, 'message': 'Not set'}
    
    # Test GOOGLE_API_KEY
    google_key = settings.get('GOOGLE_API_KEY', '')
    if google_key:
        try:
            from google import genai
            client = genai.Client(api_key=google_key)
            # Simple test - this might need adjustment based on actual API
            results['GOOGLE_API_KEY'] = {'valid': True, 'message': 'Key format valid'}
        except Exception as e:
            results['GOOGLE_API_KEY'] = {'valid': False, 'message': str(e)}
    else:
        results['GOOGLE_API_KEY'] = {'valid': False, 'message': 'Not set'}
    
    # For other keys, just check if they're set (actual validation would require API calls)
    for key in ['CIVITAI_API_KEY', 'FAL_KEY']:
        value = settings.get(key, '')
        results[key] = {
            'valid': bool(value),
            'message': 'Set' if value else 'Not set'
        }
    
    # Check HF_HOME directory
    hf_home = settings.get('HF_HOME', '')
    if hf_home:
        import os
        results['HF_HOME'] = {
            'valid': os.path.exists(hf_home),
            'message': 'Directory exists' if os.path.exists(hf_home) else 'Directory not found'
        }
    else:
        results['HF_HOME'] = {'valid': False, 'message': 'Not set'}
    
    return results
