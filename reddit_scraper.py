"""
Reddit Story Scraper
Fetches and filters stories from target subreddits
"""

import praw
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
import hashlib

import config


@dataclass
class RedditStory:
    """Structured Reddit story data"""
    id: str
    subreddit: str
    title: str
    author: str
    body: str
    url: str
    score: int
    num_comments: int
    created_utc: float
    flair: Optional[str]
    
    # Computed fields
    word_count: int = 0
    estimated_read_time: float = 0.0  # minutes
    content_hash: str = ""
    
    def __post_init__(self):
        self.word_count = len(self.body.split())
        self.estimated_read_time = self.word_count / 150  # avg reading speed
        self.content_hash = hashlib.md5(self.body.encode()).hexdigest()[:12]


class RedditScraper:
    def __init__(self):
        self.reddit = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            user_agent=config.REDDIT_USER_AGENT
        )
        self.archive_file = config.ARCHIVE_DIR / "used_stories.json"
        self._load_archive()
    
    def _load_archive(self):
        """Load previously used story IDs"""
        if self.archive_file.exists():
            with open(self.archive_file, 'r') as f:
                self.used_stories = set(json.load(f))
        else:
            self.used_stories = set()
    
    def _save_archive(self):
        """Save used story IDs"""
        config.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.archive_file, 'w') as f:
            json.dump(list(self.used_stories), f)
    
    def mark_as_used(self, story_id: str):
        """Mark a story as used to avoid repeats"""
        self.used_stories.add(story_id)
        self._save_archive()
    
    def clean_text(self, text: str) -> str:
        """Clean Reddit formatting from text"""
        # Remove markdown links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Remove Reddit-specific formatting
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&nbsp;', ' ', text)
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        # Remove edit notes at the end
        text = re.sub(r'\n*Edit:.*$', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'\n*Update:.*$', '', text, flags=re.IGNORECASE | re.DOTALL)
        return text.strip()
    
    def is_valid_story(self, submission) -> bool:
        """Check if a submission meets our criteria"""
        # Skip if already used
        if submission.id in self.used_stories:
            return False
        
        # Must be a text post
        if not submission.is_self:
            return False
        
        # Check length
        body_len = len(submission.selftext)
        if body_len < config.MIN_STORY_LENGTH or body_len > config.MAX_STORY_LENGTH:
            return False
        
        # Check engagement
        if submission.score < config.MIN_UPVOTES:
            return False
        if submission.num_comments < config.MIN_COMMENTS:
            return False
        
        # Check age
        post_time = datetime.utcfromtimestamp(submission.created_utc)
        if datetime.utcnow() - post_time > timedelta(days=config.STORY_AGE_DAYS):
            return False
        
        # Skip removed/deleted posts
        if submission.selftext in ['[removed]', '[deleted]', '']:
            return False
        
        # Skip NSFW if needed (optional filter)
        # if submission.over_18:
        #     return False
        
        return True
    
    def fetch_stories(self, limit_per_sub: int = 10) -> list[RedditStory]:
        """Fetch stories from all target subreddits"""
        all_stories = []
        
        for subreddit_name in config.TARGET_SUBREDDITS:
            print(f"Scanning r/{subreddit_name}...")
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Get hot and top posts
                for submission in subreddit.hot(limit=limit_per_sub):
                    if self.is_valid_story(submission):
                        story = self._submission_to_story(submission)
                        all_stories.append(story)
                
                # Also check top of the week
                for submission in subreddit.top(time_filter='week', limit=limit_per_sub):
                    if self.is_valid_story(submission):
                        story = self._submission_to_story(submission)
                        # Avoid duplicates
                        if story.id not in [s.id for s in all_stories]:
                            all_stories.append(story)
                            
            except Exception as e:
                print(f"Error fetching from r/{subreddit_name}: {e}")
                continue
        
        # Sort by engagement score
        all_stories.sort(key=lambda s: s.score + s.num_comments * 10, reverse=True)
        
        print(f"Found {len(all_stories)} valid stories")
        return all_stories
    
    def _submission_to_story(self, submission) -> RedditStory:
        """Convert PRAW submission to RedditStory dataclass"""
        return RedditStory(
            id=submission.id,
            subreddit=submission.subreddit.display_name,
            title=self.clean_text(submission.title),
            author=str(submission.author) if submission.author else "[deleted]",
            body=self.clean_text(submission.selftext),
            url=f"https://reddit.com{submission.permalink}",
            score=submission.score,
            num_comments=submission.num_comments,
            created_utc=submission.created_utc,
            flair=submission.link_flair_text
        )
    
    def get_best_story(self) -> Optional[RedditStory]:
        """Get the single best unused story"""
        stories = self.fetch_stories()
        if stories:
            return stories[0]
        return None
    
    def get_stories_batch(self, count: int = 5) -> list[RedditStory]:
        """Get multiple stories for batch processing"""
        stories = self.fetch_stories()
        return stories[:count]
    
    def save_story(self, story: RedditStory, output_path: Path):
        """Save story data to JSON for processing"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(story), f, indent=2, ensure_ascii=False)


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    scraper = RedditScraper()
    
    print("Fetching Reddit stories...")
    stories = scraper.fetch_stories(limit_per_sub=5)
    
    print(f"\nTop 5 stories found:")
    print("-" * 60)
    
    for i, story in enumerate(stories[:5], 1):
        print(f"\n{i}. [{story.subreddit}] {story.title[:60]}...")
        print(f"   Score: {story.score} | Comments: {story.num_comments}")
        print(f"   Words: {story.word_count} | Est. read time: {story.estimated_read_time:.1f} min")
        print(f"   URL: {story.url}")
    
    # Save the best story
    if stories:
        best = stories[0]
        output_path = config.TEMP_DIR / f"story_{best.id}.json"
        scraper.save_story(best, output_path)
        print(f"\nBest story saved to: {output_path}")
