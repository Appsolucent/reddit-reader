"""
YouTube Description Generator
Creates properly attributed video descriptions with Reddit links
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

import config


@dataclass
class VideoMetadata:
    """Complete metadata for YouTube upload"""
    title: str
    description: str
    tags: list[str]
    category_id: str  # YouTube category ID
    
    # Attribution info
    reddit_url: str
    subreddit: str
    original_author: str
    original_title: str


class DescriptionGenerator:
    """Generates YouTube descriptions with proper Reddit attribution"""
    
    def __init__(self):
        self.channel_name = config.CHANNEL_NAME if hasattr(config, 'CHANNEL_NAME') else "Reddit Stories"
    
    def generate_description(
        self,
        reddit_url: str,
        subreddit: str,
        original_title: str,
        original_author: str,
        story_summary: str = "",
        custom_footer: str = ""
    ) -> str:
        """
        Generate a YouTube description with full Reddit attribution.
        
        The description prominently features:
        - Direct link to original Reddit post
        - Subreddit attribution
        - Call-to-action to visit Reddit
        """
        
        # Build the description
        lines = []
        
        # Opening hook (optional summary)
        if story_summary:
            lines.append(story_summary)
            lines.append("")
        
        # PROMINENT ATTRIBUTION SECTION
        lines.append("=" * 50)
        lines.append("📖 ORIGINAL REDDIT POST")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"🔗 Read the original story: {reddit_url}")
        lines.append(f"📍 Subreddit: r/{subreddit}")
        lines.append(f"✍️ Original Author: u/{original_author}")
        lines.append(f"📝 Original Title: {original_title}")
        lines.append("")
        lines.append("👆 Please visit the original post to upvote and support the author!")
        lines.append("")
        
        # Call to action for Reddit
        lines.append("=" * 50)
        lines.append("🚀 DISCOVER MORE ON REDDIT")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"Join r/{subreddit} for more amazing stories:")
        lines.append(f"https://reddit.com/r/{subreddit}")
        lines.append("")
        lines.append("New to Reddit? Create a free account:")
        lines.append("https://reddit.com/register")
        lines.append("")
        
        # Timestamps section (placeholder for chapters)
        lines.append("=" * 50)
        lines.append("⏱️ TIMESTAMPS")
        lines.append("=" * 50)
        lines.append("")
        lines.append("0:00 - Introduction")
        lines.append("0:15 - Story Begins")
        lines.append("(More timestamps coming soon)")
        lines.append("")
        
        # Channel info / footer
        lines.append("=" * 50)
        lines.append("📺 ABOUT THIS CHANNEL")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"We share the best stories from Reddit with full attribution.")
        lines.append("All videos include links to original posts - please support the authors!")
        lines.append("")
        
        if custom_footer:
            lines.append(custom_footer)
            lines.append("")
        
        # Hashtags
        lines.append(f"#Reddit #r{subreddit} #RedditStories #Stories #AITA #TIFU")
        
        return "\n".join(lines)
    
    def generate_title(
        self,
        original_title: str,
        subreddit: str,
        style: str = "dramatic"
    ) -> str:
        """
        Generate a YouTube-optimized title.
        Includes subreddit for attribution.
        """
        
        # Clean up the original title
        title = original_title.strip()
        
        # Remove common Reddit prefixes
        prefixes_to_remove = [
            "AITA for ", "AITA ", "WIBTA for ", "WIBTA ",
            "TIFU by ", "TIFU ",
            "UPDATE: ", "Update: ", "[UPDATE] ",
        ]
        
        clean_title = title
        for prefix in prefixes_to_remove:
            if clean_title.startswith(prefix):
                clean_title = clean_title[len(prefix):]
                break
        
        # Capitalize first letter
        if clean_title:
            clean_title = clean_title[0].upper() + clean_title[1:]
        
        # Add subreddit tag
        if style == "dramatic":
            return f"r/{subreddit} | {clean_title}"
        elif style == "question":
            return f"r/{subreddit}: {clean_title}?"
        else:
            return f"[r/{subreddit}] {clean_title}"
    
    def generate_tags(self, subreddit: str, story_text: str = "") -> list[str]:
        """Generate relevant tags for the video"""
        
        base_tags = [
            "reddit",
            "reddit stories",
            f"r/{subreddit}",
            f"r {subreddit}",
            subreddit,
            "reddit story",
            "best reddit stories",
            "top reddit posts",
        ]
        
        # Subreddit-specific tags
        subreddit_tags = {
            "tifu": ["tifu", "today i f'd up", "tifu reddit", "funny reddit stories"],
            "AmItheAsshole": ["aita", "am i the asshole", "aita reddit", "relationship advice"],
            "MaliciousCompliance": ["malicious compliance", "revenge stories", "workplace stories"],
            "ProRevenge": ["pro revenge", "revenge", "justice served", "petty revenge"],
            "pettyrevenge": ["petty revenge", "revenge stories", "satisfying revenge"],
            "relationship_advice": ["relationship advice", "dating advice", "relationship stories"],
            "entitledparents": ["entitled parents", "karen stories", "entitled people"],
            "confessions": ["confessions", "true confessions", "reddit confessions"],
        }
        
        if subreddit.lower() in subreddit_tags:
            base_tags.extend(subreddit_tags[subreddit.lower()])
        
        # Generic story tags
        base_tags.extend([
            "storytime",
            "story time",
            "true stories",
            "real stories",
        ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in base_tags:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                unique_tags.append(tag)
        
        return unique_tags[:30]  # YouTube limit is 500 chars, ~30 tags is safe
    
    def generate_full_metadata(
        self,
        reddit_url: str,
        subreddit: str,
        original_title: str,
        original_author: str,
        story_summary: str = "",
        title_style: str = "dramatic"
    ) -> VideoMetadata:
        """Generate complete video metadata"""
        
        return VideoMetadata(
            title=self.generate_title(original_title, subreddit, title_style),
            description=self.generate_description(
                reddit_url=reddit_url,
                subreddit=subreddit,
                original_title=original_title,
                original_author=original_author,
                story_summary=story_summary
            ),
            tags=self.generate_tags(subreddit),
            category_id="24",  # Entertainment
            reddit_url=reddit_url,
            subreddit=subreddit,
            original_author=original_author,
            original_title=original_title
        )
    
    def save_metadata(self, metadata: VideoMetadata, output_path: Path):
        """Save metadata to JSON file for upload"""
        data = {
            "title": metadata.title,
            "description": metadata.description,
            "tags": metadata.tags,
            "category_id": metadata.category_id,
            "attribution": {
                "reddit_url": metadata.reddit_url,
                "subreddit": metadata.subreddit,
                "original_author": metadata.original_author,
                "original_title": metadata.original_title
            },
            "generated_at": datetime.now().isoformat()
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved metadata: {output_path}")
        return output_path


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube Description Generator")
    parser.add_argument('--url', type=str, required=True,
                       help='Reddit post URL')
    parser.add_argument('--subreddit', type=str, required=True,
                       help='Subreddit name')
    parser.add_argument('--title', type=str, required=True,
                       help='Original post title')
    parser.add_argument('--author', type=str, default='[deleted]',
                       help='Original author username')
    parser.add_argument('--output', type=str,
                       help='Output file path for metadata JSON')
    
    args = parser.parse_args()
    
    generator = DescriptionGenerator()
    
    metadata = generator.generate_full_metadata(
        reddit_url=args.url,
        subreddit=args.subreddit,
        original_title=args.title,
        original_author=args.author
    )
    
    print("\n" + "=" * 60)
    print("GENERATED TITLE")
    print("=" * 60)
    print(metadata.title)
    
    print("\n" + "=" * 60)
    print("GENERATED DESCRIPTION")
    print("=" * 60)
    print(metadata.description)
    
    print("\n" + "=" * 60)
    print("GENERATED TAGS")
    print("=" * 60)
    print(", ".join(metadata.tags))
    
    if args.output:
        generator.save_metadata(metadata, Path(args.output))
