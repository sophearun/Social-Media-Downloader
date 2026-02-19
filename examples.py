#!/usr/bin/env python3
"""
Example script demonstrating the Social Media Downloader API.
"""

from downloader.core import SocialMediaDownloader


def main():
    """Run example downloads."""
    # Initialize the downloader
    print("Initializing Social Media Downloader...")
    downloader = SocialMediaDownloader(output_dir="downloads")
    
    # Example URLs (replace with actual URLs you want to test)
    example_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # YouTube
        # Add more URLs here as needed
    ]
    
    # Example 1: Get video information
    print("\n" + "="*60)
    print("Example 1: Getting video information")
    print("="*60)
    
    url = example_urls[0]
    print(f"\nGetting info for: {url}")
    info = downloader.get_info(url)
    
    if info['success']:
        print(f"\nTitle: {info['title']}")
        print(f"Uploader: {info['uploader']}")
        print(f"Duration: {info['duration']} seconds")
        print(f"Views: {info['view_count']:,}")
        print(f"Likes: {info['like_count']:,}")
    else:
        print(f"Error: {info['error']}")
    
    # Example 2: Download a video
    print("\n" + "="*60)
    print("Example 2: Downloading a video")
    print("="*60)
    
    print(f"\nDownloading: {url}")
    result = downloader.download(
        url=url,
        format_type="best",
        audio_only=False
    )
    
    if result['success']:
        print(f"\n✓ Download successful!")
        print(f"Title: {result['title']}")
        print(f"Saved to: {result['filename']}")
    else:
        print(f"\n✗ Download failed!")
        print(f"Error: {result['error']}")
    
    # Example 3: Download audio only
    print("\n" + "="*60)
    print("Example 3: Downloading audio only")
    print("="*60)
    
    print(f"\nDownloading audio from: {url}")
    result = downloader.download(
        url=url,
        audio_only=True
    )
    
    if result['success']:
        print(f"\n✓ Audio download successful!")
        print(f"Title: {result['title']}")
        print(f"Saved to: {result['filename']}")
    else:
        print(f"\n✗ Audio download failed!")
        print(f"Error: {result['error']}")
    
    # Example 4: Check if URL is supported
    print("\n" + "="*60)
    print("Example 4: Checking platform support")
    print("="*60)
    
    test_urls = [
        "https://www.youtube.com/watch?v=test",
        "https://twitter.com/user/status/123",
        "https://www.instagram.com/p/ABC123/",
        "https://www.example.com/video",
    ]
    
    for test_url in test_urls:
        is_supported = downloader.is_url_supported(test_url)
        status = "✓ Supported" if is_supported else "✗ Not supported"
        print(f"{status}: {test_url}")
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
