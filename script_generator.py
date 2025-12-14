"""
Script Generator
Uses Claude API to create narrated scripts with funny commentary
"""

import anthropic
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import config
from reddit_scraper import RedditStory


@dataclass
class ScriptSegment:
    """A single segment of the script"""
    type: str  # "intro", "story", "commentary", "outro"
    voice: str  # "narrator" or "commentator"
    text: str
    display_text: Optional[str] = None  # Text to show on screen (may differ from spoken)
    
    def __post_init__(self):
        if self.display_text is None:
            self.display_text = self.text


@dataclass
class GeneratedScript:
    """Complete script with all segments"""
    story_id: str
    title: str
    subreddit: str
    segments: list[ScriptSegment]
    video_title: str
    video_description: str
    tags: list[str]
    
    @property
    def total_words(self) -> int:
        return sum(len(seg.text.split()) for seg in self.segments)
    
    @property
    def estimated_duration(self) -> float:
        """Estimated video duration in minutes"""
        return self.total_words / 150  # ~150 words per minute for narration


class ScriptGenerator:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    
    def generate_script(self, story: RedditStory) -> GeneratedScript:
        """Generate a complete video script from a Reddit story"""
        
        # Generate the main script with commentary
        script_response = self._generate_narration_with_commentary(story)
        segments = self._parse_script_response(script_response)
        
        # Generate video metadata
        metadata = self._generate_video_metadata(story)
        
        return GeneratedScript(
            story_id=story.id,
            title=story.title,
            subreddit=story.subreddit,
            segments=segments,
            video_title=metadata['title'],
            video_description=metadata['description'],
            tags=metadata['tags']
        )
    
    def _generate_narration_with_commentary(self, story: RedditStory) -> str:
        """Use Claude to generate narration with commentary"""
        
        prompt = f"""You are creating a script for a Reddit story narration video with two voices:
1. NARRATOR: A calm, engaging storyteller who reads the Reddit post
2. COMMENTATOR: A funny, reactive personality who adds commentary between sections

The story is from r/{story.subreddit}:

TITLE: {story.title}

STORY:
{story.body}

---

Create a video script following these rules:

1. Start with a hook intro (NARRATOR) that teases the story without spoiling it
2. Break the story into logical paragraphs/sections
3. After every 2-3 story sections, add a COMMENTATOR reaction (1-2 sentences, funny/sarcastic/shocked)
4. The NARRATOR reads the story faithfully but can slightly paraphrase for flow
5. COMMENTATOR reactions should feel like a friend reacting in real-time
6. End with NARRATOR wrap-up and COMMENTATOR final take
7. Keep commentary family-friendly but edgy

Format your output EXACTLY like this (use these exact markers):

[INTRO|NARRATOR]
Your hook intro here...

[STORY|NARRATOR]
First story section here...

[STORY|NARRATOR]
Second story section here...

[COMMENTARY|COMMENTATOR]
Funny reaction here...

[STORY|NARRATOR]
More story...

[COMMENTARY|COMMENTATOR]
Another reaction...

[OUTRO|NARRATOR]
Wrap up...

[OUTRO|COMMENTATOR]
Final funny take...

Remember:
- NARRATOR sections should be the actual story content
- COMMENTARY should be SHORT (1-2 sentences max) and punchy
- Make it entertaining and engaging
- The video will have text overlays, so don't describe visuals"""

        message = self.client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text
    
    def _parse_script_response(self, response: str) -> list[ScriptSegment]:
        """Parse Claude's response into structured segments"""
        segments = []
        
        # Pattern to match [TYPE|VOICE] markers
        pattern = r'\[(\w+)\|(\w+)\]\s*\n(.*?)(?=\[\w+\|\w+\]|$)'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for seg_type, voice, text in matches:
            text = text.strip()
            if text:
                segments.append(ScriptSegment(
                    type=seg_type.lower(),
                    voice=voice.lower(),
                    text=text
                ))
        
        # Fallback if parsing fails
        if not segments:
            segments = [ScriptSegment(
                type="story",
                voice="narrator",
                text=response
            )]
        
        return segments
    
    def _generate_video_metadata(self, story: RedditStory) -> dict:
        """Generate YouTube title, description, and tags"""
        
        prompt = f"""Generate YouTube metadata for this Reddit story video.

Subreddit: r/{story.subreddit}
Original Title: {story.title}
Story preview: {story.body[:500]}...

Provide:
1. A clickbait-y but accurate YouTube title (max 70 chars)
2. A compelling description (include the subreddit, hint at the story, call to action)
3. 10 relevant tags

Format as JSON:
{{"title": "...", "description": "...", "tags": ["tag1", "tag2", ...]}}"""

        message = self.client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse JSON from response
        response_text = message.content[0].text
        
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            try:
                metadata = json.loads(json_match.group())
                # Add default tags
                metadata['tags'] = list(set(metadata.get('tags', []) + config.DEFAULT_TAGS))
                return metadata
            except json.JSONDecodeError:
                pass
        
        # Fallback metadata
        return {
            'title': f"Reddit Stories: {story.title[:50]}",
            'description': f"A story from r/{story.subreddit}\n\nOriginal post: {story.url}\n\n#reddit #redditstories",
            'tags': config.DEFAULT_TAGS
        }
    
    def save_script(self, script: GeneratedScript, output_path: Path):
        """Save generated script to JSON"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'story_id': script.story_id,
            'title': script.title,
            'subreddit': script.subreddit,
            'video_title': script.video_title,
            'video_description': script.video_description,
            'tags': script.tags,
            'total_words': script.total_words,
            'estimated_duration_minutes': script.estimated_duration,
            'segments': [asdict(seg) for seg in script.segments]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def load_script(script_path: Path) -> GeneratedScript:
        """Load a script from JSON"""
        with open(script_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        segments = [ScriptSegment(**seg) for seg in data['segments']]
        
        return GeneratedScript(
            story_id=data['story_id'],
            title=data['title'],
            subreddit=data['subreddit'],
            segments=segments,
            video_title=data['video_title'],
            video_description=data['video_description'],
            tags=data['tags']
        )


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    from reddit_scraper import RedditScraper
    
    # Get a story
    scraper = RedditScraper()
    story = scraper.get_best_story()
    
    if story:
        print(f"Generating script for: {story.title[:60]}...")
        print(f"Story length: {story.word_count} words")
        print("-" * 60)
        
        generator = ScriptGenerator()
        script = generator.generate_script(story)
        
        print(f"\nGenerated script with {len(script.segments)} segments")
        print(f"Estimated duration: {script.estimated_duration:.1f} minutes")
        print(f"\nVideo title: {script.video_title}")
        print(f"\nSegment breakdown:")
        
        for i, seg in enumerate(script.segments, 1):
            preview = seg.text[:80].replace('\n', ' ')
            print(f"  {i}. [{seg.type.upper()}|{seg.voice}] {preview}...")
        
        # Save script
        output_path = config.TEMP_DIR / f"script_{story.id}.json"
        generator.save_script(script, output_path)
        print(f"\nScript saved to: {output_path}")
    else:
        print("No stories found!")
