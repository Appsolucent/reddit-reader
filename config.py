"""
Reddit Stories Pipeline Configuration
All API keys and settings in one place
"""

import os
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use environment variables or defaults

# =============================================================================
# API KEYS - Set these as environment variables or replace directly
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your-anthropic-key")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "your-elevenlabs-key")
YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")

# Reddit API (create app at https://www.reddit.com/prefs/apps)
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "your-reddit-client-id")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "your-reddit-secret")
REDDIT_USER_AGENT = "RedditStoriesBot/1.0 (by /u/YourUsername)"

# =============================================================================
# ELEVENLABS VOICE SETTINGS
# =============================================================================

# Narrator voice - calm, storytelling tone
NARRATOR_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam - good for narration
# Commentator voice - energetic, reaction voice
COMMENTATOR_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Bella - good for reactions

# Alternative popular voices:
# "21m00Tcm4TlvDq8ikWAM" - Rachel (calm female)
# "AZnzlk1XvdvUeBnXmlld" - Domi (energetic)
# "ErXwobaYiN019PkySvjV" - Antoni (warm male)
# "MF3mGyEYCl7XYWbV9V6O" - Elli (young female)

ELEVENLABS_MODEL = "eleven_turbo_v2_5"

VOICE_SETTINGS = {
    "narrator": {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.3,
        "use_speaker_boost": True
    },
    "commentator": {
        "stability": 0.4,  # More expressive
        "similarity_boost": 0.8,
        "style": 0.6,  # More stylized
        "use_speaker_boost": True
    }
}

# =============================================================================
# REDDIT SETTINGS
# =============================================================================

TARGET_SUBREDDITS = [
    "tifu",
    "AmItheAsshole",
    "MaliciousCompliance",
    "ProRevenge",
    "pettyrevenge",
    "entitledparents",
    "JUSTNOMIL",
    "relationship_advice",
    "confessions",
    "TrueOffMyChest"
]

# Story selection criteria
MIN_STORY_LENGTH = 500  # characters
MAX_STORY_LENGTH = 8000  # characters (keeps video under 10 min)
MIN_UPVOTES = 500
MIN_COMMENTS = 50
STORY_AGE_DAYS = 7  # Only get stories from last N days

# =============================================================================
# VIDEO SETTINGS
# =============================================================================

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # 9:16 vertical for Shorts/TikTok compatibility
VIDEO_FPS = 30

# Text overlay settings
FONT_PATH = "C:/Windows/Fonts/arial.ttf"  # Windows default
FONT_SIZE_TITLE = 48
FONT_SIZE_STORY = 36
FONT_SIZE_COMMENTARY = 32
TEXT_COLOR = "white"
TEXT_STROKE_COLOR = "black"
TEXT_STROKE_WIDTH = 2

# Background gameplay footage folder
BACKGROUND_VIDEOS_DIR = Path("./assets/background_footage")
# Put Minecraft parkour, Subway Surfers, etc. videos here

# =============================================================================
# OUTPUT SETTINGS
# =============================================================================

OUTPUT_DIR = Path("./output")
TEMP_DIR = Path("./temp")
ARCHIVE_DIR = Path("./archive")  # Store used stories to avoid repeats

# =============================================================================
# YOUTUBE SETTINGS
# =============================================================================

YOUTUBE_CATEGORY_ID = "24"  # Entertainment
DEFAULT_TAGS = [
    "reddit", "reddit stories", "reddit reading", 
    "AITA", "TIFU", "malicious compliance",
    "reddit commentary", "story time", "reddit drama"
]

# Upload schedule (for reference - actual scheduling done by task scheduler)
UPLOAD_FREQUENCY = "daily"  # or "weekly"

# =============================================================================
# CONTENT GENERATION SETTINGS
# =============================================================================

# How often to insert commentary (every N paragraphs)
COMMENTARY_FREQUENCY = 2

# Commentary style options
COMMENTARY_STYLES = [
    "sarcastic",
    "sympathetic", 
    "shocked",
    "judgmental",
    "supportive"
]

# Claude model for script generation
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# =============================================================================
# REPLICATE SETTINGS (AI Character Generation)
# =============================================================================

REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY", "your-replicate-key")

# Models
FLUX_MODEL = "black-forest-labs/flux-schnell"  # Fast image generation
HALLO2_MODEL = "fudan-generative-ai/hallo2"    # Best talking head quality

