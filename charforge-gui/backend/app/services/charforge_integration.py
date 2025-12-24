import os
import sys
import subprocess
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
import shutil

from app.core.config import settings

@dataclass
class ModelConfig:
    """Model configuration for training."""
    base_model: str = "RunDiffusion/Juggernaut-XL-v9"
    vae_model: str = "madebyollin/sdxl-vae-fp16-fix"
    unet_model: str = None
    adapter_path: str = "huanngzh/mv-adapter"
    scheduler: str = "ddpm"
    dtype: str = "float16"

@dataclass
class MVAdapterConfig:
    """MV Adapter configuration."""
    enabled: bool = False
    num_views: int = 6
    height: int = 768
    width: int = 768
    guidance_scale: float = 3.0
    reference_conditioning_scale: float = 1.0
    azimuth_degrees: List[int] = None
    remove_background: bool = True

    def __post_init__(self):
        if self.azimuth_degrees is None:
            self.azimuth_degrees = [0, 45, 90, 180, 270, 315]

@dataclass
class AdvancedTrainingConfig:
    """Advanced training configuration."""
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

@dataclass
class CharacterConfig:
    """Configuration for character generation and training."""
    name: str
    input_image: str
    work_dir: str = None
    steps: int = 800
    batch_size: int = 1
    learning_rate: float = 8e-4
    train_dim: int = 512
    rank_dim: int = 8
    pulidflux_images: int = 0

    # Model configurations
    model_config: ModelConfig = None
    mv_adapter_config: MVAdapterConfig = None
    advanced_config: AdvancedTrainingConfig = None

    # ComfyUI model paths
    comfyui_checkpoint: str = None
    comfyui_vae: str = None
    comfyui_lora: str = None

    def __post_init__(self):
        if self.model_config is None:
            self.model_config = ModelConfig()
        if self.mv_adapter_config is None:
            self.mv_adapter_config = MVAdapterConfig()
        if self.advanced_config is None:
            self.advanced_config = AdvancedTrainingConfig()

@dataclass
class InferenceConfig:
    """Configuration for character inference."""
    character_name: str
    prompt: str
    work_dir: str = None
    lora_weight: float = 0.73
    test_dim: int = 1024
    do_optimize_prompt: bool = True
    output_filenames: List[str] = None
    batch_size: int = 4
    num_inference_steps: int = 30
    fix_outfit: bool = False
    safety_check: bool = True
    face_enhance: bool = False

