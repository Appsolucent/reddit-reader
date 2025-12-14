"""
Background Footage Downloader
Helper script to download gameplay videos for backgrounds
"""

import subprocess
import sys
from pathlib import Path
import config


# Suggested videos for background footage
# These are examples - replace with actual URLs you have permission to use
SUGGESTED_SEARCHES = [
    "minecraft parkour no commentary gameplay 1 hour",
    "subway surfers gameplay no commentary",
    "temple run gameplay no commentary",
    "satisfying mobile game compilation",
    "geometry dash gameplay no commentary",
]


def check_ytdlp():
    """Check if yt-dlp is installed"""
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_ytdlp():
    """Install yt-dlp"""
    print("Installing yt-dlp...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'])


def download_video(url: str, output_dir: Path):
    """Download a single video"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_template = str(output_dir / "%(title)s.%(ext)s")
    
    cmd = [
        'yt-dlp',
        '-f', 'best[height<=1080][ext=mp4]',  # Best quality up to 1080p, prefer mp4
        '--no-playlist',  # Don't download playlists
        '-o', output_template,
        url
    ]
    
    print(f"Downloading: {url}")
    subprocess.run(cmd)


def search_and_download(query: str, output_dir: Path, max_results: int = 1):
    """Search YouTube and download top result"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_template = str(output_dir / "%(title)s.%(ext)s")
    
    cmd = [
        'yt-dlp',
        '-f', 'best[height<=1080][ext=mp4]',
        f'ytsearch{max_results}:{query}',
        '--no-playlist',
        '-o', output_template,
    ]
    
    print(f"Searching and downloading: {query}")
    subprocess.run(cmd)


def main():
    print("=" * 60)
    print("Background Footage Downloader")
    print("=" * 60)
    
    # Check/install yt-dlp
    if not check_ytdlp():
        print("yt-dlp not found. Installing...")
        install_ytdlp()
        if not check_ytdlp():
            print("Failed to install yt-dlp. Please install manually:")
            print("  pip install yt-dlp")
            return
    
    output_dir = config.BACKGROUND_VIDEOS_DIR
    print(f"\nOutput directory: {output_dir}")
    
    print("\nOptions:")
    print("1. Download from URL")
    print("2. Search and download")
    print("3. Show suggested searches")
    print("4. Exit")
    
    while True:
        choice = input("\nChoice (1-4): ").strip()
        
        if choice == '1':
            url = input("Enter YouTube URL: ").strip()
            if url:
                download_video(url, output_dir)
                print(f"\nDownload complete! Check {output_dir}")
        
        elif choice == '2':
            query = input("Enter search query: ").strip()
            if query:
                search_and_download(query, output_dir)
                print(f"\nDownload complete! Check {output_dir}")
        
        elif choice == '3':
            print("\nSuggested searches for background footage:")
            for i, search in enumerate(SUGGESTED_SEARCHES, 1):
                print(f"  {i}. {search}")
            print("\nCopy these into YouTube search to find suitable videos.")
            print("Make sure to only download videos you have rights to use!")
        
        elif choice == '4':
            break
        
        else:
            print("Invalid choice. Please enter 1-4.")
    
    # Show current background videos
    videos = list(output_dir.glob("*.mp4")) + list(output_dir.glob("*.mov"))
    if videos:
        print(f"\nCurrent background videos ({len(videos)}):")
        for v in videos:
            print(f"  - {v.name}")
    else:
        print("\nNo background videos found yet.")
        print("Add .mp4 files to:", output_dir)


if __name__ == "__main__":
    main()
