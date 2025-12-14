"""
Local ComfyUI Character Generator
Generates character images using local ComfyUI with Flux
"""

import requests
import json
import time
import uuid
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional

import config


class ComfyUIClient:
    """Client for interacting with local ComfyUI API"""
    
    def __init__(self, server_url: str = "http://127.0.0.1:8188"):
        self.server_url = server_url
        self.client_id = str(uuid.uuid4())
    
    def is_running(self) -> bool:
        """Check if ComfyUI server is running"""
        try:
            response = requests.get(f"{self.server_url}/system_stats", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_object_info(self) -> dict:
        """Get available node types from ComfyUI"""
        try:
            response = requests.get(f"{self.server_url}/object_info", timeout=5)
            return response.json()
        except:
            return {}
    
    def check_models(self) -> dict:
        """Check what models are available in ComfyUI"""
        info = self.get_object_info()
        
        models = {
            "unet": [],
            "clip": [],
            "vae": []
        }
        
        # Check UNETLoader
        if "UNETLoader" in info:
            unet_info = info["UNETLoader"]
            if "input" in unet_info and "required" in unet_info["input"]:
                req = unet_info["input"]["required"]
                if "unet_name" in req:
                    models["unet"] = req["unet_name"][0]
        
        # Check CLIPLoader
        if "CLIPLoader" in info:
            clip_info = info["CLIPLoader"]
            if "input" in clip_info and "required" in clip_info["input"]:
                req = clip_info["input"]["required"]
                if "clip_name" in req:
                    models["clip"] = req["clip_name"][0]
        
        # Check VAELoader
        if "VAELoader" in info:
            vae_info = info["VAELoader"]
            if "input" in vae_info and "required" in vae_info["input"]:
                req = vae_info["input"]["required"]
                if "vae_name" in req:
                    models["vae"] = req["vae_name"][0]
        
        return models
    
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
        
        # Check for errors
        if "error" in result:
            error_msg = result.get("error", {})
            node_errors = result.get("node_errors", {})
            print(f"\n  ComfyUI Error: {error_msg}")
            if node_errors:
                print(f"  Node errors: {json.dumps(node_errors, indent=2)}")
            raise Exception(f"ComfyUI rejected prompt: {error_msg}")
        
        if "prompt_id" not in result:
            print(f"\n  Unexpected response: {result}")
            raise Exception(f"No prompt_id in response: {result}")
        
        return result['prompt_id']
    
    def get_history(self, prompt_id: str) -> dict:
        """Get the history/output for a prompt"""
        response = requests.get(f"{self.server_url}/history/{prompt_id}")
        return response.json()
    
    def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """Download a generated image"""
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }
        url = f"{self.server_url}/view?{urllib.parse.urlencode(params)}"
        response = requests.get(url)
        return response.content
    
    def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> dict:
        """Wait for a prompt to complete and return the output"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            history = self.get_history(prompt_id)
            
            if prompt_id in history:
                return history[prompt_id]
            
            time.sleep(1)
        
        raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout} seconds")


class LocalCharacterGenerator:
    """Generate character images using local ComfyUI"""
    
    def __init__(self, comfyui_url: str = "http://127.0.0.1:8188"):
        self.client = ComfyUIClient(comfyui_url)
        self.workflow_path = Path(__file__).parent / "comfyui_workflows" / "flux_character.json"
    
    def load_workflow(self) -> dict:
        """Load the Flux character workflow"""
        if not self.workflow_path.exists():
            raise FileNotFoundError(
                f"Workflow not found: {self.workflow_path}\n"
                "Make sure flux_character.json is in comfyui_workflows/"
            )
        
        with open(self.workflow_path, 'r') as f:
            return json.load(f)
    
    def workflow_to_api_format(self, workflow: dict) -> dict:
        """Convert workflow format to API prompt format"""
        # The workflow JSON needs to be converted to API format
        # This extracts the nodes and their configurations
        prompt = {}
        
        for node in workflow.get("nodes", []):
            node_id = str(node["id"])
            prompt[node_id] = {
                "class_type": node["type"],
                "inputs": {}
            }
            
            # Add widget values as inputs
            if "widgets_values" in node:
                widget_values = node["widgets_values"]
                
                # Map widget values based on node type
                if node["type"] == "CLIPLoader":
                    prompt[node_id]["inputs"]["clip_name"] = widget_values[0]
                    prompt[node_id]["inputs"]["type"] = widget_values[1]
                
                elif node["type"] == "CLIPTextEncode":
                    prompt[node_id]["inputs"]["text"] = widget_values[0]
                
                elif node["type"] == "UNETLoader":
                    prompt[node_id]["inputs"]["unet_name"] = widget_values[0]
                    prompt[node_id]["inputs"]["weight_dtype"] = widget_values[1]
                
                elif node["type"] == "EmptySD3LatentImage":
                    prompt[node_id]["inputs"]["width"] = widget_values[0]
                    prompt[node_id]["inputs"]["height"] = widget_values[1]
                    prompt[node_id]["inputs"]["batch_size"] = widget_values[2]
                
                elif node["type"] == "KSampler":
                    prompt[node_id]["inputs"]["seed"] = widget_values[0]
                    prompt[node_id]["inputs"]["control_after_generate"] = widget_values[1]
                    prompt[node_id]["inputs"]["steps"] = widget_values[2]
                    prompt[node_id]["inputs"]["cfg"] = widget_values[3]
                    prompt[node_id]["inputs"]["sampler_name"] = widget_values[4]
                    prompt[node_id]["inputs"]["scheduler"] = widget_values[5]
                    prompt[node_id]["inputs"]["denoise"] = widget_values[6]
                
                elif node["type"] == "VAELoader":
                    prompt[node_id]["inputs"]["vae_name"] = widget_values[0]
                
                elif node["type"] == "SaveImage":
                    prompt[node_id]["inputs"]["filename_prefix"] = widget_values[0]
            
            # Add links as inputs
            if "inputs" in node:
                for input_data in node["inputs"]:
                    if input_data.get("link") is not None:
                        # Find the source node for this link
                        link_id = input_data["link"]
                        for link in workflow.get("links", []):
                            if link[0] == link_id:
                                source_node_id = str(link[1])
                                source_slot = link[2]
                                prompt[node_id]["inputs"][input_data["name"]] = [source_node_id, source_slot]
                                break
        
        return prompt
    
    def generate_character_image(
        self,
        prompt_text: str,
        output_path: Path,
        seed: int = None
    ) -> bool:
        """Generate a character image using local ComfyUI"""
        
        # Check if ComfyUI is running
        if not self.client.is_running():
            print("  Error: ComfyUI is not running!")
            print("  Start ComfyUI with: python main.py --lowvram")
            return False
        
        print(f"Generating character with local ComfyUI...")
        print(f"  Prompt: {prompt_text[:80]}...")
        
        # Build the API prompt directly (simpler than converting workflow)
        api_prompt = self._build_flux_prompt(prompt_text, seed)
        
        try:
            # Queue the prompt
            prompt_id = self.client.queue_prompt(api_prompt)
            print(f"  Queued prompt: {prompt_id}")
            
            # Wait for completion
            print("  Generating... (this may take 1-3 minutes)")
            result = self.client.wait_for_completion(prompt_id, timeout=300)
            
            # Check for execution errors
            if "status" in result:
                status = result["status"]
                if status.get("status_str") == "error":
                    messages = status.get("messages", [])
                    print(f"  Execution error: {messages}")
                    return False
            
            # Get the output image
            outputs = result.get("outputs", {})
            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    for image_info in node_output["images"]:
                        filename = image_info["filename"]
                        subfolder = image_info.get("subfolder", "")
                        
                        # Download the image
                        image_data = self.client.get_image(filename, subfolder)
                        
                        # Save to output path
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(output_path, 'wb') as f:
                            f.write(image_data)
                        
                        print(f"  Saved: {output_path}")
                        return True
            
            print("  No image output found in result")
            print(f"  Result keys: {result.keys()}")
            return False
            
        except Exception as e:
            print(f"  Error: {e}")
            return False
    
    def _build_flux_prompt(self, prompt_text: str, seed: int = None) -> dict:
        """Build a Flux Schnell prompt for the API"""
        
        if seed is None:
            import random
            seed = random.randint(0, 2**32 - 1)
        
        return {
            "6": {
                "class_type": "CLIPLoader",
                "inputs": {
                    "clip_name": "t5xxl_fp8_e4m3fn.safetensors",
                    "type": "flux2"  # Use flux2 for newer ComfyUI versions
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt_text,
                    "clip": ["6", 0]
                }
            },
            "8": {
                "class_type": "UNETLoader",
                "inputs": {
                    "unet_name": "flux1-schnell-fp8.safetensors",
                    "weight_dtype": "fp8_e4m3fn"
                }
            },
            "9": {
                "class_type": "EmptySD3LatentImage",
                "inputs": {
                    "width": 1024,
                    "height": 1024,
                    "batch_size": 1
                }
            },
            "10": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": 4,
                    "cfg": 1,
                    "sampler_name": "euler",
                    "scheduler": "simple",
                    "denoise": 1,
                    "model": ["8", 0],
                    "positive": ["7", 0],
                    "negative": ["7", 0],  # Flux doesn't use negative, but needs a value
                    "latent_image": ["9", 0]
                }
            },
            "11": {
                "class_type": "VAELoader",
                "inputs": {
                    "vae_name": "ae.safetensors"
                }
            },
            "12": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["10", 0],
                    "vae": ["11", 0]
                }
            },
            "13": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "character",
                    "images": ["12", 0]
                }
            }
        }


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Local ComfyUI Character Generator")
    parser.add_argument('--prompt', type=str,
                       help='Character description prompt')
    parser.add_argument('--output', type=str, default='./assets/characters/character_local.png',
                       help='Output path for the image')
    parser.add_argument('--url', type=str, default='http://127.0.0.1:8188',
                       help='ComfyUI server URL')
    parser.add_argument('--check', action='store_true',
                       help='Check if ComfyUI is running and show available models')
    
    args = parser.parse_args()
    
    generator = LocalCharacterGenerator(args.url)
    
    if args.check:
        print("Checking ComfyUI setup...")
        print("-" * 50)
        
        if generator.client.is_running():
            print("✓ ComfyUI is running at", args.url)
            
            # Check available models
            print("\nChecking available models...")
            models = generator.client.check_models()
            
            print("\nUNET models (need flux1-schnell-fp8.safetensors):")
            if models["unet"]:
                for m in models["unet"]:
                    marker = "✓" if "flux" in m.lower() else " "
                    print(f"  {marker} {m}")
            else:
                print("  (none found)")
            
            print("\nCLIP models (need t5xxl_fp8_e4m3fn.safetensors):")
            if models["clip"]:
                for m in models["clip"]:
                    marker = "✓" if "t5xxl" in m.lower() else " "
                    print(f"  {marker} {m}")
            else:
                print("  (none found)")
            
            print("\nVAE models (need ae.safetensors):")
            if models["vae"]:
                for m in models["vae"]:
                    marker = "✓" if "ae" in m.lower() else " "
                    print(f"  {marker} {m}")
            else:
                print("  (none found)")
            
        else:
            print("✗ ComfyUI is not running")
            print("  Start it with: python main.py --lowvram")
    
    elif args.prompt:
        success = generator.generate_character_image(
            prompt_text=args.prompt,
            output_path=Path(args.output)
        )
        
        if success:
            print("\nCharacter generated successfully!")
        else:
            print("\nFailed to generate character")
            print("\nTroubleshooting:")
            print("  1. Run: python local_comfyui.py --check")
            print("  2. Make sure all required models are installed")
            print("  3. Check ComfyUI console for errors")
    
    else:
        print("Local ComfyUI Character Generator")
        print("-" * 40)
        print("\nUsage:")
        print("  python local_comfyui.py --check")
        print("  python local_comfyui.py --prompt \"your character description\"")
        print("\nRequired models in ComfyUI:")
        print("  models/unet/flux1-schnell-fp8.safetensors")
        print("  models/clip/t5xxl_fp8_e4m3fn.safetensors")
        print("  models/vae/ae.safetensors")
