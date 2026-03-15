"""Image generation tools for PowerSymphony agents.

Supports multiple providers in priority order:
1. Adobe Firefly (user-configured integration)
2. Google Gemini (user-configured or env var)
3. OpenAI DALL-E (user-configured or env var)
4. Stability AI (user-configured)
5. Fallback: returns a ready-to-use prompt
"""

import base64
import json
import os
from pathlib import Path

import requests


# ---------------------------------------------------------------------------
# Provider helpers
# ---------------------------------------------------------------------------

def _try_adobe_firefly(prompt: str, output_path: Path, aspect_ratio: str, api_key: str) -> str | None:
    """Generate image via Adobe Firefly API."""
    try:
        size_map = {
            "1:1": {"width": 1024, "height": 1024},
            "16:9": {"width": 1792, "height": 1024},
            "9:16": {"width": 1024, "height": 1792},
            "4:5": {"width": 1024, "height": 1280},
        }
        size = size_map.get(aspect_ratio, size_map["1:1"])

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }

        payload = {
            "prompt": prompt,
            "n": 1,
            "size": size,
            "contentClass": "art",
        }

        resp = requests.post(
            "https://firefly-api.adobe.io/v3/images/generate",
            headers=headers,
            json=payload,
            timeout=60,
        )

        if resp.status_code == 200:
            data = resp.json()
            images = data.get("outputs", [])
            if images:
                img = images[0]
                # Firefly returns base64 or a URL
                if img.get("base64"):
                    output_path.write_bytes(base64.b64decode(img["base64"]))
                    return f"Image generated with Adobe Firefly and saved to: {output_path}"
                elif img.get("image", {}).get("url"):
                    img_resp = requests.get(img["image"]["url"], timeout=30)
                    output_path.write_bytes(img_resp.content)
                    return f"Image generated with Adobe Firefly and saved to: {output_path}"

        return None  # Fall through to next provider
    except Exception:
        return None


def _try_gemini(prompt: str, output_path: Path, api_key: str) -> str | None:
    """Generate image via Google Gemini."""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                image_data = part.inline_data.data
                if isinstance(image_data, str):
                    image_data = base64.b64decode(image_data)
                output_path.write_bytes(image_data)
                return f"Image generated with Google Gemini and saved to: {output_path}"

        return None
    except Exception:
        return None


def _try_openai_dalle(prompt: str, output_path: Path, aspect_ratio: str, api_key: str, base_url: str = None) -> str | None:
    """Generate image via OpenAI DALL-E."""
    try:
        import openai

        client = openai.OpenAI(api_key=api_key, base_url=base_url or "https://api.openai.com/v1")
        size_map = {
            "1:1": "1024x1024",
            "16:9": "1792x1024",
            "9:16": "1024x1792",
            "4:5": "1024x1024",
        }
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size_map.get(aspect_ratio, "1024x1024"),
            quality="standard",
            n=1,
            response_format="b64_json",
        )
        image_data = base64.b64decode(response.data[0].b64_json)
        output_path.write_bytes(image_data)
        return f"Image generated with DALL-E and saved to: {output_path}"
    except Exception:
        return None


def _try_stability_ai(prompt: str, output_path: Path, aspect_ratio: str, api_key: str) -> str | None:
    """Generate image via Stability AI."""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "text_prompts": [{"text": prompt, "weight": 1}],
            "cfg_scale": 7,
            "samples": 1,
            "steps": 30,
        }

        resp = requests.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
            headers=headers,
            json=payload,
            timeout=60,
        )

        if resp.status_code == 200:
            data = resp.json()
            artifacts = data.get("artifacts", [])
            if artifacts:
                output_path.write_bytes(base64.b64decode(artifacts[0]["base64"]))
                return f"Image generated with Stability AI and saved to: {output_path}"
        return None
    except Exception:
        return None


