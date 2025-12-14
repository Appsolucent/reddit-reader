# Reddit Stories Pipeline 🎬

Automated YouTube content pipeline that transforms Reddit stories into engaging narrated videos with AI commentary and animated AI character reactions.

## Features

- 📖 **Reddit Scraping**: Automatically fetches top stories from popular subreddits (TIFU, AITA, MaliciousCompliance, etc.)
- 🤖 **AI Script Generation**: Claude API creates narration with funny commentary injected between sections
- 🎙️ **Multi-Voice Narration**: ElevenLabs generates two distinct voices (narrator + commentator)
- 🎭 **AI Character Animation**: Replicate's Hallo2 generates lip-synced talking character for commentary
- 🎮 **Gaming Background**: Overlays story on Minecraft parkour or Subway Surfers gameplay
- 📝 **Text Overlays**: Dynamic captions synced to narration
- 📺 **YouTube Upload**: Automated upload with metadata, tags, and thumbnails
- 🔗 **Reddit Attribution**: Full attribution with links back to original Reddit posts

## Reddit Attribution (Important!)

This pipeline is designed to properly attribute and link back to Reddit, promoting the platform and original authors:

### In Every Video:
- **On-Screen Attribution**: Reddit URL displayed at bottom of video
- **Intro Overlay**: Shows r/subreddit, original author, and "Link in description" at start
- **Subreddit Badge**: Persistent r/subreddit badge in top corner

### In YouTube Description:
- **Direct Link**: Full URL to original Reddit post
- **Author Credit**: Original poster's username
- **Subreddit Link**: Link to the subreddit for viewers to discover more
- **Call-to-Action**: Encourages viewers to upvote the original post

### Generated Metadata Files:
Every video generates a `metadata_[story_id].json` file containing:
- YouTube-optimized title with subreddit
- Full description with attribution
- Relevant tags
- Original Reddit URL

This helps you comply with Reddit's API terms by driving traffic back to the platform.

## Pipeline Flow

```
Reddit Story → Claude Script → ElevenLabs Audio → Hallo2 Character → MoviePy Video → YouTube
     ↓              ↓                ↓                  ↓                  ↓
  Top posts    Narrator +       2 voices         Lip-synced        Background +
  filtered     Commentary       generated        AI character      composited
```

## Quick Start

### 1. Install Dependencies

```powershell
# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt
```

### 2. Install System Requirements

**FFmpeg** (required for video processing):
```powershell
# Using winget
winget install FFmpeg

# Or using chocolatey
choco install ffmpeg
```

**ImageMagick** (required for text overlays):
```powershell
# Using winget
winget install ImageMagick.ImageMagick

# Or download from: https://imagemagick.org/script/download.php
# IMPORTANT: During installation, check "Install legacy utilities (e.g. convert)"
```

### 3. Configure API Keys

Edit `config.py` or set environment variables:

```powershell
# Set environment variables (PowerShell)
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:ELEVENLABS_API_KEY = "..."
$env:REPLICATE_API_KEY = "r8_..."
$env:REDDIT_CLIENT_ID = "..."
$env:REDDIT_CLIENT_SECRET = "..."
```

#### Replicate API Setup (for AI Character)
1. Go to https://replicate.com
2. Sign up/login
3. Go to Account → API Tokens
4. Create and copy your token
5. Pay-as-you-go pricing (~$0.02-0.05 per character clip)

#### Reddit API Setup
1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Select "script" type
4. Name it anything (e.g., "RedditStoriesBot")
5. Set redirect URI to `http://localhost:8080`
6. Copy the client ID (under app name) and secret

#### YouTube API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable "YouTube Data API v3"
4. Create OAuth 2.0 credentials (Desktop application)
5. Download and save as `client_secrets.json`

### 4. Add Background Videos

Place gameplay footage in `./assets/background_footage/`:

```
assets/
└── background_footage/
    ├── minecraft_parkour_1.mp4
    ├── minecraft_parkour_2.mp4
    ├── subway_surfers_1.mp4
    └── ...
```

**Getting background videos:**
```powershell
# Install yt-dlp
pip install yt-dlp

# Download Minecraft parkour (example)
yt-dlp -f "best[height<=1080]" -o "assets/background_footage/%(title)s.%(ext)s" "YOUTUBE_URL"
```

Search YouTube for:
- "Minecraft parkour no commentary 1 hour"
- "Subway Surfers gameplay no commentary"
- "Satisfying gameplay background"

## Usage

### Preview Available Stories
```powershell
python pipeline.py --preview
```

### Run Full Pipeline (Video Only)
```powershell
python pipeline.py
```

### Run Pipeline with YouTube Upload
```powershell
python pipeline.py --upload --privacy private
```

### Batch Process Multiple Stories
```powershell
python pipeline.py --batch 5 --upload
```

### Disable AI Character (text-only mode)
```powershell
python pipeline.py --no-character
```

### Create Custom Character
```powershell
# Use preset style
python pipeline.py --create-character --character-style anime

# Use custom prompt
python pipeline.py --create-character --custom-character-prompt "Portrait of a cyberpunk streamer..."

# Available styles: default, anime, realistic, cartoon, meme, gamer
```

