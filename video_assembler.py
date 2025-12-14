"""
Video Assembler
Combines audio, background footage, and text overlays into final video
"""

import random
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    CompositeAudioClip, concatenate_audioclips, ColorClip, ImageClip
)
from moviepy.video.tools.subtitles import SubtitlesClip
import textwrap
import json

import config
from script_generator import GeneratedScript, ScriptSegment
from audio_generator import AudioSegment

# Optional import for character videos
try:
    from character_generator import CharacterVideo
except ImportError:
    CharacterVideo = None


@dataclass
class VideoConfig:
    """Video assembly configuration"""
    width: int = config.VIDEO_WIDTH
    height: int = config.VIDEO_HEIGHT
    fps: int = config.VIDEO_FPS
    font: str = config.FONT_PATH
    title_font_size: int = config.FONT_SIZE_TITLE
    story_font_size: int = config.FONT_SIZE_STORY
    commentary_font_size: int = config.FONT_SIZE_COMMENTARY


class VideoAssembler:
    def __init__(self, video_config: VideoConfig = None):
        self.config = video_config or VideoConfig()
        self.background_videos = self._load_background_videos()
    
    def _load_background_videos(self) -> list[Path]:
        """Load available background gameplay videos"""
        bg_dir = config.BACKGROUND_VIDEOS_DIR
        
        if not bg_dir.exists():
            bg_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created background videos directory: {bg_dir}")
            print("Please add Minecraft parkour or Subway Surfers videos to this folder!")
            return []
        
        videos = list(bg_dir.glob("*.mp4")) + list(bg_dir.glob("*.mov"))
        print(f"Found {len(videos)} background videos")
        return videos
    
    def _get_background_clip(self, duration: float) -> VideoFileClip:
        """Get a background video clip of the required duration"""
        
        if not self.background_videos:
            # Fallback: create a solid color background
            print("Warning: No background videos found. Using solid color.")
            return ColorClip(
                size=(self.config.width, self.config.height),
                color=(30, 30, 40),  # Dark blue-gray
                duration=duration
            )
        
        # Pick a random background video
        bg_path = random.choice(self.background_videos)
        clip = VideoFileClip(str(bg_path))
        
        # Resize to fit our dimensions (crop to fill)
        clip = self._resize_and_crop(clip)
        
        # Loop if needed
        if clip.duration < duration:
            loops_needed = int(duration / clip.duration) + 1
            clip = clip.loop(n=loops_needed)
        
        # Trim to exact duration
        clip = clip.subclip(0, duration)
        
        return clip
    
    def _resize_and_crop(self, clip: VideoFileClip) -> VideoFileClip:
        """Resize and crop clip to target dimensions"""
        target_ratio = self.config.width / self.config.height
        clip_ratio = clip.w / clip.h
        
        if clip_ratio > target_ratio:
            # Clip is wider - resize by height, crop width
            new_height = self.config.height
            new_width = int(clip_ratio * new_height)
            clip = clip.resize(height=new_height)
            x_center = new_width / 2
            x1 = x_center - self.config.width / 2
            clip = clip.crop(x1=x1, x2=x1 + self.config.width)
        else:
            # Clip is taller - resize by width, crop height
            new_width = self.config.width
            new_height = int(new_width / clip_ratio)
            clip = clip.resize(width=new_width)
            y_center = new_height / 2
            y1 = y_center - self.config.height / 2
            clip = clip.crop(y1=y1, y2=y1 + self.config.height)
        
        return clip
    
    def _create_text_clip(
        self,
        text: str,
        duration: float,
        segment_type: str,
        voice: str
    ) -> TextClip:
        """Create a text overlay clip"""
        
        # Determine styling based on segment type
        if segment_type == "intro" or segment_type == "outro":
            font_size = self.config.title_font_size
            color = "white"
            position = ("center", "center")
            max_width = 30  # characters per line
        elif voice == "commentator":
            font_size = self.config.commentary_font_size
            color = "#FFD700"  # Gold for commentary
            position = ("center", self.config.height * 0.75)  # Lower third
            max_width = 35
        else:  # story narrator
            font_size = self.config.story_font_size
            color = "white"
            position = ("center", "center")
            max_width = 35
        
        # Wrap text for display
        wrapped_text = textwrap.fill(text, width=max_width)
        
        # Truncate if too long (for display)
        lines = wrapped_text.split('\n')
        if len(lines) > 8:
            lines = lines[:8]
            lines[-1] += "..."
            wrapped_text = '\n'.join(lines)
        
        try:
            txt_clip = TextClip(
                wrapped_text,
                fontsize=font_size,
                color=color,
                font=self.config.font,
                stroke_color=config.TEXT_STROKE_COLOR,
                stroke_width=config.TEXT_STROKE_WIDTH,
                method='caption',
                size=(self.config.width - 80, None),  # Padding
                align='center'
            )
            txt_clip = txt_clip.set_duration(duration)
            txt_clip = txt_clip.set_position(position)
            
            return txt_clip
            
        except Exception as e:
            print(f"Error creating text clip: {e}")
            # Fallback without fancy styling
            txt_clip = TextClip(
                wrapped_text,
                fontsize=font_size,
                color=color,
                method='label'
            )
            txt_clip = txt_clip.set_duration(duration)
            txt_clip = txt_clip.set_position("center")
            return txt_clip
    
    def _create_subreddit_badge(self, subreddit: str, duration: float) -> TextClip:
        """Create a subreddit badge overlay"""
        badge_text = f"r/{subreddit}"
        
        try:
            badge = TextClip(
                badge_text,
                fontsize=28,
                color="white",
                font=self.config.font,
                bg_color='#FF4500',  # Reddit orange
                method='label'
            )
            badge = badge.set_duration(duration)
            badge = badge.set_position((20, 20))  # Top left
            badge = badge.margin(left=10, right=10, top=5, bottom=5, color=(255, 69, 0))
            return badge
        except Exception:
            return None
    
    def _get_character_position(self, char_clip_size: tuple) -> tuple:
        """Calculate character position based on config setting"""
        char_w, char_h = char_clip_size
        margin = 20  # Pixels from edge
        
        positions = {
            "bottom_right": (self.config.width - char_w - margin, 
                           self.config.height - char_h - margin),
            "bottom_left": (margin, 
                          self.config.height - char_h - margin),
            "top_right": (self.config.width - char_w - margin, 
                         margin + 60),  # Below subreddit badge
            "top_left": (margin + 200,  # Right of subreddit badge
                        margin),
            "center_bottom": ((self.config.width - char_w) // 2,
                            self.config.height - char_h - margin)
        }
        
        return positions.get(config.CHARACTER_POSITION, positions["bottom_right"])
    
    def _create_character_clip(
        self,
        character_video_path: Path,
        duration: float,
        start_time: float
    ) -> Optional[VideoFileClip]:
        """Create a positioned character video clip"""
        
        try:
            # Load character video
            char_clip = VideoFileClip(str(character_video_path))
            
            # Calculate target size (fraction of video width)
            target_width = int(self.config.width * config.CHARACTER_SIZE)
            scale_factor = target_width / char_clip.w
            target_height = int(char_clip.h * scale_factor)
            
            # Resize character video
            char_clip = char_clip.resize((target_width, target_height))
            
            # Set timing
            char_clip = char_clip.set_start(start_time)
            char_clip = char_clip.set_duration(min(char_clip.duration, duration))
            
            # Get position
            position = self._get_character_position((target_width, target_height))
            char_clip = char_clip.set_position(position)
            
            # Remove audio (we use the original audio track)
            char_clip = char_clip.without_audio()
            
            return char_clip
            
        except Exception as e:
            print(f"Error creating character clip: {e}")
            return None
    
    def assemble_video(
        self,
        script: GeneratedScript,
        audio_segments: list[AudioSegment],
        output_path: Path,
        character_videos: list = None
    ) -> bool:
        """Assemble the final video with optional character overlays"""
        
        print("Assembling video...")
        
        # Calculate total duration from audio
        total_duration = sum(seg.duration for seg in audio_segments)
        
        # Add small gaps between segments
        gap_duration = 0.3  # seconds
        total_duration += gap_duration * (len(audio_segments) - 1)
        
        print(f"  Total duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
        
        # Get background footage
        print("  Loading background footage...")
        background = self._get_background_clip(total_duration)
        
        # Build index of character videos by segment index
        char_video_map = {}
        if character_videos:
            for cv in character_videos:
                char_video_map[cv.segment_index] = cv
            print(f"  Character videos available: {len(character_videos)}")
        
        # Create audio and text clips
        print("  Creating audio and text overlays...")
        audio_clips = []
        text_clips = []
        character_clips = []
        current_time = 0
        
        for i, audio_seg in enumerate(audio_segments):
            script_seg = script.segments[audio_seg.segment_index]
            
            # Load audio
            audio_clip = AudioFileClip(str(audio_seg.audio_path))
            audio_clip = audio_clip.set_start(current_time)
            audio_clips.append(audio_clip)
            
            # Create text overlay
            text_clip = self._create_text_clip(
                script_seg.display_text or script_seg.text,
                audio_seg.duration,
                script_seg.type,
                script_seg.voice
            )
            text_clip = text_clip.set_start(current_time)
            text_clips.append(text_clip)
            
            # Add character video if available for this segment
            if audio_seg.segment_index in char_video_map:
                char_vid = char_video_map[audio_seg.segment_index]
                char_clip = self._create_character_clip(
                    char_vid.video_path,
                    audio_seg.duration,
                    current_time
                )
                if char_clip:
                    character_clips.append(char_clip)
            
            current_time += audio_seg.duration + gap_duration
        
        # Create subreddit badge (persistent throughout video)
        badge = self._create_subreddit_badge(script.subreddit, total_duration)
        if badge:
            text_clips.insert(0, badge)
        
        # Composite everything
        print("  Compositing video...")
        
        # Combine audio
        final_audio = CompositeAudioClip(audio_clips)
        
        # Layer order: background -> character -> text overlays
        all_clips = [background] + character_clips + text_clips
        
        if character_clips:
            print(f"  Adding {len(character_clips)} character video overlays...")
        
        # Combine video with text overlays
        final_video = CompositeVideoClip(
            all_clips,
            size=(self.config.width, self.config.height)
        )
        final_video = final_video.set_audio(final_audio)
        final_video = final_video.set_duration(total_duration)
        
        # Export
        print(f"  Exporting to {output_path}...")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        final_video.write_videofile(
            str(output_path),
            fps=self.config.fps,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile=str(config.TEMP_DIR / 'temp_audio.m4a'),
            remove_temp=True,
            threads=4,
            preset='medium',
            verbose=False,
            logger=None
        )
        
        # Cleanup
        print("  Cleaning up...")
        final_video.close()
        background.close()
        for clip in audio_clips:
            clip.close()
        for clip in character_clips:
            try:
                clip.close()
            except:
                pass
        
        print(f"Video saved to: {output_path}")
        return True
    
    def create_thumbnail(
        self,
        script: GeneratedScript,
        output_path: Path
    ) -> bool:
        """Create a thumbnail image for the video"""
        
        # Use first frame of background with title overlay
        if self.background_videos:
            bg_path = random.choice(self.background_videos)
            bg_clip = VideoFileClip(str(bg_path))
            bg_clip = self._resize_and_crop(bg_clip)
            bg_frame = bg_clip.get_frame(1)  # Frame at 1 second
            bg_clip.close()
        else:
            # Solid color fallback
            import numpy as np
            bg_frame = np.full(
                (self.config.height, self.config.width, 3),
                (30, 30, 40),
                dtype=np.uint8
            )
        
        # Create thumbnail with title
        bg_image = ImageClip(bg_frame)
        
        # Title text
        title_text = script.title[:50] + "..." if len(script.title) > 50 else script.title
        wrapped_title = textwrap.fill(title_text, width=20)
        
        try:
            title_clip = TextClip(
                wrapped_title,
                fontsize=60,
                color="white",
                font=self.config.font,
                stroke_color="black",
                stroke_width=3,
                method='caption',
                size=(self.config.width - 100, None),
                align='center'
            )
            title_clip = title_clip.set_position("center")
            
            # Subreddit badge
            badge = TextClip(
                f"r/{script.subreddit}",
                fontsize=40,
                color="white",
                bg_color='#FF4500',
                method='label'
            )
            badge = badge.set_position((50, 50))
            
            # Composite
            thumbnail = CompositeVideoClip(
                [bg_image, title_clip, badge],
                size=(self.config.width, self.config.height)
            )
            
            # Save
            output_path.parent.mkdir(parents=True, exist_ok=True)
            thumbnail.save_frame(str(output_path), t=0)
            
            thumbnail.close()
            bg_image.close()
            
            print(f"Thumbnail saved to: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            return False


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    print("Video Assembler Test")
    print("-" * 60)
    
    assembler = VideoAssembler()
    
    print(f"\nBackground videos directory: {config.BACKGROUND_VIDEOS_DIR}")
    print(f"Videos found: {len(assembler.background_videos)}")
    
    if assembler.background_videos:
        print("\nAvailable background videos:")
        for vid in assembler.background_videos:
            print(f"  - {vid.name}")
    else:
        print("\nNo background videos found!")
        print("Please add Minecraft parkour or Subway Surfers gameplay videos to:")
        print(f"  {config.BACKGROUND_VIDEOS_DIR.absolute()}")
        print("\nYou can find these on YouTube and download with yt-dlp")