def _get_integration_key(provider: str) -> str | None:
    """Try to get an API key from the integrations database."""
    try:
        from server.services.db import get_cursor
        with get_cursor() as cur:
            cur.execute(
                "SELECT api_key FROM integrations WHERE provider = %s AND enabled = TRUE LIMIT 1",
                (provider,),
            )
            row = cur.fetchone()
            return row["api_key"] if row else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_image(
    prompt: str,
    output_filename: str = "generated_image.png",
    style: str = "default",
    aspect_ratio: str = "1:1",
    _context: dict = None,
) -> str:
    """Generate an image from a text prompt.

    Tries providers in order: Adobe Firefly, Gemini, DALL-E, Stability AI.
    Falls back to returning a ready-to-use prompt if no provider is available.

    Args:
        prompt: Detailed description of the image to generate.
        output_filename: Name for the output file.
        style: Style hint — 'photorealistic', 'illustration', 'minimalist',
               'bold-graphic', 'watercolor', or 'default'.
        aspect_ratio: Aspect ratio — '1:1', '16:9', '9:16', '4:5'.
        _context: Internal context dict (injected by tool manager).

    Returns:
        Path to the generated image file, or a detailed prompt if no provider available.
    """
    workspace = Path(_context.get("python_workspace_root", ".")) if _context else Path(".")
    output_dir = workspace / "generated_images"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_filename

    style_modifiers = {
        "photorealistic": "photorealistic, high detail, professional photography, sharp focus",
        "illustration": "digital illustration, vibrant colors, clean lines, artistic",
        "minimalist": "minimalist design, clean, simple, modern, white space",
        "bold-graphic": "bold graphic design, strong colors, high contrast, eye-catching",
        "watercolor": "watercolor painting style, soft edges, artistic, flowing colors",
        "default": "",
    }
    style_suffix = style_modifiers.get(style, "")
    full_prompt = f"{prompt}. {style_suffix}".strip(". ")

    # 1. Adobe Firefly (integration DB or env var)
    firefly_key = _get_integration_key("adobe_firefly") or os.getenv("ADOBE_FIREFLY_API_KEY")
    if firefly_key:
        result = _try_adobe_firefly(full_prompt, output_path, aspect_ratio, firefly_key)
        if result:
            return result

    # 2. Google Gemini
    gemini_key = _get_integration_key("google_gemini") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if gemini_key:
        result = _try_gemini(full_prompt, output_path, gemini_key)
        if result:
            return result

    # 3. OpenAI DALL-E
    dalle_key = _get_integration_key("openai_dalle") or os.getenv("OPENAI_API_KEY")
    if dalle_key:
        result = _try_openai_dalle(full_prompt, output_path, aspect_ratio, dalle_key)
        if result:
            return result

    # 4. Stability AI
    stability_key = _get_integration_key("stability_ai") or os.getenv("STABILITY_API_KEY")
    if stability_key:
        result = _try_stability_ai(full_prompt, output_path, aspect_ratio, stability_key)
        if result:
            return result

    # 5. No provider available — return the prompt for manual use
    return (
        f"No image generation provider connected. Go to Settings > Integrations to connect "
        f"Adobe Firefly, DALL-E, Gemini, or Stability AI.\n\n"
        f"Ready-to-use image prompt:\n\n"
        f"**Prompt:** {full_prompt}\n"
        f"**Aspect Ratio:** {aspect_ratio}\n"
        f"**Style:** {style}\n\n"
        f"Paste this into any image generator (Firefly, Midjourney, DALL-E, etc.)"
    )


def generate_social_media_image(
    platform: str,
    content_type: str,
    description: str,
    brand_colors: str = "",
    text_overlay: str = "",
    _context: dict = None,
) -> str:
    """Generate a social media image optimized for a specific platform.

    Args:
        platform: Target platform — 'instagram', 'tiktok', 'twitter', 'linkedin', 'youtube'.
        content_type: Type — 'post', 'story', 'cover', 'profile', 'thumbnail'.
        description: What the image should show.
        brand_colors: Optional brand colors (e.g., '#FF5733, #2E86C1').
        text_overlay: Optional text to include in the image.
        _context: Internal context dict.

    Returns:
        Path to generated image or a detailed prompt.
    """
    platform_specs = {
        "instagram": {"post": "1:1", "story": "9:16", "cover": "16:9"},
        "tiktok": {"post": "9:16", "story": "9:16", "cover": "16:9", "thumbnail": "9:16"},
        "twitter": {"post": "16:9", "story": "9:16", "cover": "16:9"},
        "linkedin": {"post": "1:1", "story": "9:16", "cover": "16:9"},
        "youtube": {"thumbnail": "16:9", "cover": "16:9", "post": "16:9"},
    }

    aspect_ratio = platform_specs.get(platform, {}).get(content_type, "1:1")

    prompt_parts = [
        f"Professional social media {content_type} for {platform}.",
        description,
    ]
    if brand_colors:
        prompt_parts.append(f"Use brand colors: {brand_colors}.")
    if text_overlay:
        prompt_parts.append(f'Include text overlay: "{text_overlay}".')
    prompt_parts.append("Clean, modern, scroll-stopping design. High quality.")

    full_prompt = " ".join(prompt_parts)
    filename = f"{platform}_{content_type}.png"

    return generate_image(
        prompt=full_prompt,
        output_filename=filename,
        style="bold-graphic",
        aspect_ratio=aspect_ratio,
        _context=_context,
    )
