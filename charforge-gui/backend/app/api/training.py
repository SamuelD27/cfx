from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime
from pathlib import Path

from app.core.database import get_db, Character, TrainingSession, User
from app.core.auth import get_current_user_optional
from app.services.charforge_integration import CharForgeIntegration, CharacterConfig
from app.services.settings_service import get_user_env_vars

router = APIRouter()

# Pydantic models
class ModelConfig(BaseModel):
    base_model: str = "RunDiffusion/Juggernaut-XL-v9"
    vae_model: str = "madebyollin/sdxl-vae-fp16-fix"
    unet_model: Optional[str] = None
    adapter_path: str = "huanngzh/mv-adapter"
    scheduler: str = "ddpm"
    dtype: str = "float16"

class MVAdapterConfig(BaseModel):
    enabled: bool = False
    num_views: int = 6
    height: int = 768
    width: int = 768
    guidance_scale: float = 3.0
    reference_conditioning_scale: float = 1.0
    azimuth_degrees: List[int] = [0, 45, 90, 180, 270, 315]
    remove_background: bool = True

class AdvancedTrainingConfig(BaseModel):
    optimizer: str = "adamw"
    weight_decay: float = 1e-2
    lr_scheduler: str = "constant"
    gradient_checkpointing: bool = True
    train_text_encoder: bool = False
    noise_scheduler: str = "ddpm"
    gradient_accumulation: int = 1
    mixed_precision: str = "fp16"
    save_every: int = 250
    max_saves: int = 5

class TrainingRequest(BaseModel):
    character_id: int
    # Basic parameters
    steps: Optional[int] = 800
    batch_size: Optional[int] = 1
    learning_rate: Optional[float] = 8e-4
    train_dim: Optional[int] = 512
    rank_dim: Optional[int] = 8
    pulidflux_images: Optional[int] = 0

    # Model configuration
    model_config: Optional[ModelConfig] = ModelConfig()

    # MV Adapter configuration
    mv_adapter_config: Optional[MVAdapterConfig] = MVAdapterConfig()

    # Advanced training options
    advanced_config: Optional[AdvancedTrainingConfig] = AdvancedTrainingConfig()

    # ComfyUI model selection
    comfyui_checkpoint: Optional[str] = None
    comfyui_vae: Optional[str] = None
    comfyui_lora: Optional[str] = None

class TrainingResponse(BaseModel):
    id: int
    character_id: int
    status: str
    progress: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class CharacterResponse(BaseModel):
    id: int
    name: str
    status: str
    work_dir: str
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class CharacterCreateRequest(BaseModel):
    name: str
    input_image_path: str

# Global integration instance
charforge = CharForgeIntegration()

