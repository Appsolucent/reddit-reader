"""
Audio Generator
Generates multi-voice narration using ElevenLabs API
"""

import requests
import json
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import wave
import struct

import config
from script_generator import GeneratedScript, ScriptSegment


@dataclass
class AudioSegment:
    """Generated audio segment"""
    segment_index: int
    segment_type: str
    voice: str
    text: str
    audio_path: Path
    duration: float  # seconds


class AudioGenerator:
    def __init__(self):
        self.api_key = config.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
    
    def _get_voice_id(self, voice_type: str) -> str:
        """Get voice ID based on voice type"""
        if voice_type.lower() == "commentator":
            return config.COMMENTATOR_VOICE_ID
        return config.NARRATOR_VOICE_ID
    
    def _get_voice_settings(self, voice_type: str) -> dict:
        """Get voice settings based on voice type"""
        if voice_type.lower() == "commentator":
            return config.VOICE_SETTINGS["commentator"]
        return config.VOICE_SETTINGS["narrator"]
    
    def generate_audio(self, text: str, voice_type: str, output_path: Path) -> bool:
        """Generate audio for a single segment"""
        
        voice_id = self._get_voice_id(voice_type)
        voice_settings = self._get_voice_settings(voice_type)
        
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        payload = {
            "text": text,
            "model_id": config.ELEVENLABS_MODEL,
            "voice_settings": voice_settings
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            
            if response.status_code == 200:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                print(f"ElevenLabs API error: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"Error generating audio: {e}")
            return False
    
    def generate_all_audio(self, script: GeneratedScript, output_dir: Path) -> list[AudioSegment]:
        """Generate audio for all script segments"""
        
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_segments = []
        
        print(f"Generating audio for {len(script.segments)} segments...")
        
        for i, segment in enumerate(script.segments):
            print(f"  [{i+1}/{len(script.segments)}] {segment.type} ({segment.voice})...")
            
            # Output path for this segment
            audio_path = output_dir / f"segment_{i:03d}_{segment.type}_{segment.voice}.mp3"
            
            # Generate audio
            success = self.generate_audio(segment.text, segment.voice, audio_path)
            
            if success:
                # Get audio duration
                duration = self._get_audio_duration(audio_path)
                
                audio_segments.append(AudioSegment(
                    segment_index=i,
                    segment_type=segment.type,
                    voice=segment.voice,
                    text=segment.text,
                    audio_path=audio_path,
                    duration=duration
                ))
            else:
                print(f"    Failed to generate audio for segment {i}")
            
            # Rate limiting - ElevenLabs has limits
            time.sleep(0.5)
        
        print(f"Generated {len(audio_segments)} audio segments")
        return audio_segments
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of an audio file using ffprobe"""
        import subprocess
        
        try:
            result = subprocess.run(
                [
                    'ffprobe', '-v', 'quiet', '-show_entries',
                    'format=duration', '-of', 'csv=p=0', str(audio_path)
                ],
                capture_output=True,
                text=True
            )
            return float(result.stdout.strip())
        except Exception as e:
            # Fallback: estimate from file size (rough approximation)
            # MP3 at ~128kbps = ~16KB per second
            file_size = audio_path.stat().st_size
            return file_size / 16000
    
    def get_available_voices(self) -> list[dict]:
        """Get list of available ElevenLabs voices"""
        url = f"{self.base_url}/voices"
        headers = {"xi-api-key": self.api_key}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get('voices', [])
            return []
        except Exception as e:
            print(f"Error fetching voices: {e}")
            return []
    
    def check_subscription(self) -> dict:
        """Check ElevenLabs subscription status and character limits"""
        url = f"{self.base_url}/user/subscription"
        headers = {"xi-api-key": self.api_key}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            print(f"Error checking subscription: {e}")
            return {}


def generate_silence(duration: float, output_path: Path, sample_rate: int = 44100):
    """Generate a silent WAV file of specified duration"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    num_samples = int(duration * sample_rate)
    
    with wave.open(str(output_path), 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        silence = struct.pack('<' + 'h' * num_samples, *([0] * num_samples))
        wav_file.writeframes(silence)


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    generator = AudioGenerator()
    
    # Check subscription
    print("Checking ElevenLabs subscription...")
    sub = generator.check_subscription()
    if sub:
        print(f"  Characters used: {sub.get('character_count', 'N/A')}")
        print(f"  Character limit: {sub.get('character_limit', 'N/A')}")
    
    # List available voices
    print("\nAvailable voices:")
    voices = generator.get_available_voices()
    for voice in voices[:10]:  # Show first 10
        print(f"  - {voice['name']} ({voice['voice_id']})")
    
    # Test generation
    print("\nTesting audio generation...")
    test_path = config.TEMP_DIR / "test_narrator.mp3"
    success = generator.generate_audio(
        "Welcome back to Reddit Stories! Today we have an absolutely wild tale.",
        "narrator",
        test_path
    )
    
    if success:
        duration = generator._get_audio_duration(test_path)
        print(f"  Test audio generated: {test_path} ({duration:.1f}s)")
    
    # Test commentator voice
    test_path2 = config.TEMP_DIR / "test_commentator.mp3"
    success2 = generator.generate_audio(
        "Oh no she didn't! This is about to get spicy!",
        "commentator",
        test_path2
    )
    
    if success2:
        duration2 = generator._get_audio_duration(test_path2)
        print(f"  Test audio generated: {test_path2} ({duration2:.1f}s)")
