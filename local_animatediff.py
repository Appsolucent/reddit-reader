"""
Local AnimateDiff Character Reactions
Generates animated character reaction clips using ComfyUI + AnimateDiff
"""

import requests
import json
import time
import uuid
import random
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import config


# =============================================================================
# REACTION DEFINITIONS
# =============================================================================

REACTION_PROMPTS = {
    "shocked": {
        "prompt": "character with shocked surprised expression, wide eyes, open mouth, dramatic reaction",
        "motion_scale": 1.1,
    },
    "laughing": {
        "prompt": "character laughing hard, eyes closed, big smile, head tilted back, joyful",
        "motion_scale": 1.2,
    },
    "facepalm": {
        "prompt": "character facepalm, hand on face, disappointed expression, shaking head",
        "motion_scale": 0.9,
    },
    "nodding": {
        "prompt": "character nodding in agreement, slight smile, understanding expression",
        "motion_scale": 0.8,
    },
    "confused": {
        "prompt": "character confused expression, raised eyebrow, tilted head, questioning look",
        "motion_scale": 0.9,
    },
    "excited": {
        "prompt": "character very excited, jumping with joy, arms raised, huge smile, celebrating",
        "motion_scale": 1.3,
    },
    "nervous": {
        "prompt": "character nervous anxious expression, biting lip, worried eyes, fidgeting",
        "motion_scale": 0.8,
    },
    "angry": {
        "prompt": "character angry frustrated expression, furrowed brows, clenched jaw",
        "motion_scale": 1.0,
    },
    "sad": {
        "prompt": "character sad disappointed expression, drooping eyes, frown, dejected",
        "motion_scale": 0.7,
    },
    "smug": {
        "prompt": "character smug satisfied expression, knowing smirk, raised eyebrow, confident",
        "motion_scale": 0.8,
    },
    "thinking": {
        "prompt": "character thinking pondering expression, hand on chin, looking up, contemplating",
        "motion_scale": 0.7,
    },
    "eye_roll": {
        "prompt": "character rolling eyes, exasperated expression, slight head shake",
        "motion_scale": 0.9,
    },
    "cringe": {
        "prompt": "character cringing, squinting eyes, teeth showing, uncomfortable expression",
        "motion_scale": 0.9,
    },
    "sipping_tea": {
        "prompt": "character sipping drink, side eye, watching drama unfold, entertained",
        "motion_scale": 0.7,
    },
}

# Map commentary keywords to reactions
KEYWORD_TO_REACTION = {
    # Shocked reactions
    "what": "shocked",
    "wait": "shocked", 
    "hold up": "shocked",
    "excuse me": "shocked",
    "no way": "shocked",
    "seriously": "shocked",
    
    # Laughing reactions
    "lmao": "laughing",
    "lol": "laughing",
    "hilarious": "laughing",
    "funny": "laughing",
    "dead": "laughing",
    "crying": "laughing",
    
    # Facepalm reactions
    "stupid": "facepalm",
    "dumb": "facepalm",
    "idiot": "facepalm",
    "mistake": "facepalm",
    "bad idea": "facepalm",
    
    # Excited reactions
    "yes": "excited",
    "amazing": "excited",
    "perfect": "excited",
    "love": "excited",
    "brilliant": "excited",
    
    # Nervous reactions
    "uh oh": "nervous",
    "oh no": "nervous",
    "this is bad": "nervous",
    "worried": "nervous",
    
    # Angry reactions
    "angry": "angry",
    "furious": "angry",
    "mad": "angry",
    "rage": "angry",
    
    # Smug reactions
    "deserve": "smug",
    "karma": "smug",
    "told you": "smug",
    "called it": "smug",
    "revenge": "smug",
    
    # Cringe reactions
    "cringe": "cringe",
    "awkward": "cringe",
    "uncomfortable": "cringe",
    "yikes": "cringe",
    
    # Default
    "wow": "shocked",
    "oh": "thinking",
}


@dataclass
class AnimatedReaction:
    """Generated animated reaction clip"""
    segment_index: int
    reaction_type: str
    video_path: Path
    duration: float