@router.post("/characters", response_model=CharacterResponse)
async def create_character(
    request: CharacterCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Create a new character."""

    # Validate input
    if not request.name or len(request.name.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character name is required"
        )

    # Sanitize character name
    sanitized_name = ''.join(c for c in request.name if c.isalnum() or c in '_-').strip()
    if not sanitized_name or len(sanitized_name) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid character name. Use only letters, numbers, underscores, and hyphens (max 100 chars)"
        )

    # Validate image path
    if not request.input_image_path or not Path(request.input_image_path).exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid input image path is required"
        )

    # Check if character name already exists for this user
    existing = db.query(Character).filter(
        Character.name == sanitized_name,
        Character.user_id == current_user.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character with this name already exists"
        )

    # Create character record
    character = Character(
        name=sanitized_name,
        user_id=current_user.id,
        input_image_path=request.input_image_path,
        work_dir=str(charforge.scratch_dir / sanitized_name),
        status="created"
    )

    db.add(character)
    db.commit()
    db.refresh(character)

    return character

@router.get("/characters", response_model=List[CharacterResponse])
async def list_characters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """List all characters for the current user."""
    characters = db.query(Character).filter(Character.user_id == current_user.id).all()
    return characters

@router.get("/characters/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get a specific character."""
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    return character

@router.post("/characters/{character_id}/train", response_model=TrainingResponse)
async def start_training(
    character_id: int,
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Start training for a character."""
    
    # Get character
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    # Check if there's already a running training session
    existing_session = db.query(TrainingSession).filter(
        TrainingSession.character_id == character_id,
        TrainingSession.status.in_(["pending", "running"])
    ).first()
    
    if existing_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Training session already in progress"
        )

    # Enhanced validation for training parameters
    steps = request.steps or 800
    learning_rate = request.learning_rate or 8e-4
    batch_size = request.batch_size or 1
    rank_dim = request.rank_dim or 8
    train_dim = request.train_dim or 512
    
    if steps < 100 or steps > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Steps must be between 100 and 10000"
        )

    if learning_rate < 1e-6 or learning_rate > 1e-2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Learning rate must be between 1e-6 and 1e-2"
        )

    if batch_size < 1 or batch_size > 16:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size must be between 1 and 16"
        )

    if rank_dim < 4 or rank_dim > 256:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rank dimension must be between 4 and 256"
        )

    if train_dim < 256 or train_dim > 2048:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Train dimension must be between 256 and 2048"
        )

    # Validate model configuration if provided
    if request.model_config:
        if request.model_config.dtype not in ["float16", "float32", "bfloat16"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid data type. Must be float16, float32, or bfloat16"
            )

    # Validate MV Adapter configuration if enabled
    if request.mv_adapter_config and request.mv_adapter_config.enabled:
        if request.mv_adapter_config.num_views < 4 or request.mv_adapter_config.num_views > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of views must be between 4 and 12"
            )

        if request.mv_adapter_config.guidance_scale < 1.0 or request.mv_adapter_config.guidance_scale > 20.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Guidance scale must be between 1.0 and 20.0"
            )

    # Create training session
    training_session = TrainingSession(
        character_id=character_id,
        user_id=current_user.id,
        steps=request.steps,
        batch_size=request.batch_size,
        learning_rate=request.learning_rate,
        train_dim=request.train_dim,
        rank_dim=request.rank_dim,
        pulidflux_images=request.pulidflux_images,
        status="pending"
    )
    
    db.add(training_session)
    db.commit()
    db.refresh(training_session)
    
    # Start training in background
    background_tasks.add_task(
        run_training_background,
        training_session.id,
        character,
        request,
        current_user.id
    )
    
    return training_session

async def run_training_background(
    session_id: int,
    character: Character,
    request: TrainingRequest,
    user_id: int
):
    """Background task to run training."""
    db = next(get_db())
    
    try:
        # Update session status
        session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
        session.status = "running"
        session.started_at = datetime.utcnow()
        db.commit()
        
        # Update character status
        character.status = "training"
        db.commit()
        
        # Get user environment variables
        env_vars = await get_user_env_vars(user_id, db)
        
        # Create CharForge config
        config = CharacterConfig(
            name=character.name,
            input_image=character.input_image_path,
            work_dir=character.work_dir,
            steps=steps,
            batch_size=batch_size,
            learning_rate=learning_rate,
            train_dim=train_dim,
            rank_dim=rank_dim,
            pulidflux_images=request.pulidflux_images or 0,

            # Model configuration
            model_config=request.model_config or ModelConfig(),
            mv_adapter_config=request.mv_adapter_config or MVAdapterConfig(),
            advanced_config=request.advanced_config or AdvancedTrainingConfig(),

            # ComfyUI model paths
            comfyui_checkpoint=request.comfyui_checkpoint or "",
            comfyui_vae=request.comfyui_vae or "",
            comfyui_lora=request.comfyui_lora or ""
        )
        
        # Progress callback
        def update_progress(progress: float, message: str):
            session.progress = progress
            db.commit()
        
        # Run training
        result = await charforge.run_training(config, env_vars, update_progress)
        
        # Update session with results
        session.status = "completed" if result["success"] else "failed"
        session.completed_at = datetime.utcnow()
        session.progress = 100.0 if result["success"] else session.progress
        
        # Update character status
        character.status = "completed" if result["success"] else "failed"
        if result["success"]:
            character.completed_at = datetime.utcnow()
        
        db.commit()
        
    except Exception as e:
        # Handle errors
        session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
        session.status = "failed"
        session.completed_at = datetime.utcnow()
        
        character.status = "failed"
        
        db.commit()
    
    finally:
        db.close()

@router.get("/characters/{character_id}/training", response_model=List[TrainingResponse])
async def get_training_sessions(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get training sessions for a character."""
    
    # Verify character ownership
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    sessions = db.query(TrainingSession).filter(
        TrainingSession.character_id == character_id
    ).order_by(TrainingSession.created_at.desc()).all()
    
    return sessions

@router.get("/training/{session_id}", response_model=TrainingResponse)
async def get_training_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get a specific training session."""

    # Validate session_id
    if session_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID"
        )

    session = db.query(TrainingSession).filter(
        TrainingSession.id == session_id,
        TrainingSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found"
        )

    return session
