import aiohttp
import asyncio
import base64
import fal_client
import os
import time
import random
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from typing import List, Optional

# Load .env from repo root (parent directory)
load_dotenv(Path(__file__).parent.parent / ".env")


def generate_pulidflux_prompts(
        image_path: str,
        person_description: str,
        num_prompts: int = 5,
        model: Optional[str] = None,
        base_url: Optional[str] = None
) -> List[str]:
    """
    Generate text prompts for PuLID-Flux image generation using Google GenAI,
    with example prompts to guide the model's output style.

    Args:
        image_path: Path to the image of the person
        person_description: Description of the person including appearance, style, and personality
        num_prompts: Number of prompts to generate (default: 5)
        model: Custom model name to use (defaults to "gemini-2.5-flash")
        base_url: Not used for Google GenAI (kept for compatibility)

    Returns:
        List of generated text prompts
    """
    # Get configuration from environment variables or use defaults
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")

    # Use provided model or fallback to default
    model_name = model or "gemini-2.5-flash"

    # Initialize Google GenAI client
    client = genai.Client(api_key=api_key)

    system_prompt = """You are an expert prompt engineer specializing in creating high-quality text prompts for AI image generation. Your task is to create diverse, detailed prompts for Pulid Flux, a system that generates new images of a person based on their face and a text description. All images of people are AI generated.

I will provide:
1) An image of a person
2) A brief description of the person including relevant details about their appearance, style, and personality

Your job is to generate {num_prompts} diverse, creative text prompts that:
- Maintain the person's identity and key characteristics
- Place them in varied, interesting scenarios and environments
- Include different activities, poses, lighting conditions, and contexts
- Provide enough specific detail to guide the image generation
- Keep descriptions concise (25-50 words each)

Each prompt should be on a new line and prefixed with 'PROMPT:'. Focus on scenarios that would make for visually compelling images and showcase the person in different contexts.

Here are examples of the style and quality of prompts I'm looking for:

PROMPT: "The sexy woman sensually dancing barefoot on a moonlit beach, her sheer, silken dress clinging to her curves as it flows gently in the ocean breeze, a sultry gaze hinting at hidden desires."
PROMPT: "The sexy woman gracefully arranging fresh flowers into a vibrant bouquet at a charming farmer's market stall, the sunlight caressing her bare shoulders and accentuating her alluring smile and captivating features."
PROMPT: "The sexy woman standing poised and powerful at the bow of an old wooden sailing ship, her form-fitting captain's attire accentuating her figure, an intense gaze fixed on the horizon as waves splash softly around her, hinting at a thrilling adventure."
PROMPT: "The sexy woman in her luxurious, form-fitting evening gown seated at an antique piano, her eyes half-closed in passionate intensity as her fingers dance across the keys, lost deeply in a romantic classical piece, illuminated seductively by the flickering vintage candlelight."
PROMPT: "The sexy woman delicately releasing colorful paper lanterns into a twilight sky during a vibrant cultural festival, her arms gracefully raised upward, her sheer, flowing dress subtly outlining her curves as the ethereal light plays across her features."
Format your response as {num_prompts} lines, each starting with 'PROMPT:' followed by the prompt text.""".format(
        num_prompts=num_prompts)

    # Retry logic for rate limiting (15 requests per minute)
    max_retries = 5
    base_delay = 4  # Base delay in seconds (60/15 = 4 seconds between requests)

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                # Exponential backoff with jitter for rate limiting
                delay = base_delay * (2 ** attempt) + random.uniform(0, 2)
                print(f"⏳ Rate limit retry {attempt}/{max_retries-1}, waiting {delay:.1f} seconds...")
                time.sleep(delay)

            print(f"🤖 Calling Google GenAI with model: {model_name} (attempt {attempt + 1})")

            # Convert image to PIL Image for Google GenAI
            from PIL import Image as PILImage
            with open(image_path, "rb") as image_file:
                pil_image = PILImage.open(image_file)
                if pil_image.mode == 'RGBA':
                    pil_image = pil_image.convert('RGB')

            if attempt == 0:  # Only print this on first attempt
                print(f"📸 Loaded image: {pil_image.size} pixels, mode: {pil_image.mode}")

            # Prepare contents for Google GenAI
            contents = [pil_image, f"Here's a description of the person: {person_description}"]

            # Make the API call
            print("🔄 Making API call to Google GenAI...")
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=1000
                )
            )

            if response and response.text:
                generated_text = response.text.strip()
                print(f"✅ Received response from Google GenAI ({len(generated_text)} characters)")
                break  # Success, exit retry loop
            else:
                generated_text = None
                print("❌ Warning: Google GenAI API response is not in the expected format.")
                print("Response:", response)
                break  # Don't retry for empty responses

        except Exception as e:
            error_str = str(e).lower()

            # Check if it's a rate limit error
            if any(keyword in error_str for keyword in ['rate limit', 'quota', 'too many requests', '429']):
                print(f"🚫 Rate limit hit on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    print("❌ Max retries reached for rate limiting")
                    generated_text = None
                    break
                # Continue to next retry attempt
                continue
            else:
                # Non-rate-limit error, don't retry
                print(f"❌ Error calling Google GenAI API: {e}")
                import traceback
                traceback.print_exc()
                generated_text = None
                break
    else:
        # This runs if the for loop completes without breaking (all retries exhausted)
        print("❌ All retry attempts exhausted")
        generated_text = None

    print(generated_text)

    if not generated_text:
        print("Warning: No text generated from the API.")
        return []

    prompts = []
    for line in generated_text.split("\n"):
        line = line.strip()
        if line.startswith("PROMPT:"):
            prompt_text = line[len("PROMPT:"):].strip()
            prompts.append(prompt_text)

    return prompts[:num_prompts]


async def download_image(url: str, save_path: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(save_path, 'wb') as f:
                    f.write(await response.read())


async def generate_pulidflux_images(prompts: List[str], image_path: str, output_dir: str):
    try:
        print(f"📁 Preparing image data from: {image_path}")
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            data_uri = f"data:image/jpeg;base64,{encoded_image}"

        output_image_paths = []  # List to store output image paths

        for i, prompt in enumerate(prompts):
            print(f"🎯 Generating image {i+1}/{len(prompts)} with FAL PuLID Flux...")

            # Add small delay between FAL API calls to avoid rate limiting
            if i > 0:
                await asyncio.sleep(2)  # 2 second delay between requests

            # Retry logic for FAL API calls
            max_fal_retries = 3
            fal_success = False

            for fal_attempt in range(max_fal_retries):
                try:
                    if fal_attempt > 0:
                        delay = 5 * (2 ** fal_attempt)  # Exponential backoff: 5, 10, 20 seconds
                        print(f"⏳ FAL API retry {fal_attempt}/{max_fal_retries-1}, waiting {delay} seconds...")
                        await asyncio.sleep(delay)

                    handler = await fal_client.submit_async(
                        "fal-ai/flux-pulid",
                        arguments={
                            "prompt": prompt,
                            "reference_image_url": data_uri,
                            "image_size": {
                                "width": 1024,
                                "height": 1024
                            },
                            "num_inference_steps": 20,
                            "guidance_scale": 4,
                            "negative_prompt": "bad quality, worst quality, text, signature, watermark, extra limbs",
                            "true_cfg": 1,
                            "id_weight": 1,
                            "enable_safety_checker": False,
                            "max_sequence_length": "256"
                        },
                    )
                    print(f"⏳ Waiting for FAL API response for image {i+1}...")
                    result = await handler.get()
                    print(f"✅ Received result for image {i+1}")

                    if 'images' in result and len(result['images']) > 0:
                        image_url = result['images'][0]['url']
                        output_path = os.path.join(output_dir, f"pulid_{i}.jpg")
                        print(f"⬇️ Downloading image {i+1} to: {output_path}")
                        await download_image(image_url, output_path)
                        output_image_paths.append(output_path)
                        print(f"✅ Successfully saved image {i+1}")
                        fal_success = True
                        break  # Success, exit retry loop
                    else:
                        print(f"❌ No images in result for prompt {i+1}: {result}")
                        break  # Don't retry for empty results

                except Exception as e:
                    error_str = str(e).lower()
                    print(f"❌ Error generating image {i+1} (attempt {fal_attempt + 1}): {e}")

                    # Check if it's a rate limit or server error that might benefit from retry
                    if any(keyword in error_str for keyword in ['rate limit', 'quota', 'too many requests', '429', '500', '502', '503', '504']):
                        if fal_attempt == max_fal_retries - 1:
                            print(f"❌ Max FAL retries reached for image {i+1}")
                            break
                        # Continue to next retry attempt
                        continue
                    else:
                        # Non-retryable error
                        break

            if not fal_success:
                print(f"❌ Failed to generate image {i+1} after all retries")

        return output_image_paths

    except Exception as e:
        print(f"❌ Error in generate_pulidflux_images: {e}")
        import traceback
        traceback.print_exc()
        return []


def generate_synthetic_images(
        image_path: str,
        description: str,
        num_images: int,
        output_dir: str,
        model: Optional[str] = None,
        base_url: Optional[str] = None
):
    """
    Generate prompts and create images based on the given parameters.

    Args:
        image_path: Path to the image of the person
        description: Description of the person including appearance, style, and personality
        num_images: Number of images to generate
        output_dir: Directory to save the generated images
        model: Custom model name to use (defaults to "gemini-2.5-flash")
        base_url: Not used for Google GenAI (kept for compatibility)
    """
    print(f"🎨 Starting PuLID image generation:")
    print(f"   - Image path: {image_path}")
    print(f"   - Description: {description[:100]}...")
    print(f"   - Number of images: {num_images}")
    print(f"   - Output directory: {output_dir}")

    try:
        # Check if FAL_KEY is available
        fal_key = os.getenv("FAL_KEY")
        if not fal_key:
            print("❌ Error: FAL_KEY environment variable is required for PuLID image generation")
            return []

        print("✅ FAL_KEY found")

        # Generate prompts
        print("🔤 Generating prompts with Google GenAI...")
        prompts = generate_pulidflux_prompts(
            image_path=image_path,
            person_description=description,
            num_prompts=num_images,
            model=model,
            base_url=base_url
        )

        if not prompts:
            print("❌ Error: No prompts were generated")
            return []

        print(f"✅ Generated {len(prompts)} prompts")
        for i, prompt in enumerate(prompts):
            print(f"   Prompt {i+1}: {prompt[:80]}...")

        # Generate images
        print("🖼️ Generating images with FAL PuLID Flux...")
        output_image_paths = asyncio.run(generate_pulidflux_images(prompts, image_path, output_dir))

        if output_image_paths:
            print(f"✅ Successfully generated {len(output_image_paths)} PuLID images")
            for path in output_image_paths:
                print(f"   - {path}")
        else:
            print("❌ No images were generated")

        return output_image_paths

    except Exception as e:
        print(f"❌ Error in PuLID image generation: {e}")
        import traceback
        traceback.print_exc()
        return []
