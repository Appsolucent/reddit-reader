"""
Reddit Stories Pipeline - Main Orchestrator
Automated content pipeline from Reddit to YouTube
"""

import argparse
import json
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

import config
from reddit_scraper import RedditScraper, RedditStory
from script_generator import ScriptGenerator, GeneratedScript
from audio_generator import AudioGenerator, AudioSegment
from video_assembler import VideoAssembler
from youtube_uploader import UploadManager

# Optional character generation
try:
    from character_generator import CharacterGenerator, CharacterManager
    CHARACTER_AVAILABLE = True
except ImportError:
    CHARACTER_AVAILABLE = False
    print("Note: Character generation not available (missing replicate package)")


class RedditStoriesPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self, dry_run: bool = False, enable_character: bool = None, use_local: bool = False, use_animatediff: bool = None):
        self.dry_run = dry_run
        self.scraper = RedditScraper()
        self.script_gen = ScriptGenerator()
        self.audio_gen = AudioGenerator()
        self.video_assembler = VideoAssembler()
        
        # Character generation (optional)
        if enable_character is None:
            enable_character = config.ENABLE_CHARACTER_VIDEO
        
        self.enable_character = enable_character and CHARACTER_AVAILABLE
        
        # Local generation flags
        self.use_local = use_local
        
        # AnimateDiff for reactions (optional)
        if use_animatediff is None:
            use_animatediff = config.USE_LOCAL_ANIMATEDIFF
        self.use_animatediff = use_animatediff
        
        if self.enable_character:
            self.char_manager = CharacterManager(use_local=use_local, use_animatediff=use_animatediff)
            self.char_generator = CharacterGenerator(use_local=use_local, use_animatediff=use_animatediff)
            
            mode_parts = []
            if use_local:
                mode_parts.append("Local Flux")
            else:
                mode_parts.append("Replicate Flux")
            if use_animatediff:
                mode_parts.append("Local AnimateDiff")
            else:
                mode_parts.append("Replicate Hallo2")
            
            print(f"Character video generation: ENABLED ({' + '.join(mode_parts)})")
        else:
            self.char_manager = None
            self.char_generator = None
            if enable_character and not CHARACTER_AVAILABLE:
                print("Character video generation: DISABLED (install replicate package)")
            else:
                print("Character video generation: DISABLED")
        
        # Create necessary directories
        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        config.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        config.BACKGROUND_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        config.CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
    
    def run_full_pipeline(
        self,
        upload: bool = False,
        privacy: str = "private"
    ) -> dict:
        """Run the complete pipeline from Reddit scraping to YouTube upload"""
        
        print("=" * 60)
        print("REDDIT STORIES PIPELINE")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        results = {
            'success': False,
            'story_id': None,
            'video_path': None,
            'youtube_id': None,
            'errors': []
        }
        
        try:
            # Step 1: Fetch Reddit story
            print("\n[1/5] Fetching Reddit story...")
            story = self.scraper.get_best_story()
            
            if not story:
                results['errors'].append("No suitable stories found")
                return results
            
            print(f"  Selected: [{story.subreddit}] {story.title[:50]}...")
            print(f"  Score: {story.score} | Comments: {story.num_comments}")
            print(f"  Word count: {story.word_count}")
            results['story_id'] = story.id
            
            if self.dry_run:
                print("\n[DRY RUN] Stopping after story selection")
                results['success'] = True
                return results
            
            # Step 2: Generate script
            print("\n[2/5] Generating script with commentary...")
            script = self.script_gen.generate_script(story)
            
            print(f"  Segments: {len(script.segments)}")
            print(f"  Estimated duration: {script.estimated_duration:.1f} min")
            print(f"  Video title: {script.video_title}")
            
            # Save script for reference
            script_path = config.TEMP_DIR / f"script_{story.id}.json"
            self.script_gen.save_script(script, script_path)
            
            # Step 3: Generate audio
            print("\n[3/5] Generating audio...")
            audio_dir = config.TEMP_DIR / f"audio_{story.id}"
            audio_segments = self.audio_gen.generate_all_audio(script, audio_dir)
            
            if not audio_segments:
                results['errors'].append("Audio generation failed")
                return results
            
            total_audio_duration = sum(seg.duration for seg in audio_segments)
            print(f"  Total audio duration: {total_audio_duration:.1f}s")
            
            # Step 4: Generate character videos (if enabled)
            character_videos = None
            if self.enable_character:
                print("\n[4/6] Generating character videos...")
                
                # Ensure we have a character image
                char_image = self.char_manager.get_or_create_character(style="default")
                
                # Generate videos for commentary segments
                char_video_dir = config.TEMP_DIR / f"character_{story.id}"
                character_videos = self.char_generator.generate_all_commentary_videos(
                    audio_segments=audio_segments,
                    output_dir=char_video_dir
                )
                
                if character_videos:
                    print(f"  Generated {len(character_videos)} character videos")
                else:
                    print("  No character videos generated (continuing without)")
            else:
                print("\n[4/6] Skipping character generation (disabled)")
            
            # Step 5: Assemble video
            print("\n[5/6] Assembling video...")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            video_filename = f"reddit_story_{story.id}_{timestamp}.mp4"
            video_path = config.OUTPUT_DIR / video_filename
            
            success = self.video_assembler.assemble_video(
                script=script,
                audio_segments=audio_segments,
                output_path=video_path,
                character_videos=character_videos
            )
            
            if not success:
                results['errors'].append("Video assembly failed")
                return results
            
            results['video_path'] = str(video_path)
            
            # Create thumbnail
            thumbnail_path = config.OUTPUT_DIR / f"thumb_{story.id}.jpg"
            self.video_assembler.create_thumbnail(script, thumbnail_path)
            
            # Step 6: Upload to YouTube (optional)
            if upload:
                print("\n[6/6] Uploading to YouTube...")
                upload_manager = UploadManager()
                
                upload_result = upload_manager.upload_from_script(
                    video_path=video_path,
                    script=script,
                    thumbnail_path=thumbnail_path if thumbnail_path.exists() else None,
                    privacy=privacy
                )
                
                if upload_result:
                    results['youtube_id'] = upload_result['id']
                    print(f"  YouTube URL: https://youtube.com/watch?v={upload_result['id']}")
                else:
                    results['errors'].append("YouTube upload failed")
            else:
                print("\n[6/6] Skipping YouTube upload (use --upload to enable)")
            
            # Mark story as used
            self.scraper.mark_as_used(story.id)
            
            # Cleanup temp files
            print("\nCleaning up temporary files...")
            self._cleanup_temp(story.id)
            
            results['success'] = True
            
        except Exception as e:
            results['errors'].append(str(e))
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print(f"Success: {results['success']}")
        if results['video_path']:
            print(f"Video: {results['video_path']}")
        if results['youtube_id']:
            print(f"YouTube: https://youtube.com/watch?v={results['youtube_id']}")
        if results['errors']:
            print(f"Errors: {', '.join(results['errors'])}")
        print("=" * 60)
        
        return results
    
    def _cleanup_temp(self, story_id: str):
        """Clean up temporary files for a story"""
        patterns = [
            config.TEMP_DIR / f"story_{story_id}.json",
            config.TEMP_DIR / f"script_{story_id}.json",
            config.TEMP_DIR / f"audio_{story_id}",
            config.TEMP_DIR / f"character_{story_id}",  # Character videos
        ]
        
        for path in patterns:
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
    
    def batch_process(self, count: int = 5, upload: bool = False):
        """Process multiple stories in batch"""
        
        print(f"\nBatch processing {count} stories...")
        
        results = []
        stories = self.scraper.get_stories_batch(count)
        
        for i, story in enumerate(stories, 1):
            print(f"\n{'='*60}")
            print(f"Processing story {i}/{count}")
            print(f"{'='*60}")
            
            result = self.process_single_story(story, upload=upload)
            results.append(result)
            
            # Mark as used even if processing fails
            self.scraper.mark_as_used(story.id)
        
        # Summary
        successful = sum(1 for r in results if r['success'])
        print(f"\n\nBatch complete: {successful}/{count} successful")
        
        return results
    
    def process_single_story(
        self,
        story: RedditStory,
        upload: bool = False,
        privacy: str = "private"
    ) -> dict:
        """Process a specific story through the pipeline"""
        
        results = {
            'success': False,
            'story_id': story.id,
            'video_path': None,
            'youtube_id': None,
            'errors': []
        }
        
        try:
            # Generate script
            print(f"\nGenerating script for: {story.title[:50]}...")
            script = self.script_gen.generate_script(story)
            
            # Generate audio
            print("Generating audio...")
            audio_dir = config.TEMP_DIR / f"audio_{story.id}"
            audio_segments = self.audio_gen.generate_all_audio(script, audio_dir)
            
            if not audio_segments:
                results['errors'].append("Audio generation failed")
                return results
            
            # Generate character videos (if enabled)
            character_videos = None
            if self.enable_character:
                print("Generating character videos...")
                char_image = self.char_manager.get_or_create_character(style="default")
                char_video_dir = config.TEMP_DIR / f"character_{story.id}"
                character_videos = self.char_generator.generate_all_commentary_videos(
                    audio_segments=audio_segments,
                    output_dir=char_video_dir
                )
            
            # Assemble video
            print("Assembling video...")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            video_path = config.OUTPUT_DIR / f"reddit_story_{story.id}_{timestamp}.mp4"
            
            success = self.video_assembler.assemble_video(
                script=script,
                audio_segments=audio_segments,
                output_path=video_path,
                character_videos=character_videos
            )
            
            if success:
                results['video_path'] = str(video_path)
                results['success'] = True
            
            # Upload if requested
            if upload and success:
                upload_manager = UploadManager()
                upload_result = upload_manager.upload_from_script(
                    video_path=video_path,
                    script=script,
                    privacy=privacy
                )
                if upload_result:
                    results['youtube_id'] = upload_result['id']
            
            # Cleanup
            self._cleanup_temp(story.id)
            
        except Exception as e:
            results['errors'].append(str(e))
        
        return results
    
    def preview_stories(self, count: int = 5):
        """Preview available stories without processing"""
        
        print(f"\nPreviewing top {count} stories...")
        stories = self.scraper.get_stories_batch(count)
        
        print("\n" + "=" * 70)
        for i, story in enumerate(stories, 1):
            print(f"\n{i}. [{story.subreddit}] {story.title}")
            print(f"   Score: {story.score} | Comments: {story.num_comments} | Words: {story.word_count}")
            print(f"   Est. video length: {story.estimated_read_time:.1f} min")
            print(f"   URL: {story.url}")
        print("\n" + "=" * 70)
        
        return stories


