# AnimateDiff Setup Guide for Reddit Stories Pipeline

This guide will help you set up local AnimateDiff for generating animated character reactions.

## Prerequisites

- ComfyUI already installed and running
- ~6-8GB VRAM (RTX 4060 works)
- Python 3.10+

## Step 1: Install Required Custom Nodes

Open terminal/PowerShell and navigate to your ComfyUI custom_nodes folder:

```powershell
cd C:\path\to\ComfyUI\custom_nodes
```

### Install AnimateDiff Evolved

```powershell
git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved
cd ComfyUI-AnimateDiff-Evolved
pip install -r requirements.txt
cd ..
```

### Install Video Helper Suite (for video output)

```powershell
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
```

### Install IP-Adapter (for character consistency) - Optional but Recommended

```powershell
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus
```

## Step 2: Download Motion Models

Download AnimateDiff motion models and place in `ComfyUI/models/animatediff_models/`:

### Option A: SD 1.5 Based (Recommended for 8GB VRAM)

Download from: https://huggingface.co/guoyww/animatediff/tree/main

Required files:
- `mm_sd_v15_v2.ckpt` (~1.8GB) - Best general motion

Place in:
```
ComfyUI/
└── models/
    └── animatediff_models/
        └── mm_sd_v15_v2.ckpt
```

### Option B: Additional Motion Models (Optional)

- `mm_sd_v15.ckpt` - Original v1
- `mm_sd_v14.ckpt` - Older version
- `v3_sd15_mm.ckpt` - AnimateDiff v3

## Step 3: Download Base Checkpoint

AnimateDiff works with SD 1.5 checkpoints. Download one:

**Stable Diffusion 1.5:**
- https://huggingface.co/runwayml/stable-diffusion-v1-5

Place in `ComfyUI/models/checkpoints/`:
```
ComfyUI/
└── models/
    └── checkpoints/
        └── v1-5-pruned-emaonly.safetensors
```

## Step 4: Download IP-Adapter Models (Optional)

For better character consistency, download IP-Adapter models:

From: https://huggingface.co/h94/IP-Adapter/tree/main

- `ip-adapter_sd15.safetensors` → `ComfyUI/models/ipadapter/`
- `ip-adapter-plus_sd15.safetensors` → `ComfyUI/models/ipadapter/`

CLIP Vision model:
- `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` → `ComfyUI/models/clip_vision/`

## Step 5: Restart ComfyUI

```powershell
cd C:\path\to\ComfyUI
python main.py --lowvram
```

## Step 6: Verify Installation

Run the check command:

```powershell
cd reddit_stories_pipeline
python local_animatediff.py --check
```

Expected output:
```
Checking AnimateDiff setup...
--------------------------------------------------
✓ ComfyUI is running
✓ AnimateDiff nodes found

Motion models available: 1
  - mm_sd_v15_v2.ckpt
```

## Step 7: Test a Reaction

```powershell
python local_animatediff.py --reaction shocked --character assets/characters/character_custom.png
```

## Folder Structure Summary

```
ComfyUI/
├── models/
│   ├── animatediff_models/
│   │   └── mm_sd_v15_v2.ckpt          # Motion model
│   ├── checkpoints/
│   │   └── v1-5-pruned-emaonly.safetensors  # Base SD 1.5
│   ├── ipadapter/                      # Optional
│   │   └── ip-adapter_sd15.safetensors
│   └── clip_vision/                    # Optional
│       └── CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors
└── custom_nodes/
    ├── ComfyUI-AnimateDiff-Evolved/
    ├── ComfyUI-VideoHelperSuite/
    └── ComfyUI_IPAdapter_plus/         # Optional
```

## Available Reaction Types

```
shocked     - Wide eyes, dramatic surprise
laughing    - Big smile, head tilted back
facepalm    - Hand on face, disappointed
nodding     - Agreement, slight smile
confused    - Raised eyebrow, tilted head
excited     - Jumping, arms raised
nervous     - Worried expression
angry       - Furrowed brows
sad         - Drooping eyes, frown
smug        - Knowing smirk
thinking    - Hand on chin
eye_roll    - Exasperated expression
cringe      - Squinting, uncomfortable
sipping_tea - Side eye, watching drama
```

## Troubleshooting

### "AnimateDiff not installed"
- Make sure you cloned to `custom_nodes` folder
- Restart ComfyUI after installing

### "No motion models found"
- Check that `.ckpt` files are in `models/animatediff_models/`
- Model names are case-sensitive

### Out of VRAM
- Use `--lowvram` flag when starting ComfyUI
- Reduce `REACTION_FRAMES` in config.py
- Use smaller resolution (384x384 instead of 512x512)

### Video output not working
- Make sure ComfyUI-VideoHelperSuite is installed
- Check ffmpeg is installed on your system

## Enable in Pipeline

Once everything is working, enable in `config.py`:

```python
USE_LOCAL_ANIMATEDIFF = True
```

Then run the pipeline:

```powershell
python pipeline.py
```

Reactions will be automatically detected from commentary text and animated!