class CharForgeIntegration:
    """Integration layer for CharForge Python scripts."""
    
    def __init__(self):
        self.charforge_root = settings.CHARFORGE_ROOT
        self.scratch_dir = settings.CHARFORGE_SCRATCH_DIR
        
        # Ensure CharForge directories exist
        os.makedirs(self.scratch_dir, exist_ok=True)
    
    def setup_environment(self, env_vars: Dict[str, str]) -> Dict[str, str]:
        """Set up environment variables for CharForge."""
        env = os.environ.copy()

        # Always set APP_PATH (required)
        env['APP_PATH'] = str(self.charforge_root)

        # Only set non-empty environment variables
        # This allows load_dotenv() in subprocess to load from .env file
        # when keys are not configured in GUI settings
        for key in ['HF_HOME', 'HF_TOKEN', 'CIVITAI_API_KEY', 'GOOGLE_API_KEY', 'FAL_KEY']:
            value = env_vars.get(key, '')
            if value:  # Only set if non-empty
                env[key] = value

        return env

    def _validate_config(self, config) -> bool:
        """Validate configuration parameters to prevent injection attacks."""
        try:
            # Validate numeric parameters
            if not (1 <= int(config.steps) <= 10000):
                return False
            if not (1 <= int(config.batch_size) <= 32):
                return False
            if not (0.0001 <= float(config.learning_rate) <= 1.0):
                return False
            if not (64 <= int(config.train_dim) <= 2048):
                return False
            if not (1 <= int(config.rank_dim) <= 128):
                return False
            if not (0 <= int(config.pulidflux_images) <= 100):
                return False

            # Validate string parameters
            if not config.name or not config.name.replace('_', '').replace('-', '').isalnum():
                return False
            if len(config.name) > 100:
                return False

            # Validate file paths
            if not Path(config.input_image).exists():
                return False

            return True
        except (ValueError, TypeError):
            return False

    def _sanitize_string(self, value: str) -> str:
        """Sanitize string input to prevent injection."""
        # Only allow alphanumeric, underscore, and hyphen
        return ''.join(c for c in value if c.isalnum() or c in '_-')

    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is safe (no traversal attacks)."""
        try:
            # Resolve the path and check if it's within allowed directories
            resolved_path = path.resolve()
            allowed_roots = [
                self.charforge_root.resolve(),
                self.scratch_dir.resolve(),
                Path.cwd().resolve()
            ]

            return any(
                str(resolved_path).startswith(str(root))
                for root in allowed_roots
            )
        except (OSError, ValueError):
            return False

    def _validate_inference_config(self, config) -> bool:
        """Validate inference configuration parameters."""
        try:
            # Validate numeric parameters
            if not (0.1 <= float(config.lora_weight) <= 2.0):
                return False
            if not (256 <= int(config.test_dim) <= 2048):
                return False
            if not (1 <= int(config.batch_size) <= 16):
                return False
            if not (10 <= int(config.num_inference_steps) <= 200):
                return False

            # Validate string parameters
            if not config.character_name or len(config.character_name) > 100:
                return False
            if not config.prompt or len(config.prompt) > 2000:
                return False

            return True
        except (ValueError, TypeError):
            return False

    def _sanitize_prompt(self, prompt: str) -> str:
        """Sanitize prompt input while preserving readability."""
        # Remove potentially dangerous characters but keep normal punctuation
        dangerous_chars = ['`', '$', '\\', ';', '|', '&', '>', '<']
        sanitized = prompt
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        return sanitized.strip()[:2000]  # Limit length

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        # Remove path separators and dangerous characters
        safe_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-')
        return ''.join(c for c in filename if c in safe_chars)[:100]

    def _is_safe_filename(self, filename: str) -> bool:
        """Check if filename is safe."""
        if not filename or '..' in filename or '/' in filename or '\\' in filename:
            return False
        return len(filename) <= 100 and filename.replace('.', '').replace('_', '').replace('-', '').isalnum()
    
    async def run_training(
        self,
        config: CharacterConfig,
        env_vars: Dict[str, str],
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Dict[str, any]:
        """Run character training workflow."""

        # Validate inputs to prevent command injection
        if not self._validate_config(config):
            return {
                "success": False,
                "error": "Invalid configuration parameters",
                "output": ""
            }

        # Set up environment
        env = self.setup_environment(env_vars)

        # Prepare command with validated parameters
        cmd = [
            sys.executable,
            str(self.charforge_root / "train_character.py"),
            "--name", self._sanitize_string(config.name),
            "--input", str(Path(config.input_image).resolve()),
            "--steps", str(int(config.steps)),
            "--batch_size", str(int(config.batch_size)),
            "--lr", str(float(config.learning_rate)),
            "--train_dim", str(int(config.train_dim)),
            "--rank_dim", str(int(config.rank_dim)),
            "--pulidflux_images", str(int(config.pulidflux_images))
        ]

        # Add model configuration
        if config.model_config:
            cmd.extend(["--base_model", config.model_config.base_model])
            cmd.extend(["--vae_model", config.model_config.vae_model])
            if config.model_config.unet_model:
                cmd.extend(["--unet_model", config.model_config.unet_model])
            cmd.extend(["--scheduler", config.model_config.scheduler])
            cmd.extend(["--dtype", config.model_config.dtype])

        # Add MV Adapter configuration
        if config.mv_adapter_config and config.mv_adapter_config.enabled:
            cmd.extend(["--use_mv_adapter"])
            cmd.extend(["--adapter_path", config.mv_adapter_config.adapter_path])
            cmd.extend(["--num_views", str(config.mv_adapter_config.num_views)])
            cmd.extend(["--mv_height", str(config.mv_adapter_config.height)])
            cmd.extend(["--mv_width", str(config.mv_adapter_config.width)])
            cmd.extend(["--guidance_scale", str(config.mv_adapter_config.guidance_scale)])
            cmd.extend(["--reference_conditioning_scale", str(config.mv_adapter_config.reference_conditioning_scale)])
            cmd.extend(["--azimuth_degrees", ",".join(map(str, config.mv_adapter_config.azimuth_degrees))])
            if config.mv_adapter_config.remove_background:
                cmd.extend(["--remove_background"])

        # Add advanced training configuration
        if config.advanced_config:
            cmd.extend(["--optimizer", config.advanced_config.optimizer])
            cmd.extend(["--weight_decay", str(config.advanced_config.weight_decay)])
            cmd.extend(["--lr_scheduler", config.advanced_config.lr_scheduler])
            cmd.extend(["--gradient_accumulation", str(config.advanced_config.gradient_accumulation)])
            cmd.extend(["--mixed_precision", config.advanced_config.mixed_precision])
            cmd.extend(["--save_every", str(config.advanced_config.save_every)])
            cmd.extend(["--max_saves", str(config.advanced_config.max_saves)])

            if config.advanced_config.gradient_checkpointing:
                cmd.extend(["--gradient_checkpointing"])
            if config.advanced_config.train_text_encoder:
                cmd.extend(["--train_text_encoder"])

        # Add ComfyUI model paths (these will be copied to standard names)
        if config.comfyui_checkpoint:
            cmd.extend(["--comfyui_checkpoint", config.comfyui_checkpoint])
        if config.comfyui_vae:
            cmd.extend(["--comfyui_vae", config.comfyui_vae])
        if config.comfyui_lora:
            cmd.extend(["--comfyui_lora", config.comfyui_lora])

        if config.work_dir:
            # Validate and sanitize work directory path
            work_dir = Path(config.work_dir).resolve()
            if not self._is_safe_path(work_dir):
                return {
                    "success": False,
                    "error": "Invalid work directory path",
                    "output": ""
                }
            cmd.extend(["--work_dir", str(work_dir)])
        
        # Run the process
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
                cwd=str(self.charforge_root)
            )
            
            output_lines = []
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                line_str = line.decode().strip()
                output_lines.append(line_str)
                
                # Parse progress if callback provided
                if progress_callback:
                    progress = self._parse_training_progress(line_str)
                    if progress is not None:
                        progress_callback(progress, line_str)
            
            await process.wait()
            
            return {
                "success": process.returncode == 0,
                "returncode": process.returncode,
                "output": "\n".join(output_lines),
                "work_dir": config.work_dir or str(self.scratch_dir / config.name)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": ""
            }
    
    async def run_inference(
        self,
        config: InferenceConfig,
        env_vars: Dict[str, str]
    ) -> Dict[str, any]:
        """Run character inference."""

        # Validate inference config
        if not self._validate_inference_config(config):
            return {
                "success": False,
                "error": "Invalid inference configuration parameters",
                "output": "",
                "output_files": []
            }

        # Set up environment
        env = self.setup_environment(env_vars)

        # Prepare command with validated parameters
        cmd = [
            sys.executable,
            str(self.charforge_root / "test_character.py"),
            "--character_name", self._sanitize_string(config.character_name),
            "--prompt", self._sanitize_prompt(config.prompt),
            "--lora_weight", str(float(config.lora_weight)),
            "--test_dim", str(int(config.test_dim)),
            "--batch_size", str(int(config.batch_size)),
            "--num_inference_steps", str(int(config.num_inference_steps))
        ]
        
        # Add optional flags with validation
        if config.work_dir:
            work_dir = Path(config.work_dir).resolve()
            if self._is_safe_path(work_dir):
                cmd.extend(["--work_dir", str(work_dir)])

        if config.output_filenames:
            # Validate output filenames
            safe_filenames = [
                self._sanitize_filename(f) for f in config.output_filenames
                if self._is_safe_filename(f)
            ]
            if safe_filenames:
                cmd.extend(["--output_filenames"] + safe_filenames)

        if not config.do_optimize_prompt:
            cmd.append("--no_optimize_prompt")

        if config.fix_outfit:
            cmd.append("--fix_outfit")

        if not config.safety_check:
            cmd.append("--no_safety_check")

        if config.face_enhance:
            cmd.append("--face_enhance")
        
        # Run the process
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
                cwd=str(self.charforge_root)
            )
            
            output_lines = []
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                line_str = line.decode().strip()
                output_lines.append(line_str)
            
            await process.wait()
            
            # Parse output files
            output_files = self._parse_inference_output(output_lines, config)
            
            return {
                "success": process.returncode == 0,
                "returncode": process.returncode,
                "output": "\n".join(output_lines),
                "output_files": output_files
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "output_files": []
            }
    
    def _parse_training_progress(self, line: str) -> Optional[float]:
        """Parse training progress from output line."""
        # Look for progress indicators in the output
        # This is a simplified version - you might need to adjust based on actual output
        if "Step" in line and "/" in line:
            try:
                # Extract step numbers like "Step 100/800"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "Step" and i + 1 < len(parts):
                        step_info = parts[i + 1]
                        if "/" in step_info:
                            current, total = step_info.split("/")
                            return float(current) / float(total) * 100
            except:
                pass
        return None
    
    def _parse_inference_output(self, output_lines: List[str], config: InferenceConfig) -> List[str]:
        """Parse inference output to extract generated file paths."""
        output_files = []
        for line in output_lines:
            if "Saved image to:" in line:
                # Extract file path from line like "✅ Saved image to: /path/to/file.jpg"
                path = line.split("Saved image to:")[-1].strip()
                output_files.append(path)
        return output_files
    
    def get_character_info(self, character_name: str, work_dir: str = None) -> Dict[str, any]:
        """Get information about a trained character."""
        if work_dir is None:
            work_dir = self.scratch_dir / character_name
        else:
            work_dir = Path(work_dir)
        
        info = {
            "name": character_name,
            "exists": work_dir.exists(),
            "work_dir": str(work_dir),
            "has_lora": False,
            "has_sheet": False,
            "sheet_images": [],
            "lora_path": None
        }
        
        if work_dir.exists():
            # Check for LoRA
            lora_dir = work_dir / "char"
            lora_file = lora_dir / "char.safetensors"
            if lora_file.exists():
                info["has_lora"] = True
                info["lora_path"] = str(lora_file)
            
            # Check for character sheet
            sheet_dir = work_dir / "sheet"
            if sheet_dir.exists():
                info["has_sheet"] = True
                # Get sheet images
                for ext in ["*.png", "*.jpg", "*.jpeg"]:
                    info["sheet_images"].extend([str(p) for p in sheet_dir.glob(ext)])
        
        return info
    
    def list_characters(self) -> List[Dict[str, any]]:
        """List all available characters."""
        characters = []
        if self.scratch_dir.exists():
            for char_dir in self.scratch_dir.iterdir():
                if char_dir.is_dir():
                    char_info = self.get_character_info(char_dir.name, str(char_dir))
                    characters.append(char_info)
        return characters