def main():
    parser = argparse.ArgumentParser(
        description="Reddit Stories to YouTube Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline.py                    # Run full pipeline (no upload)
  python pipeline.py --upload           # Run pipeline and upload to YouTube
  python pipeline.py --preview          # Preview available stories
  python pipeline.py --batch 3          # Process 3 stories
  python pipeline.py --dry-run          # Test without processing
  python pipeline.py --no-character     # Disable AI character
  python pipeline.py --create-character # Create new character image
  python pipeline.py --character-style anime  # Use anime style character
        """
    )
    
    parser.add_argument(
        '--upload', action='store_true',
        help='Upload to YouTube after processing'
    )
    parser.add_argument(
        '--privacy', choices=['private', 'unlisted', 'public'],
        default='private',
        help='YouTube video privacy setting (default: private)'
    )
    parser.add_argument(
        '--preview', action='store_true',
        help='Preview available stories without processing'
    )
    parser.add_argument(
        '--batch', type=int, metavar='N',
        help='Process N stories in batch'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Test run without processing'
    )
    
    # Character options
    char_group = parser.add_argument_group('Character Options')
    char_group.add_argument(
        '--no-character', action='store_true',
        help='Disable AI character video generation'
    )
    char_group.add_argument(
        '--create-character', action='store_true',
        help='Create a new character image before processing'
    )
    char_group.add_argument(
        '--character-style', type=str, default='default',
        choices=['default', 'anime', 'realistic', 'cartoon', 'meme', 'gamer'],
        help='Character style to use (default: default)'
    )
    char_group.add_argument(
        '--custom-character-prompt', type=str,
        help='Custom prompt for character generation'
    )
    char_group.add_argument(
        '--animatediff', action='store_true',
        help='Use local AnimateDiff for character reactions (instead of Replicate)'
    )
    char_group.add_argument(
        '--local', action='store_true',
        help='Use local ComfyUI for all generation (Flux + AnimateDiff)'
    )
    
    args = parser.parse_args()
    
    # Handle character creation first if requested
    if args.create_character:
        if not CHARACTER_AVAILABLE:
            print("Error: replicate package not installed")
            print("Run: pip install replicate")
            return
        
        manager = CharacterManager()
        
        if args.custom_character_prompt:
            char_path = manager.create_custom_character(
                prompt=args.custom_character_prompt,
                name="custom"
            )
        else:
            char_path = manager.get_or_create_character(style=args.character_style)
        
        print(f"\nCharacter created: {char_path}")
        
        if not args.preview and not args.batch and args.dry_run:
            return  # Exit if only creating character
    
    enable_character = not args.no_character
    use_local = args.local
    use_animatediff = args.animatediff or args.local
    
    pipeline = RedditStoriesPipeline(
        dry_run=args.dry_run, 
        enable_character=enable_character,
        use_local=use_local,
        use_animatediff=use_animatediff
    )
    
    # Set character style if using characters
    if enable_character and CHARACTER_AVAILABLE and pipeline.char_manager:
        pipeline.char_manager.get_or_create_character(style=args.character_style)
    
    if args.preview:
        pipeline.preview_stories(count=10)
    elif args.batch:
        pipeline.batch_process(count=args.batch, upload=args.upload)
    else:
        pipeline.run_full_pipeline(upload=args.upload, privacy=args.privacy)


if __name__ == "__main__":
    main()