# Alternative models (uncomment to switch):
# FLUX_MODEL = "black-forest-labs/flux-dev"    # Higher quality, slower
# HALLO2_MODEL = "fudan-generative-ai/hallo"   # Original, faster
# HALLO2_MODEL = "cjwbw/sadtalker"             # Good for stylized characters

# Hallo2 generation settings
HALLO2_POSE_WEIGHT = 1.0      # How much head movement
HALLO2_FACE_WEIGHT = 1.0      # Facial expression intensity
HALLO2_LIP_WEIGHT = 1.0       # Lip sync accuracy
HALLO2_FACE_EXPAND_RATIO = 1.2  # Face crop ratio

# =============================================================================
# CHARACTER SETTINGS
# =============================================================================

CHARACTERS_DIR = Path("./assets/characters")
CHARACTER_IMAGE_PATH = CHARACTERS_DIR / "character_default.png"

# Enable/disable character video generation
ENABLE_CHARACTER_VIDEO = True

# =============================================================================
# YOUTUBE & ATTRIBUTION SETTINGS
# =============================================================================

# Your YouTube channel name (for video descriptions)
CHANNEL_NAME = "Reddit Stories"

# Show intro attribution overlay at start of video
SHOW_INTRO_ATTRIBUTION = True

# Show persistent Reddit URL at bottom of video
SHOW_URL_ATTRIBUTION = True

# Where to position the character in the video
# Options: "bottom_right", "bottom_left", "top_right", "top_left", "center_bottom"
CHARACTER_POSITION = "bottom_right"

# Character size as fraction of video width (0.2 = 20% of width)
CHARACTER_SIZE = 0.35

# =============================================================================
# LOCAL COMFYUI SETTINGS (Alternative to Replicate)
# =============================================================================

# Set to True to use local ComfyUI instead of Replicate for image generation
USE_LOCAL_COMFYUI = False

# ComfyUI server URL (default when running locally)
COMFYUI_URL = "http://127.0.0.1:8188"

# Required models for local Flux (place in ComfyUI/models/):
# - unet/flux1-schnell-fp8.safetensors
# - clip/t5xxl_fp8_e4m3fn.safetensors  
# - vae/ae.safetensors

# =============================================================================
# LOCAL ANIMATEDIFF SETTINGS (For animated reactions)
# =============================================================================

# Use local AnimateDiff for character reactions instead of static lip sync
USE_LOCAL_ANIMATEDIFF = False

# AnimateDiff motion model (place in ComfyUI/models/animatediff_models/)
ANIMATEDIFF_MOTION_MODEL = "mm_sd_v15_v2.ckpt"

# Base checkpoint for AnimateDiff (SD 1.5 based)
ANIMATEDIFF_CHECKPOINT = "v1-5-pruned-emaonly.safetensors"

# Animation settings
REACTION_FRAMES = 16  # Number of frames per reaction (~0.5s at 30fps)
REACTION_FPS = 30

# Default character prompt (used if no character image exists)
CHARACTER_PROMPT = """Portrait of a young animated content creator character, 
expressive face, friendly appearance, vibrant colors, 
digital art style, facing camera, neutral background, 
high quality, detailed features, suitable for YouTube commentary"""

# Pre-defined character styles
CHARACTER_STYLES = {
    "default": CHARACTER_PROMPT,
    
    "anime": """Anime style portrait of a young commentator character,
expressive eyes, colorful hair, friendly smile, 
facing camera, clean background, high quality anime art,
suitable for YouTube reaction videos""",
    
    "realistic": """Photorealistic portrait of a young content creator,
friendly expression, professional lighting, 
facing camera, neutral studio background,
high quality photography style""",
    
    "cartoon": """Cartoon style portrait of an expressive character,
big eyes, exaggerated features, vibrant colors,
friendly appearance, facing camera, simple background,
pixar-style 3D animation look""",
    
    "meme": """Portrait of a smug anime girl character,
knowing smirk, raised eyebrow, expressive face,
internet meme aesthetic, facing camera,
high quality digital art""",
    
    "gamer": """Portrait of an energetic gamer character,
wearing headphones, excited expression, 
RGB lighting effects, gaming setup background,
digital art style, facing camera"""
}
