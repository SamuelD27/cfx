from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime

from app.core.database import get_db, Character, InferenceJob, User
from app.core.auth import get_current_user_optional
from app.services.charforge_integration import CharForgeIntegration, InferenceConfig
from app.services.settings_service import get_user_env_vars

router = APIRouter()

# Pydantic models
class InferenceRequest(BaseModel):
    character_id: int
    prompt: str
    lora_weight: Optional[float] = 0.73
    test_dim: Optional[int] = 1024
    do_optimize_prompt: Optional[bool] = True
    output_filenames: Optional[List[str]] = None
    batch_size: Optional[int] = 4
    num_inference_steps: Optional[int] = 30
    fix_outfit: Optional[bool] = False
    safety_check: Optional[bool] = True
    face_enhance: Optional[bool] = False

class InferenceResponse(BaseModel):
    id: int
    character_id: int
    prompt: str
    optimized_prompt: Optional[str]
    status: str
    output_paths: Optional[List[str]]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class InferenceJobResponse(BaseModel):
    id: int
    character_id: int
    character_name: str
    prompt: str
    optimized_prompt: Optional[str]
    status: str
    output_paths: Optional[List[str]]
    lora_weight: float
    test_dim: int
    batch_size: int
    created_at: datetime
    completed_at: Optional[datetime]

# Global integration instance
charforge = CharForgeIntegration()

@router.post("/generate", response_model=InferenceResponse)
async def generate_images(
    request: InferenceRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Generate images using a trained character LoRA."""
    
    # Get character
    character = db.query(Character).filter(
        Character.id == request.character_id,
        Character.user_id == current_user.id
    ).first()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    # Check if character has completed training
    if character.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character training not completed"
        )
    
    # Create inference job
    inference_job = InferenceJob(
        character_id=request.character_id,
        user_id=current_user.id,
        prompt=request.prompt,
        lora_weight=request.lora_weight,
        test_dim=request.test_dim,
        batch_size=request.batch_size,
        num_inference_steps=request.num_inference_steps,
        do_optimize_prompt=request.do_optimize_prompt,
        fix_outfit=request.fix_outfit,
        safety_check=request.safety_check,
        face_enhance=request.face_enhance,
        status="pending"
    )
    
    db.add(inference_job)
    db.commit()
    db.refresh(inference_job)
    
    # Start inference in background
    background_tasks.add_task(
        run_inference_background,
        inference_job.id,
        character,
        request,
        current_user.id
    )
    
    return inference_job

async def run_inference_background(
    job_id: int,
    character: Character,
    request: InferenceRequest,
    user_id: int
):
    """Background task to run inference."""
    db = next(get_db())
    
    try:
        # Update job status
        job = db.query(InferenceJob).filter(InferenceJob.id == job_id).first()
        job.status = "running"
        db.commit()
        
        # Get user environment variables
        env_vars = await get_user_env_vars(user_id, db)
        
        # Create CharForge config
        config = InferenceConfig(
            character_name=character.name,
            prompt=request.prompt,
            work_dir=character.work_dir,
            lora_weight=request.lora_weight or 0.73,
            test_dim=request.test_dim or 1024,
            do_optimize_prompt=request.do_optimize_prompt if request.do_optimize_prompt is not None else True,
            output_filenames=request.output_filenames,
            batch_size=request.batch_size or 4,
            num_inference_steps=request.num_inference_steps or 30,
            fix_outfit=request.fix_outfit if request.fix_outfit is not None else False,
            safety_check=request.safety_check if request.safety_check is not None else True,
            face_enhance=request.face_enhance if request.face_enhance is not None else False
        )
        
        # Run inference
        result = await charforge.run_inference(config, env_vars)
        
        # Update job with results
        job.status = "completed" if result["success"] else "failed"
        job.completed_at = datetime.utcnow()
        
        if result["success"]:
            job.output_paths = json.dumps(result["output_files"])
            
            # Extract optimized prompt from output if available
            output_lines = result["output"].split('\n')
            for line in output_lines:
                if "Optimized Prompt:" in line:
                    # Find the next non-empty line
                    idx = output_lines.index(line)
                    if idx + 1 < len(output_lines):
                        job.optimized_prompt = output_lines[idx + 1].strip()
                    break
        
        db.commit()
        
    except Exception as e:
        # Handle errors
        job = db.query(InferenceJob).filter(InferenceJob.id == job_id).first()
        job.status = "failed"
        job.completed_at = datetime.utcnow()
        db.commit()
    
    finally:
        db.close()

@router.get("/jobs", response_model=List[InferenceJobResponse])
async def list_inference_jobs(
    character_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """List inference jobs for the current user."""
    
    query = db.query(InferenceJob, Character).join(
        Character, InferenceJob.character_id == Character.id
    ).filter(InferenceJob.user_id == current_user.id)
    
    if character_id:
        query = query.filter(InferenceJob.character_id == character_id)
    
    jobs = query.order_by(InferenceJob.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for job, character in jobs:
        output_paths = None
        if job.output_paths:
            try:
                output_paths = json.loads(job.output_paths)
            except:
                output_paths = []
        
        result.append(InferenceJobResponse(
            id=job.id,
            character_id=job.character_id,
            character_name=character.name,
            prompt=job.prompt,
            optimized_prompt=job.optimized_prompt,
            status=job.status,
            output_paths=output_paths,
            lora_weight=job.lora_weight,
            test_dim=job.test_dim,
            batch_size=job.batch_size,
            created_at=job.created_at,
            completed_at=job.completed_at
        ))
    
    return result

@router.get("/jobs/{job_id}", response_model=InferenceResponse)
async def get_inference_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get a specific inference job."""
    
    job = db.query(InferenceJob).filter(
        InferenceJob.id == job_id,
        InferenceJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inference job not found"
        )
    
    # Parse output paths
    output_paths = None
    if job.output_paths:
        try:
            output_paths = json.loads(job.output_paths)
        except:
            output_paths = []
    
    return InferenceResponse(
        id=job.id,
        character_id=job.character_id,
        prompt=job.prompt,
        optimized_prompt=job.optimized_prompt,
        status=job.status,
        output_paths=output_paths,
        created_at=job.created_at,
        completed_at=job.completed_at
    )

@router.get("/characters/{character_id}/info")
async def get_character_info(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get detailed information about a character including LoRA status."""
    
    # Get character from database
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    # Get CharForge info
    charforge_info = charforge.get_character_info(character.name, character.work_dir)
    
    return {
        "database_info": {
            "id": character.id,
            "name": character.name,
            "status": character.status,
            "work_dir": character.work_dir,
            "created_at": character.created_at,
            "completed_at": character.completed_at
        },
        "charforge_info": charforge_info
    }

@router.get("/available-characters")
async def list_available_characters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """List all characters available for inference (completed training)."""
    
    characters = db.query(Character).filter(
        Character.user_id == current_user.id,
        Character.status == "completed"
    ).all()
    
    result = []
    for character in characters:
        charforge_info = charforge.get_character_info(character.name, character.work_dir)
        if charforge_info["has_lora"]:
            result.append({
                "id": character.id,
                "name": character.name,
                "work_dir": character.work_dir,
                "lora_path": charforge_info["lora_path"],
                "completed_at": character.completed_at
            })
    
    return result
