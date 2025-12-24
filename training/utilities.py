import base64
import cv2
import fal_client
import io
import numpy as np
import os
import requests
import sys
from PIL import Image
from google import genai
from google.genai import types

# Get the absolute path to the ComfyUI_AutoCropFaces directory
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(current_dir)  # Get parent directory of training
autocrop_path = os.path.join(repo_root, 'ComfyUI_AutoCropFaces')

sys.path.append(autocrop_path)

from Pytorch_Retinaface.pytorch_retinaface import Pytorch_RetinaFace


def get_system_prompt():
    return """You are a concise image captioning assistant.

Your task is to provide a brief caption for the given image (around 3 sentences).
Focus on describing:
- The subject (person, character, etc.)
- Physical appearance and attributes
- Clothing and accessories
- Facial features and expression

IMPORTANT: Completely IGNORE the background - do not mention it at all.
Remain objective – do not reference known characters, franchises, or people, even if recognizable.
Avoid making assumptions about things that aren't visible in the image.
"""


def image_to_base64(image):
    """Convert a PIL image to base64 encoded string."""
    if not isinstance(image, Image.Image):
        image = Image.fromarray(image)

    # Convert to RGB if it has an alpha channel
    if image.mode == 'RGBA':
        image = image.convert('RGB')

    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str


