"""
YouTube Uploader
Handles video upload to YouTube via API
"""

import os
import pickle
import json
from pathlib import Path
from datetime import datetime, timedelta
import time
import random
import httplib2

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

import config
from script_generator import GeneratedScript


# YouTube API settings
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

# Retry settings
MAX_RETRIES = 3
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]


class YouTubeUploader:
    def __init__(self):
        self.credentials = None
        self.youtube = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with YouTube API"""
        creds = None
        token_path = Path("token.pickle")
        
        # Load existing credentials
        if token_path.exists():
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                client_secrets = config.YOUTUBE_CLIENT_SECRETS
                if not Path(client_secrets).exists():
                    raise FileNotFoundError(
                        f"YouTube client secrets not found at {client_secrets}\n"
                        "Download from Google Cloud Console and save as 'client_secrets.json'"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets, SCOPES
                )
                creds = flow.run_local_server(port=8080)
            
            # Save credentials
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.credentials = creds
        self.youtube = build(API_SERVICE_NAME, API_VERSION, credentials=creds)
        print("YouTube API authenticated successfully")
    
    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        category_id: str = config.YOUTUBE_CATEGORY_ID,
        privacy_status: str = "private",  # Start as private for safety
        thumbnail_path: Path = None,
        notify_subscribers: bool = False
    ) -> dict:
        """Upload a video to YouTube"""
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Prepare metadata
        body = {
            'snippet': {
                'title': title[:100],  # YouTube title limit
                'description': description[:5000],  # YouTube description limit
                'tags': tags[:500],  # YouTube tag limit
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False,
                'notifySubscribers': notify_subscribers
            }
        }
        
        print(f"Uploading video: {title}")
        print(f"  File: {video_path}")
        print(f"  Privacy: {privacy_status}")
        
        # Create upload request
        media = MediaFileUpload(
            str(video_path),
            chunksize=1024*1024,  # 1MB chunks
            resumable=True
        )
        
        request = self.youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        # Execute upload with retry logic
        response = self._resumable_upload(request)
        
        if response:
            video_id = response['id']
            print(f"  Upload successful! Video ID: {video_id}")
            print(f"  URL: https://www.youtube.com/watch?v={video_id}")
            
            # Upload thumbnail if provided
            if thumbnail_path and thumbnail_path.exists():
                self._upload_thumbnail(video_id, thumbnail_path)
            
            return response
        
        return None
    
    def _resumable_upload(self, request) -> dict:
        """Execute a resumable upload with retry logic"""
        response = None
        error = None
        retry = 0
        
        while response is None:
            try:
                status, response = request.next_chunk()
                
                if status:
                    progress = int(status.progress() * 100)
                    print(f"  Upload progress: {progress}%")
                    
            except HttpError as e:
                if e.resp.status in RETRIABLE_STATUS_CODES:
                    error = f"HTTP error {e.resp.status}: {e.content}"
                else:
                    raise
                    
            except Exception as e:
                error = str(e)
            
            if error:
                retry += 1
                if retry > MAX_RETRIES:
                    print(f"  Upload failed after {MAX_RETRIES} retries")
                    return None
                
                sleep_time = random.uniform(1, 5) * (2 ** retry)
                print(f"  Retry {retry}/{MAX_RETRIES} in {sleep_time:.1f}s - {error}")
                time.sleep(sleep_time)
                error = None
        
        return response
    
    def _upload_thumbnail(self, video_id: str, thumbnail_path: Path) -> bool:
        """Upload a custom thumbnail for a video"""
        try:
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path))
            ).execute()
            print(f"  Thumbnail uploaded successfully")
            return True
        except HttpError as e:
            print(f"  Thumbnail upload failed: {e}")
            return False
    
    def schedule_video(
        self,
        video_id: str,
        publish_time: datetime
    ) -> bool:
        """Schedule a video to be published at a specific time"""
        try:
            # Format time for YouTube API
            publish_at = publish_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            self.youtube.videos().update(
                part='status',
                body={
                    'id': video_id,
                    'status': {
                        'privacyStatus': 'private',
                        'publishAt': publish_at
                    }
                }
            ).execute()
            
            print(f"  Video scheduled for: {publish_time}")
            return True
            
        except HttpError as e:
            print(f"  Scheduling failed: {e}")
            return False
    
    def get_channel_info(self) -> dict:
        """Get information about the authenticated channel"""
        try:
            response = self.youtube.channels().list(
                part='snippet,statistics',
                mine=True
            ).execute()
            
            if response.get('items'):
                channel = response['items'][0]
                return {
                    'id': channel['id'],
                    'title': channel['snippet']['title'],
                    'subscribers': channel['statistics'].get('subscriberCount', 'hidden'),
                    'videos': channel['statistics']['videoCount'],
                    'views': channel['statistics']['viewCount']
                }
            return {}
            
        except HttpError as e:
            print(f"Error fetching channel info: {e}")
            return {}
    
    def get_upload_quota(self) -> dict:
        """Check remaining upload quota (approximate)"""
        # YouTube's quota system is complex, this is informational only
        return {
            'note': 'YouTube API has daily quotas. Default is 10,000 units/day.',
            'video_upload_cost': '1600 units per upload',
            'estimated_daily_uploads': '6 videos max with default quota'
        }


class UploadManager:
    """Manages upload scheduling and tracking"""
    
    def __init__(self):
        self.uploader = YouTubeUploader()
        self.upload_log_path = config.OUTPUT_DIR / "upload_log.json"
        self._load_log()
    
    def _load_log(self):
        """Load upload history"""
        if self.upload_log_path.exists():
            with open(self.upload_log_path, 'r') as f:
                self.upload_log = json.load(f)
        else:
            self.upload_log = {'uploads': []}
    
    def _save_log(self):
        """Save upload history"""
        self.upload_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.upload_log_path, 'w') as f:
            json.dump(self.upload_log, f, indent=2, default=str)
    
    def upload_from_script(
        self,
        video_path: Path,
        script: GeneratedScript,
        thumbnail_path: Path = None,
        privacy: str = "private"
    ) -> dict:
        """Upload a video using metadata from GeneratedScript"""
        
        # Build description
        description = f"{script.video_description}\n\n"
        description += f"📖 Original story from r/{script.subreddit}\n"
        description += f"Story ID: {script.story_id}\n\n"
        description += "🔔 Subscribe for daily Reddit stories!\n"
        description += "#reddit #redditstories #storytime"
        
        result = self.uploader.upload_video(
            video_path=video_path,
            title=script.video_title,
            description=description,
            tags=script.tags,
            privacy_status=privacy,
            thumbnail_path=thumbnail_path
        )
        
        if result:
            # Log the upload
            self.upload_log['uploads'].append({
                'timestamp': datetime.now().isoformat(),
                'video_id': result['id'],
                'story_id': script.story_id,
                'subreddit': script.subreddit,
                'title': script.video_title,
                'privacy': privacy
            })
            self._save_log()
        
        return result
    
    def get_next_scheduled_time(self) -> datetime:
        """Calculate next optimal upload time"""
        # Best times for YouTube engagement (in UTC)
        optimal_hours = [14, 17, 20]  # 2 PM, 5 PM, 8 PM
        
        now = datetime.utcnow()
        
        for hour in optimal_hours:
            candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if candidate > now:
                return candidate
        
        # All today's slots passed, schedule for tomorrow
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=optimal_hours[0], minute=0, second=0, microsecond=0)


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    print("YouTube Uploader Test")
    print("-" * 60)
    
    try:
        uploader = YouTubeUploader()
        
        # Get channel info
        print("\nChannel Info:")
        info = uploader.get_channel_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        # Quota info
        print("\nQuota Info:")
        quota = uploader.get_upload_quota()
        for key, value in quota.items():
            print(f"  {key}: {value}")
            
    except FileNotFoundError as e:
        print(f"\n{e}")
        print("\nTo set up YouTube API:")
        print("1. Go to Google Cloud Console")
        print("2. Create a project and enable YouTube Data API v3")
        print("3. Create OAuth 2.0 credentials (Desktop app)")
        print("4. Download and save as 'client_secrets.json'")
    except Exception as e:
        print(f"\nError: {e}")
