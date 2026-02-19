"""
Command-line interface for Social Media Downloader.
"""

import argparse
import sys
import json
from typing import Optional
from .core import SocialMediaDownloader


def print_info(info: dict):
    """Print video information in a readable format."""
    print("\n" + "="*60)
    if info.get('success'):
        print(f"Title: {info.get('title', 'N/A')}")
        print(f"Uploader: {info.get('uploader', 'N/A')}")
        print(f"Duration: {info.get('duration', 0)} seconds")
        print(f"Upload Date: {info.get('upload_date', 'N/A')}")
        print(f"Views: {info.get('view_count', 0):,}")
        print(f"Likes: {info.get('like_count', 0):,}")
        if info.get('description'):
            desc = info['description'][:200] + "..." if len(info['description']) > 200 else info['description']
            print(f"Description: {desc}")
    else:
        print(f"Error: {info.get('error', 'Unknown error')}")
    print("="*60 + "\n")


def print_download_result(result: dict):
    """Print download result in a readable format."""
    print("\n" + "="*60)
    if result.get('success'):
        print("✓ Download Successful!")
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"Filename: {result.get('filename', 'N/A')}")
        print(f"Format: {result.get('format', 'N/A')}")
        print(f"Uploader: {result.get('uploader', 'N/A')}")
    else:
        print("✗ Download Failed!")
        print(f"Error: {result.get('error', 'Unknown error')}")
        print(f"URL: {result.get('url', 'N/A')}")
    print("="*60 + "\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Social Media Downloader - Download content from various social media platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download a video
  sm-downloader https://www.youtube.com/watch?v=dQw4w9WgXcQ

  # Download audio only
  sm-downloader -a https://www.youtube.com/watch?v=dQw4w9WgXcQ

  # Get video information without downloading
  sm-downloader --info https://www.youtube.com/watch?v=dQw4w9WgXcQ

  # Specify output directory
  sm-downloader -o /path/to/downloads https://www.youtube.com/watch?v=dQw4w9WgXcQ

  # Specify custom filename
  sm-downloader --filename "my_video.mp4" https://www.youtube.com/watch?v=dQw4w9WgXcQ

Supported Platforms:
  - YouTube
  - Twitter/X
  - Instagram
  - TikTok
  - Facebook
  - Reddit
  - Vimeo
  - Dailymotion
  - Twitch
        """
    )
    
    parser.add_argument(
        'url',
        help='URL of the content to download'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='downloads',
        help='Output directory for downloaded files (default: downloads)'
    )
    
    parser.add_argument(
        '-a', '--audio-only',
        action='store_true',
        help='Download audio only (converts to MP3)'
    )
    
    parser.add_argument(
        '-f', '--format',
        default='best',
        help='Format preference: best, worst, or specific format (default: best)'
    )
    
    parser.add_argument(
        '--filename',
        help='Custom filename for the downloaded file'
    )
    
    parser.add_argument(
        '--info',
        action='store_true',
        help='Get video information without downloading'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='Social Media Downloader 1.0.0'
    )
    
    args = parser.parse_args()
    
    # Initialize downloader
    downloader = SocialMediaDownloader(output_dir=args.output)
    
    # Check if URL is supported
    if not downloader.is_url_supported(args.url):
        print(f"Warning: The URL does not appear to be from a recognized platform.")
        print("yt-dlp will attempt to download it anyway...\n")
    
    try:
        if args.info:
            # Get information only
            info = downloader.get_info(args.url)
            if args.json:
                print(json.dumps(info, indent=2))
            else:
                print_info(info)
            sys.exit(0 if info.get('success') else 1)
        else:
            # Download content
            print(f"Downloading from: {args.url}")
            print(f"Output directory: {args.output}")
            if args.audio_only:
                print("Mode: Audio only (MP3)")
            print()
            
            result = downloader.download(
                url=args.url,
                format_type=args.format,
                audio_only=args.audio_only,
                custom_filename=args.filename
            )
            
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print_download_result(result)
            
            sys.exit(0 if result.get('success') else 1)
            
    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