class AnimateDiffClient:
    """Client for ComfyUI with AnimateDiff"""
    
    def __init__(self, server_url: str = "http://127.0.0.1:8188"):
        self.server_url = server_url
        self.client_id = str(uuid.uuid4())
    
    def is_running(self) -> bool:
        """Check if ComfyUI is running"""
        try:
            response = requests.get(f"{self.server_url}/system_stats", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def check_animatediff_installed(self) -> bool:
        """Check if AnimateDiff nodes are available"""
        try:
            response = requests.get(f"{self.server_url}/object_info", timeout=5)
            nodes = response.json()
            # Check for AnimateDiff nodes
            animatediff_nodes = [
                "ADE_AnimateDiffLoaderGen1",
                "AnimateDiffLoaderWithContext", 
                "ADE_UseEvolvedSampling"
            ]
            for node in animatediff_nodes:
                if node in nodes:
                    return True
            return False
        except:
            return False
    
    def get_available_motion_models(self) -> list:
        """Get list of available AnimateDiff motion models"""
        try:
            response = requests.get(f"{self.server_url}/object_info", timeout=5)
            nodes = response.json()
            
            # Check different AnimateDiff loader nodes
            for node_name in ["ADE_AnimateDiffLoaderGen1", "AnimateDiffLoaderWithContext"]:
                if node_name in nodes:
                    node_info = nodes[node_name]
                    if "input" in node_info and "required" in node_info["input"]:
                        req = node_info["input"]["required"]
                        if "model_name" in req:
                            return req["model_name"][0]
            return []
        except:
            return []
    
    def queue_prompt(self, prompt: dict) -> str:
        """Queue a prompt and return the prompt_id"""
        data = {
            "prompt": prompt,
            "client_id": self.client_id
        }
        response = requests.post(
            f"{self.server_url}/prompt",
            json=data
        )
        
        result = response.json()
        
        if "error" in result:
            error_msg = result.get("error", {})
            node_errors = result.get("node_errors", {})
            print(f"\n  ComfyUI Error: {error_msg}")
            if node_errors:
                for node_id, errors in node_errors.items():
                    print(f"  Node {node_id}: {errors}")
            raise Exception(f"ComfyUI rejected prompt: {error_msg}")
        
        if "prompt_id" not in result:
            raise Exception(f"No prompt_id in response: {result}")
        
        return result['prompt_id']
    
    def get_history(self, prompt_id: str) -> dict:
        """Get the history/output for a prompt"""
        response = requests.get(f"{self.server_url}/history/{prompt_id}")
        return response.json()
    
    def get_video(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """Download a generated video"""
        import urllib.parse
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }
        url = f"{self.server_url}/view?{urllib.parse.urlencode(params)}"
        response = requests.get(url)
        return response.content
    
    def wait_for_completion(self, prompt_id: str, timeout: int = 600) -> dict:
        """Wait for a prompt to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            history = self.get_history(prompt_id)
            
            if prompt_id in history:
                return history[prompt_id]
            
            time.sleep(2)
        
        raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout} seconds")


class LocalReactionGenerator:
    """Generate animated character reactions using local AnimateDiff"""
    
    def __init__(self, comfyui_url: str = None):
        if comfyui_url is None:
            comfyui_url = config.COMFYUI_URL
        self.client = AnimateDiffClient(comfyui_url)
        self.character_image_path = config.CHARACTER_IMAGE_PATH
    
    def detect_reaction_type(self, commentary_text: str) -> str:
        """Detect appropriate reaction type from commentary text"""
        text_lower = commentary_text.lower()
        
        # Check for keyword matches
        for keyword, reaction in KEYWORD_TO_REACTION.items():
            if keyword in text_lower:
                return reaction
        
        # Default reactions based on punctuation/tone
        if "!" in commentary_text:
            return random.choice(["shocked", "excited", "laughing"])
        if "?" in commentary_text:
            return random.choice(["confused", "thinking"])
        
        # Random default
        return random.choice(["nodding", "thinking", "smug"])
    
    def generate_reaction(
        self,
        reaction_type: str,
        character_image: Path,
        output_path: Path,
        duration_frames: int = 16  # ~0.5 seconds at 30fps
    ) -> bool:
        """Generate an animated reaction clip"""
        
        if not self.client.is_running():
            print("  Error: ComfyUI is not running!")
            return False
        
        if not self.client.check_animatediff_installed():
            print("  Error: AnimateDiff not installed in ComfyUI!")
            print("  Install: https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved")
            return False
        
        if reaction_type not in REACTION_PROMPTS:
            print(f"  Unknown reaction type: {reaction_type}, using 'nodding'")
            reaction_type = "nodding"
        
        reaction_config = REACTION_PROMPTS[reaction_type]
        
        print(f"  Generating {reaction_type} reaction...")
        
        # Build the AnimateDiff prompt
        api_prompt = self._build_animatediff_prompt(
            character_image=character_image,
            reaction_prompt=reaction_config["prompt"],
            motion_scale=reaction_config["motion_scale"],
            num_frames=duration_frames
        )
        
        try:
            prompt_id = self.client.queue_prompt(api_prompt)
            print(f"  Queued: {prompt_id}")
            
            result = self.client.wait_for_completion(prompt_id, timeout=300)
            
            # Find the output video
            outputs = result.get("outputs", {})
            for node_id, node_output in outputs.items():
                if "gifs" in node_output:
                    for gif_info in node_output["gifs"]:
                        filename = gif_info["filename"]
                        subfolder = gif_info.get("subfolder", "")
                        
                        video_data = self.client.get_video(filename, subfolder)
                        
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(output_path, 'wb') as f:
                            f.write(video_data)
                        
                        print(f"  Saved: {output_path}")
                        return True
                
                # Also check for images (some setups output as image sequence)
                if "images" in node_output:
                    # Would need to convert image sequence to video
                    # For now, just note this
                    print("  Got image sequence output - video conversion needed")
            
            print("  No video output found")
            return False
            
        except Exception as e:
            print(f"  Error: {e}")
            return False
    
    def _build_animatediff_prompt(
        self,
        character_image: Path,
        reaction_prompt: str,
        motion_scale: float,
        num_frames: int
    ) -> dict:
        """Build AnimateDiff workflow prompt"""
        
        import base64
        
        # Load character image as base64
        with open(character_image, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        seed = random.randint(0, 2**32 - 1)
        
        # This is a simplified AnimateDiff workflow
        # You may need to adjust based on your installed nodes
        return {
            # Load character image
            "1": {
                "class_type": "LoadImage",
                "inputs": {
                    "image": character_image.name,  # Assumes image is in ComfyUI input folder
                }
            },
            # Or use base64 if LoadImageFromBase64 is available
            
            # Checkpoint loader
            "2": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors"  # Adjust to your model
                }
            },
            
            # AnimateDiff Loader
            "3": {
                "class_type": "ADE_AnimateDiffLoaderGen1",
                "inputs": {
                    "model_name": "mm_sd_v15_v2.ckpt",  # Adjust to your motion model
                    "beta_schedule": "autoselect",
                    "motion_scale": motion_scale,
                    "apply_v2_models_properly": True,
                }
            },
            
            # CLIP Text Encode (positive)
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": reaction_prompt,
                    "clip": ["2", 1]
                }
            },
            
            # CLIP Text Encode (negative)
            "5": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "blurry, low quality, distorted, deformed",
                    "clip": ["2", 1]
                }
            },
            
            # Empty Latent Image (for animation frames)
            "6": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": num_frames
                }
            },
            
            # KSampler
            "7": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": 20,
                    "cfg": 7,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["3", 0],  # From AnimateDiff
                    "positive": ["4", 0],
                    "negative": ["5", 0],
                    "latent_image": ["6", 0]
                }
            },
            
            # VAE Decode
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["7", 0],
                    "vae": ["2", 2]
                }
            },
            
            # Save as animated GIF/video
            "9": {
                "class_type": "VHS_VideoCombine",
                "inputs": {
                    "images": ["8", 0],
                    "frame_rate": 8,
                    "loop_count": 0,
                    "filename_prefix": "reaction",
                    "format": "video/h264-mp4",
                    "pingpong": False,
                    "save_output": True
                }
            }
        }
    
    def generate_all_reactions(
        self,
        script_segments: list,
        audio_segments: list,
        character_image: Path,
        output_dir: Path
    ) -> list[AnimatedReaction]:
        """Generate reactions for all commentary segments"""
        
        output_dir.mkdir(parents=True, exist_ok=True)
        reactions = []
        
        # Filter to commentary segments only
        commentary_segments = [
            (seg, audio) for seg, audio in zip(script_segments, audio_segments)
            if seg.voice == "commentator"
        ]
        
        print(f"\nGenerating {len(commentary_segments)} reaction animations...")
        
        for i, (script_seg, audio_seg) in enumerate(commentary_segments):
            print(f"  [{i+1}/{len(commentary_segments)}] Segment {audio_seg.segment_index}")
            
            # Detect reaction type from commentary text
            reaction_type = self.detect_reaction_type(script_seg.text)
            print(f"    Detected reaction: {reaction_type}")
            
            # Generate the reaction
            output_path = output_dir / f"reaction_{audio_seg.segment_index:03d}.mp4"
            
            success = self.generate_reaction(
                reaction_type=reaction_type,
                character_image=character_image,
                output_path=output_path
            )
            
            if success:
                reactions.append(AnimatedReaction(
                    segment_index=audio_seg.segment_index,
                    reaction_type=reaction_type,
                    video_path=output_path,
                    duration=audio_seg.duration
                ))
            
            time.sleep(1)  # Small delay between generations
        
        print(f"Generated {len(reactions)} reaction animations")
        return reactions


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Local AnimateDiff Reaction Generator")
    parser.add_argument('--check', action='store_true',
                       help='Check if AnimateDiff is installed and show available models')
    parser.add_argument('--reaction', type=str, choices=list(REACTION_PROMPTS.keys()),
                       help='Generate a specific reaction type')
    parser.add_argument('--character', type=str,
                       help='Path to character image')
    parser.add_argument('--output', type=str, default='./temp/test_reaction.mp4',
                       help='Output path for the video')
    parser.add_argument('--list-reactions', action='store_true',
                       help='List all available reaction types')
    parser.add_argument('--detect', type=str,
                       help='Detect reaction type from text')
    
    args = parser.parse_args()
    
    if args.list_reactions:
        print("\nAvailable reaction types:")
        print("-" * 50)
        for reaction, config in REACTION_PROMPTS.items():
            print(f"  {reaction:15} - {config['prompt'][:50]}...")
        exit()
    
    if args.detect:
        generator = LocalReactionGenerator()
        reaction = generator.detect_reaction_type(args.detect)
        print(f"\nText: \"{args.detect}\"")
        print(f"Detected reaction: {reaction}")
        exit()
    
    generator = LocalReactionGenerator()
    
    if args.check:
        print("Checking AnimateDiff setup...")
        print("-" * 50)
        
        if generator.client.is_running():
            print("✓ ComfyUI is running")
            
            if generator.client.check_animatediff_installed():
                print("✓ AnimateDiff nodes found")
                
                models = generator.client.get_available_motion_models()
                print(f"\nMotion models available: {len(models)}")
                for m in models[:10]:  # Show first 10
                    print(f"  - {m}")
            else:
                print("✗ AnimateDiff not installed")
                print("\nInstall instructions:")
                print("  cd ComfyUI/custom_nodes")
                print("  git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved")
                print("  pip install -r requirements.txt")
        else:
            print("✗ ComfyUI is not running")
    
    elif args.reaction:
        if not args.character:
            # Try default character
            char_path = config.CHARACTER_IMAGE_PATH
            if not char_path.exists():
                print("Error: No character image specified and default not found")
                print("  Use --character path/to/image.png")
                exit(1)
        else:
            char_path = Path(args.character)
        
        output_path = Path(args.output)
        
        success = generator.generate_reaction(
            reaction_type=args.reaction,
            character_image=char_path,
            output_path=output_path
        )
        
        if success:
            print(f"\n✓ Reaction generated: {output_path}")
        else:
            print("\n✗ Failed to generate reaction")
    
    else:
        print("Local AnimateDiff Reaction Generator")
        print("-" * 50)
        print("\nUsage:")
        print("  python local_animatediff.py --check")
        print("  python local_animatediff.py --list-reactions")
        print("  python local_animatediff.py --detect \"Oh no, this is bad!\"")
        print("  python local_animatediff.py --reaction shocked --character char.png")
        print("\nRequired ComfyUI custom nodes:")
        print("  - ComfyUI-AnimateDiff-Evolved")
        print("  - ComfyUI-VideoHelperSuite (for video output)")