### Dry Run (Test Without Processing)
```powershell
python pipeline.py --dry-run
```

## AI Character System

The pipeline uses Replicate's Hallo2 model to generate lip-synced talking head videos.

### How It Works

1. **Character Image**: Generated once using Flux (or provide your own)
2. **Commentary Audio**: ElevenLabs generates the commentator voice
3. **Lip Sync**: Hallo2 animates the character to match the audio
4. **Compositing**: Character appears in corner during commentary segments

### Character Styles

| Style | Description |
|-------|-------------|
| `default` | Friendly animated content creator |
| `anime` | Anime-style with colorful hair |
| `realistic` | Photorealistic portrait |
| `cartoon` | Pixar-style 3D look |
| `meme` | Smug anime girl aesthetic |
| `gamer` | Energetic with RGB vibes |

### Using Your Own Character

Place a PNG image at `./assets/characters/character_default.png`:
- Square aspect ratio (1:1) works best
- Clear face, front-facing
- Neutral expression
- High resolution (512x512 or higher)

### Character Position

Edit `config.py` to change where the character appears:

```python
CHARACTER_POSITION = "bottom_right"  # Options: bottom_right, bottom_left, top_right, top_left, center_bottom
CHARACTER_SIZE = 0.35  # Fraction of video width
```

## Output

Videos are saved to `./output/`:
```
output/
├── reddit_story_abc123_20240115_143022.mp4
├── thumb_abc123.jpg
└── upload_log.json
```

## Configuration

### Customize Voices

Edit `config.py` to change ElevenLabs voices:

```python
# Browse voices at: https://elevenlabs.io/voice-library
NARRATOR_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam
COMMENTATOR_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Bella
```

### Customize Subreddits

```python
TARGET_SUBREDDITS = [
    "tifu",
    "AmItheAsshole",
    "MaliciousCompliance",
    # Add more...
]
```

### Customize Story Selection

```python
MIN_STORY_LENGTH = 500  # characters
MAX_STORY_LENGTH = 8000  # characters
MIN_UPVOTES = 500
MIN_COMMENTS = 50
```

### Video Dimensions

Default is 9:16 (1080x1920) for YouTube Shorts/TikTok:

```python
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# For 16:9 landscape:
# VIDEO_WIDTH = 1920
# VIDEO_HEIGHT = 1080
```

## Automation

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., Daily at 2 PM)
4. Action: Start a program
5. Program: `python`
6. Arguments: `C:\path\to\pipeline.py --upload --privacy private`
7. Start in: `C:\path\to\reddit_stories_pipeline`

### PowerShell Script for Scheduled Runs

Create `run_pipeline.ps1`:

```powershell
# Activate virtual environment
Set-Location "C:\path\to\reddit_stories_pipeline"
.\venv\Scripts\Activate.ps1

# Run pipeline
python pipeline.py --upload --privacy unlisted

# Log result
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path "pipeline_log.txt" -Value "$timestamp - Pipeline executed"
```

## Estimated Costs

Per video (approximate):
- **Claude API**: ~$0.05-0.15 (depending on story length)
- **ElevenLabs**: ~$0.15-0.50 (depends on plan and audio length)
- **Replicate (Hallo2)**: ~$0.10-0.30 (depends on number of commentary segments)
- **YouTube API**: Free (within daily quotas)

Monthly budget for daily uploads: **$15-25** (with character) or **$12-15** (without)

## Troubleshooting

### "No background videos found"
- Add .mp4 files to `./assets/background_footage/`
- Pipeline will use solid color background as fallback

### MoviePy ImageMagick errors
- Ensure ImageMagick is installed with legacy utilities
- Add to PATH or set in MoviePy config:
  ```python
  from moviepy.config import change_settings
  change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.0-Q16-HDRI\magick.exe"})
  ```

### Replicate errors
- Check API key is valid
- Check account has credits
- Some models may be cold-started (first run slower)

### YouTube upload quota exceeded
- Default quota: 10,000 units/day
- Video upload costs: ~1,600 units
- Max ~6 uploads per day with default quota
- Request quota increase in Google Cloud Console

### Reddit API rate limits
- PRAW handles rate limiting automatically
- If issues persist, increase delay between requests

## Project Structure

```
reddit_stories_pipeline/
├── config.py              # All configuration
├── reddit_scraper.py      # Reddit API integration
├── script_generator.py    # Claude script generation
├── audio_generator.py     # ElevenLabs TTS
├── character_generator.py # Replicate Hallo2 integration
├── video_assembler.py     # MoviePy video creation
├── youtube_uploader.py    # YouTube API upload
├── pipeline.py            # Main orchestrator
├── requirements.txt       # Python dependencies
├── client_secrets.json    # YouTube OAuth (you create)
├── token.pickle           # YouTube auth token (auto-generated)
├── assets/
│   ├── background_footage/  # Your gameplay videos
│   └── characters/          # AI character images
├── output/                # Generated videos
├── temp/                  # Processing temp files
└── archive/               # Used story tracking
```

## License

MIT License - Use freely for personal projects.

**Note**: Respect Reddit's content policies and give attribution to original posters. Consider linking to the original Reddit post in your video descriptions.