def get_google_genai_client():
    """Initialize and return the Google GenAI client."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables!")
    return genai.Client(api_key=api_key)


def generate_caption(image):
    """Generate a detailed caption for the image"""
    client = get_google_genai_client()

    # Convert PIL image if needed
    if not isinstance(image, Image.Image):
        image = Image.fromarray(image)

    # Convert to RGB if it has an alpha channel
    if image.mode == 'RGBA':
        image = image.convert('RGB')

    system_prompt = get_system_prompt()
    contents = [image, "Please provide a detailed caption for this image."]

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt
        )
    )
    caption = response.text.strip() if response.text else ""
    return caption


def ensure_captions_for_all_images(dataset_dir):
    """
    Ensure all images in the dataset directory have corresponding caption files.
    Generate captions for images that don't have txt files.

    Args:
        dataset_dir (str): Path to the dataset directory containing images

    Returns:
        int: Number of captions generated
    """
    import glob

    # Supported image extensions
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.webp']

    # Find all image files
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(dataset_dir, ext)))
        image_files.extend(glob.glob(os.path.join(dataset_dir, ext.upper())))

    captions_generated = 0

    for image_path in image_files:
        # Get the corresponding txt file path
        base_name = os.path.splitext(image_path)[0]
        txt_path = base_name + '.txt'

        # Check if caption file already exists
        if not os.path.exists(txt_path):
            try:
                print(f"Generating caption for {os.path.basename(image_path)}...")

                # Load and process the image
                image = Image.open(image_path).convert('RGB')

                # Generate caption
                caption = generate_caption(image)

                # Save caption to txt file
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(caption)

                print(f"Generated caption: {caption}")
                captions_generated += 1

            except Exception as e:
                print(f"Error generating caption for {os.path.basename(image_path)}: {e}")

    if captions_generated > 0:
        print(f"Generated {captions_generated} new captions")
    else:
        print("All images already have caption files")

    return captions_generated


def ensure_images_1024x1024(dataset_dir):
    """
    Ensure all images in the dataset directory are 1024x1024.
    Resize and crop images that are not already 1024x1024.

    Args:
        dataset_dir (str): Path to the dataset directory containing images

    Returns:
        int: Number of images processed
    """
    import glob

    # Supported image extensions
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.webp']

    # Find all image files
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(dataset_dir, ext)))
        image_files.extend(glob.glob(os.path.join(dataset_dir, ext.upper())))

    images_processed = 0
    target_size = 1024

    for image_path in image_files:
        try:
            # Load the image
            image = Image.open(image_path).convert('RGB')
            width, height = image.size

            # Check if image is already 1024x1024
            if width == target_size and height == target_size:
                continue

            print(f"Processing {os.path.basename(image_path)} ({width}x{height} -> {target_size}x{target_size})")

            # Convert to square first using the existing function
            square_image = rectangle_to_square(image)

            # Resize to 1024x1024
            processed_image = square_image.resize((target_size, target_size), Image.Resampling.LANCZOS)

            # Save the processed image (overwrite original)
            processed_image.save(image_path, format='PNG', quality=95)

            images_processed += 1

        except Exception as e:
            print(f"Error processing {os.path.basename(image_path)}: {e}")

    if images_processed > 0:
        print(f"Processed {images_processed} images to 1024x1024")
    else:
        print("All images are already 1024x1024")

    return images_processed


def preprocess_dataset_before_training(dataset_dir):
    """
    Complete preprocessing pipeline for dataset before training:
    1. Ensure all images are 1024x1024
    2. Generate captions for images without txt files

    Args:
        dataset_dir (str): Path to the dataset directory

    Returns:
        dict: Summary of preprocessing results
    """
    print(f"Starting dataset preprocessing for: {dataset_dir}")

    # Step 1: Ensure all images are 1024x1024
    print("\nStep 1: Ensuring all images are 1024x1024...")
    images_processed = ensure_images_1024x1024(dataset_dir)

    # Step 2: Generate captions for images without txt files
    print("\nStep 2: Generating captions for images without txt files...")
    captions_generated = ensure_captions_for_all_images(dataset_dir)

    results = {
        'images_processed': images_processed,
        'captions_generated': captions_generated,
        'dataset_dir': dataset_dir
    }

    print(f"\nDataset preprocessing complete:")
    print(f"  - Images processed to 1024x1024: {images_processed}")
    print(f"  - Captions generated: {captions_generated}")

    return results


def upscale_image(image_path, output_path=None, scale=1.5, model="RealESRGAN_x4plus", face_enhance=True,
                  output_format="png"):
    """
    Upscale an image using fal.ai's ESRGAN service (synchronous version)

    Args:
        image_path: Path to the image file
        output_path: Path where the upscaled image will be saved (default: None, will return PIL Image)
        scale: Scaling factor (default: 1.5)
        model: Model to use (default: "RealESRGAN_x4plus")
        face_enhance: Whether to enhance faces (default: True)
        output_format: Output image format (default: "png")

    Returns:
        If output_path is provided: Path to the saved image
        If output_path is None: PIL Image of the upscaled result
    """
    # Load image from path
    with open(image_path, "rb") as img_file:
        img_data = img_file.read()
        img_str = base64.b64encode(img_data).decode("utf-8")

    img_url = f"data:image/png;base64,{img_str}"

    # Submit to fal.ai API synchronously
    result = fal_client.subscribe(
        "fal-ai/esrgan",
        arguments={
            "image_url": img_url,
            "scale": scale,
            "model": model,
            "output_format": output_format,
            "face": face_enhance
        },
        with_logs=False
    )

    # Parse the result
    if "image" in result:
        # According to fal.ai docs, the result has format: {"image": {"url": "...", "content_type": "...", etc.}}
        if isinstance(result["image"], dict) and "url" in result["image"]:
            # Download image from the provided URL
            response = requests.get(result["image"]["url"])
            image_data = response.content
        else:
            # Fallback for any other format
            raise ValueError(f"Unexpected image format in result: {result['image']}")

        upscaled_image = Image.open(io.BytesIO(image_data))

        # Save to output path if provided
        if output_path:
            upscaled_image.save(output_path)
            return output_path

        return upscaled_image
    else:
        raise ValueError("No image was returned from the upscale service")


def rectangle_to_square(image, background_color=(128, 128, 128)):
    """
    Convert a rectangular image to a square by adding padding with a background color.
    If the image is already square, returns the original image.
    
    Args:
        image: PIL Image or numpy array
        background_color: RGB tuple for the background color (default: gray)
    
    Returns:
        A square PIL Image with the original image centered
    """
    if not isinstance(image, Image.Image):
        image = Image.fromarray(image)

    # Get the original dimensions
    width, height = image.size

    # If image is already square, return the original
    if width == height:
        return image

    # Calculate the target size (use the larger dimension)
    target_size = max(width, height)

    # Create a new square image with the background color
    result = Image.new('RGB', (target_size, target_size), background_color)

    # Calculate position to paste the original image (centered)
    x_offset = (target_size - width) // 2
    y_offset = (target_size - height) // 2

    # Paste the original image onto the square background
    result.paste(image, (x_offset, y_offset))

    return result


def crop_face(image_path, output_dir, output_name, scale_factor=4.0):
    image = Image.open(image_path).convert("RGB")

    img_raw = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    img_raw = img_raw.astype(np.float32)

    rf = Pytorch_RetinaFace(
        cfg='mobile0.25',
        pretrained_path='./weights/mobilenet0.25_Final.pth',
        confidence_threshold=0.02,
        nms_threshold=0.4,
        vis_thres=0.6
    )

    dets = rf.detect_faces(img_raw)
    print("Dets: ", dets)

    # Instead of asserting, handle multiple faces gracefully
    if len(dets) == 0:
        print("No faces detected!")
        return False

    # If multiple faces detected, use the one with highest confidence
    if len(dets) > 1:
        print(f"Warning: {len(dets)} faces detected, using the one with highest confidence")
        # Assuming dets is a list of [bbox, landmark, score] and we want to sort by score
        dets = sorted(dets, key=lambda x: x[2], reverse=True)  # Sort by confidence score
        # Just keep the highest confidence detection
        dets = [dets[0]]

    # Pass the scale_factor to center_and_crop_rescale for adjustable crop size
    try:
        # Unpack the tuple correctly - the function returns (cropped_imgs, bbox_infos)
        cropped_imgs, bbox_infos = rf.center_and_crop_rescale(img_raw, dets, shift_factor=0.45,
                                                              scale_factor=scale_factor)

        # Assuming cropped_imgs is a list or tuple (cropped_imgs, bbox_infos)
        for i, (cropped_img, bbox_info) in enumerate(zip(cropped_imgs, bbox_infos)):
            # Convert BGR to RGB
            cropped_img_rgb = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB)

            # Convert to PIL Image
            cropped_pil = Image.fromarray(cropped_img_rgb.astype(np.uint8))

            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            # Save to output path
            out_name = output_name if isinstance(output_name, str) else f"face_{i}.png"
            output_path = os.path.join(output_dir, out_name)
            cropped_pil.save(output_path)

            print(f"Face cropped and saved to {output_path}")
            return output_path
    except Exception as e:
        print(f"Error cropping face: {e}")
        return False


def get_upscale_factor(image: str = None, input_size=None, target_size=768):
    """Calculate the scale factor needed to upscale an image to approximately targetxtarget"""

    if input_size is None:
        image = Image.open(image).convert("RGB")
        width, height = image.size
    else:
        width, height = input_size

    width_scale = target_size / width
    height_scale = target_size / height

    scale_factor = max(width_scale, height_scale)
    return scale_factor


def resize_if_large(image, max_size=1536):
    """
    Resize a square image if its dimensions exceed the specified maximum size.
    
    Args:
        image: PIL Image object (assumed to be square)
        max_size: Maximum allowed dimension (width/height) in pixels
        
    Returns:
        PIL Image: Resized image if needed, or original image if already small enough
    """
    if not isinstance(image, Image.Image):
        image = Image.fromarray(image)

    width, height = image.size

    # Verify image is square (should be after rectangle_to_square)
    if width != height:
        print(f"Warning: Expected square image but got {width}x{height}")

    # If image is already small enough, return the original
    if width <= max_size:
        return image

    # Resize the square image
    resized_image = image.resize((max_size, max_size), Image.Resampling.LANCZOS)

    return resized_image
