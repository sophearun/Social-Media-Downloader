"""
Core downloader module using yt-dlp for social media content downloading.
"""

import os
import sys
from typing import Optional, Dict, Any
import yt_dlp


class SocialMediaDownloader:
    """
    Main downloader class that handles downloading content from various social media platforms.
    """
    
    # Supported platforms
    SUPPORTED_PLATFORMS = [
        'youtube',
        'twitter',
        'instagram',
        'tiktok',
        'facebook',
        'reddit',
        'vimeo',
        'dailymotion',
        'twitch',
    ]
    
    def __init__(self, output_dir: str = "downloads"):
        """
        Initialize the downloader.
        
        Args:
            output_dir: Directory where downloaded files will be saved
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def download(
        self, 
        url: str, 
        format_type: str = "best",
        audio_only: bool = False,
        custom_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Download content from a given URL.
        
        Args:
            url: The URL of the content to download
            format_type: Format preference ('best', 'worst', or specific format)
            audio_only: If True, download only audio
            custom_filename: Custom filename for the downloaded file
            
        Returns:
            Dictionary containing download information
        """
        try:
            # Configure yt-dlp options
            ydl_opts = {
                'outtmpl': os.path.join(
                    self.output_dir, 
                    custom_filename if custom_filename else '%(title)s.%(ext)s'
                ),
                'quiet': False,
                'no_warnings': False,
            }
            
            # Set format options
            if audio_only:
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            else:
                if format_type == 'best':
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
                elif format_type == 'worst':
                    ydl_opts['format'] = 'worst'
                else:
                    ydl_opts['format'] = format_type
            
            # Download the content
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                return {
                    'success': True,
                    'title': info.get('title', 'Unknown'),
                    'url': url,
                    'format': info.get('format', 'Unknown'),
                    'filename': ydl.prepare_filename(info),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                }
                
        except yt_dlp.utils.DownloadError as e:
            return {
                'success': False,
                'error': f"Download error: {str(e)}",
                'url': url,
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'url': url,
            }
    
    def get_info(self, url: str) -> Dict[str, Any]:
        """
        Get information about a video without downloading it.
        
        Args:
            url: The URL of the content
            
        Returns:
            Dictionary containing video information
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'success': True,
                    'title': info.get('title', 'Unknown'),
                    'url': url,
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'upload_date': info.get('upload_date', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'formats': [
                        {
                            'format_id': f.get('format_id'),
                            'ext': f.get('ext'),
                            'quality': f.get('quality'),
                            'filesize': f.get('filesize'),
                        }
                        for f in info.get('formats', [])
                    ] if info.get('formats') else [],
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Error getting info: {str(e)}",
                'url': url,
            }
    
    def is_url_supported(self, url: str) -> bool:
        """
        Check if a URL is from a supported platform.
        
        Args:
            url: The URL to check
            
        Returns:
            True if supported, False otherwise
        """
        import re
        url_lower = url.lower()
        
        # More specific domain-based matching patterns
        platform_patterns = [
            r'youtube\.com|youtu\.be',
            r'twitter\.com|x\.com',
            r'instagram\.com',
            r'tiktok\.com',
            r'facebook\.com|fb\.watch',
            r'reddit\.com',
            r'vimeo\.com',
            r'dailymotion\.com',
            r'twitch\.tv',
        ]
        
        for pattern in platform_patterns:
            if re.search(pattern, url_lower):
                return True
        return False
