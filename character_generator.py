"""
Character Video Generator
Uses Replicate API or Local ComfyUI for AI character generation and lip sync
- Flux for character image generation (Replicate or local)
- Hallo2 for audio-driven talking head animation (Replicate only)
"""

import replicate
import requests
import time
import base64
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import json

import config

# Import local ComfyUI generator if available
try:
    from local_comfyui import LocalCharacterGenerator
    LOCAL_COMFYUI_AVAILABLE = True
except ImportError:
    LOCAL_COMFYUI_AVAILABLE = False

# Import local AnimateDiff for reactions
try:
    from local_animatediff import LocalReactionGenerator, REACTION_PROMPTS
    LOCAL_ANIMATEDIFF_AVAILABLE = True
except ImportError:
    LOCAL_ANIMATEDIFF_AVAILABLE = False


@dataclass
class CharacterVideo:
    """Generated character video segment"""
    segment_index: int
    audio_path: Path
    video_path: Path
    duration: float


class CharacterGenerator:
    """Generates AI character videos with lip sync using Replicate or local ComfyUI"""
    
    def __init__(self, use_local: bool = None, use_animatediff: bool = None):
        # Determine whether to use local ComfyUI for image generation
        if use_local is None:
            use_local = config.USE_LOCAL_COMFYUI
        
        self.use_local = use_local and LOCAL_COMFYUI_AVAILABLE
        
        if self.use_local:
            self.local_generator = LocalCharacterGenerator(config.COMFYUI_URL)
            print("Using local ComfyUI for image generation")
        else:
            self.local_generator = None
        
        # Determine whether to use local AnimateDiff for reactions
        if use_animatediff is None:
            use_animatediff = config.USE_LOCAL_ANIMATEDIFF
        
        self.use_animatediff = use_animatediff and LOCAL_ANIMATEDIFF_AVAILABLE
        
        if self.use_animatediff:
            self.reaction_generator = LocalReactionGenerator(config.COMFYUI_URL)
            print("Using local AnimateDiff for reactions")
        else:
            self.reaction_generator = None
            # Need Replicate client for Hallo2 lip sync if not using AnimateDiff
            print("Using Replicate API for lip sync")
        
        # Always need Replicate client for Hallo2 lip sync (if not using AnimateDiff)
        self.client = replicate.Client(api_token=config.REPLICATE_API_KEY)
        self.character_image_path = config.CHARACTER_IMAGE_PATH
        
    def generate_character_image(
        self,
        prompt: str = None,
        output_path: Path = None
    ) -> Path:
        """
        Generate a character image using Flux.
        Uses local ComfyUI if enabled, otherwise Replicate.
        Only needs to be run once to create your recurring character.
        """
        
        if prompt is None:
            prompt = config.CHARACTER_PROMPT
        
        if output_path is None:
            output_path = config.CHARACTER_IMAGE_PATH
        
        print(f"Generating character image...")
        print(f"  Prompt: {prompt[:80]}...")
        
        # Use local ComfyUI if enabled
        if self.use_local and self.local_generator:
            print("  Using local ComfyUI...")
            success = self.local_generator.generate_character_image(
                prompt_text=prompt,
                output_path=output_path
            )
            if success:
                return output_path
            else:
                raise Exception("Local ComfyUI generation failed")
        
        # Otherwise use Replicate
        print("  Using Replicate API...")
        output = self.client.run(
            config.FLUX_MODEL,
            input={
                "prompt": prompt,
                "aspect_ratio": "1:1",  # Square for talking head
                "num_outputs": 1,
                "output_format": "png",
                "output_quality": 90,
                "num_inference_steps": 28,
                "guidance": 3.5
            }
        )
        
        # Download the generated image
        image_url = output[0] if isinstance(output, list) else output
        
        response = requests.get(image_url)
        if response.status_code == 200:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"  Character image saved: {output_path}")
            return output_path
        else:
            raise Exception(f"Failed to download image: {response.status_code}")
    
    def generate_talking_video(
        self,
        audio_path: Path,
        output_path: Path,
        character_image: Path = None
    ) -> bool:
        """
        Generate a talking head video from audio using Hallo2.
        """
        
        if character_image is None:
            character_image = self.character_image_path
        
        if not character_image.exists():
            print(f"Character image not found: {character_image}")
            print("Run generate_character_image() first or set CHARACTER_IMAGE_PATH")
            return False
        
        if not audio_path.exists():
            print(f"Audio file not found: {audio_path}")
            return False
        
        print(f"  Generating talking video for: {audio_path.name}")
        
        # Read and encode files for API
        with open(character_image, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        with open(audio_path, 'rb') as f:
            audio_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Determine image mime type
        img_suffix = character_image.suffix.lower()
        img_mime = "image/png" if img_suffix == ".png" else "image/jpeg"
        
        # Determine audio mime type
        audio_suffix = audio_path.suffix.lower()
        audio_mime = "audio/mpeg" if audio_suffix == ".mp3" else "audio/wav"
        
        try:
            output = self.client.run(
                config.HALLO2_MODEL,
                input={
                    "face_image": f"data:{img_mime};base64,{image_data}",
                    "driving_audio": f"data:{audio_mime};base64,{audio_data}",
                    "pose_weight": config.HALLO2_POSE_WEIGHT,
                    "face_weight": config.HALLO2_FACE_WEIGHT,
                    "lip_weight": config.HALLO2_LIP_WEIGHT,
                    "face_expand_ratio": config.HALLO2_FACE_EXPAND_RATIO,
                }
            )
            
            # Download the generated video
            video_url = output if isinstance(output, str) else output[0]
            
            response = requests.get(video_url)
            if response.status_code == 200:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"    Saved: {output_path.name}")
                return True
            else:
                print(f"    Failed to download video: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"    Error generating video: {e}")
            return False
    
    def generate_all_commentary_videos(
        self,
        audio_segments: list,
        output_dir: Path,
        script_segments: list = None
    ) -> list[CharacterVideo]:
        """
        Generate character videos for all commentary segments.
        Uses AnimateDiff for reactions if enabled, otherwise Hallo2 for lip sync.
        """
        
        output_dir.mkdir(parents=True, exist_ok=True)
        character_videos = []
        
        # Filter to only commentary segments
        commentary_segments = [
            seg for seg in audio_segments 
            if seg.voice == "commentator"
        ]
        
        print(f"\nGenerating character videos for {len(commentary_segments)} commentary segments...")
        
        # Use local AnimateDiff if enabled
        if self.use_animatediff and self.reaction_generator:
            print("  Mode: Local AnimateDiff reactions")
            
            for i, audio_seg in enumerate(commentary_segments):
                print(f"  [{i+1}/{len(commentary_segments)}] Processing segment {audio_seg.segment_index}...")
                
                # Get the script segment text for reaction detection
                commentary_text = ""
                if script_segments:
                    for script_seg in script_segments:
                        if hasattr(script_seg, 'voice') and script_seg.voice == "commentator":
                            commentary_text = script_seg.text
                            break
                
                # Detect reaction type
                reaction_type = self.reaction_generator.detect_reaction_type(
                    audio_seg.text if hasattr(audio_seg, 'text') else commentary_text
                )
                print(f"    Reaction: {reaction_type}")
                
                video_path = output_dir / f"character_{audio_seg.segment_index:03d}.mp4"
                
                success = self.reaction_generator.generate_reaction(
                    reaction_type=reaction_type,
                    character_image=self.character_image_path,
                    output_path=video_path
                )
                
                if success:
                    character_videos.append(CharacterVideo(
                        segment_index=audio_seg.segment_index,
                        audio_path=audio_seg.audio_path,
                        video_path=video_path,
                        duration=audio_seg.duration
                    ))
                
                time.sleep(0.5)
        
        else:
            # Use Replicate Hallo2 for lip sync
            print("  Mode: Replicate Hallo2 lip sync")
            
            for i, audio_seg in enumerate(commentary_segments):
                print(f"  [{i+1}/{len(commentary_segments)}] Processing segment {audio_seg.segment_index}...")
                
                video_path = output_dir / f"character_{audio_seg.segment_index:03d}.mp4"
                
                success = self.generate_talking_video(
                    audio_path=audio_seg.audio_path,
                    output_path=video_path
                )
                
                if success:
                    character_videos.append(CharacterVideo(
                        segment_index=audio_seg.segment_index,
                        audio_path=audio_seg.audio_path,
                        video_path=video_path,
                        duration=audio_seg.duration
                    ))
                
                # Small delay to avoid rate limits
                time.sleep(0.5)
        
        print(f"Generated {len(character_videos)} character videos")
        return character_videos


class CharacterManager:
    """Manages character creation and storage"""
    
    def __init__(self, use_local: bool = None, use_animatediff: bool = None):
        self.generator = CharacterGenerator(use_local=use_local, use_animatediff=use_animatediff)
        self.characters_dir = config.CHARACTERS_DIR
        self.characters_dir.mkdir(parents=True, exist_ok=True)
    
    def get_or_create_character(self, style: str = "default") -> Path:
        """Get existing character image or create new one"""
        
        char_path = self.characters_dir / f"character_{style}.png"
        
        if char_path.exists():
            print(f"Using existing character: {char_path}")
            return char_path
        
        # Get prompt for this style
        prompt = config.CHARACTER_STYLES.get(style, config.CHARACTER_PROMPT)
        
        print(f"Creating new character with style: {style}")
        return self.generator.generate_character_image(
            prompt=prompt,
            output_path=char_path
        )
    
    def list_characters(self) -> list[Path]:
        """List all available character images"""
        return list(self.characters_dir.glob("*.png"))
    
    def create_custom_character(self, prompt: str, name: str) -> Path:
        """Create a custom character with specific prompt"""
        
        char_path = self.characters_dir / f"character_{name}.png"
        return self.generator.generate_character_image(
            prompt=prompt,
            output_path=char_path
        )


# =============================================================================
# Alternative Models (can swap in config.py)
# =============================================================================

class AlternativeGenerators:
    """
    Alternative Replicate models you can use.
    Change the model in config.py to switch.
    """
    
    MODELS = {
        # Talking head / lip sync
        "hallo2": "fudan-generative-ai/hallo2",  # Best quality
        "hallo": "fudan-generative-ai/hallo",    # Original, faster
        "sadtalker": "cjwbw/sadtalker",          # Good for stylized
        "liveportrait": "fofr/liveportrait",     # Fast, expressive
        "wav2lip": "devxpy/wav2lip",             # Classic, reliable
        
        # Image generation
        "flux-schnell": "black-forest-labs/flux-schnell",  # Fast
        "flux-dev": "black-forest-labs/flux-dev",          # Higher quality
        "sdxl": "stability-ai/sdxl",                       # Good alternative
        
        # Video generation (if you want full video gen)
        "wan21": "wavymulder/wan2.1",            # Best open source t2v
        "cogvideox": "fofr/cogvideox-5b",        # Good quality
    }


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Character Video Generator")
    parser.add_argument('--create-character', action='store_true',
                       help='Generate a new character image')
    parser.add_argument('--style', default='default',
                       help='Character style (default, anime, realistic, cartoon)')
    parser.add_argument('--custom-prompt', type=str,
                       help='Custom prompt for character generation')
    parser.add_argument('--test-video', type=str,
                       help='Path to audio file to test video generation')
    parser.add_argument('--list', action='store_true',
                       help='List available characters')
    parser.add_argument('--local', action='store_true',
                       help='Use local ComfyUI instead of Replicate for image generation')
    parser.add_argument('--check-local', action='store_true',
                       help='Check if local ComfyUI is running')
    
    args = parser.parse_args()
    
    # Check local ComfyUI status
    if args.check_local:
        if LOCAL_COMFYUI_AVAILABLE:
            from local_comfyui import LocalCharacterGenerator
            gen = LocalCharacterGenerator(config.COMFYUI_URL)
            if gen.client.is_running():
                print("✓ ComfyUI is running at", config.COMFYUI_URL)
            else:
                print("✗ ComfyUI is not running")
                print("  Start it with: python main.py --lowvram")
        else:
            print("✗ Local ComfyUI module not available")
        exit()
    
    manager = CharacterManager(use_local=args.local)
    
    if args.list:
        characters = manager.list_characters()
        print(f"\nAvailable characters ({len(characters)}):")
        for char in characters:
            print(f"  - {char.name}")
    
    elif args.create_character:
        if args.custom_prompt:
            char_path = manager.create_custom_character(
                prompt=args.custom_prompt,
                name="custom"
            )
        else:
            char_path = manager.get_or_create_character(style=args.style)
        print(f"\nCharacter created: {char_path}")
    
    elif args.test_video:
        audio_path = Path(args.test_video)
        if not audio_path.exists():
            print(f"Audio file not found: {audio_path}")
        else:
            generator = CharacterGenerator(use_local=args.local)
            
            # Ensure we have a character
            char_path = manager.get_or_create_character(style=args.style)
            
            # Generate test video
            output_path = config.TEMP_DIR / "test_character_video.mp4"
            success = generator.generate_talking_video(
                audio_path=audio_path,
                output_path=output_path,
                character_image=char_path
            )
            
            if success:
                print(f"\nTest video created: {output_path}")
    
    else:
        print("Character Video Generator")
        print("-" * 40)
        print("\nUsage examples:")
        print("  python character_generator.py --create-character")
        print("  python character_generator.py --create-character --style anime")
        print("  python character_generator.py --test-video audio.mp3")
        print("  python character_generator.py --list")
        print("\nAvailable styles:", list(config.CHARACTER_STYLES.keys()))
