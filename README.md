# Social Media Downloader

A powerful and easy-to-use Python tool for downloading content from various social media platforms.

## Features

- 📥 Download videos, audio, and images from popular social media platforms
- 🎵 Extract audio from videos (MP3 format)
- 📊 Get video information without downloading
- 🎯 Support for multiple platforms:
  - YouTube
  - Twitter/X
  - Instagram
  - TikTok
  - Facebook
  - Reddit
  - Vimeo
  - Dailymotion
  - Twitch
- 🔧 Customizable output directory and filenames
- 📝 JSON output support for automation
- 🚀 Simple command-line interface

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Install from source

```bash
# Clone the repository
git clone https://github.com/sophearun/Social-Media-Downloader.git
cd Social-Media-Downloader

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Usage

### Basic Usage

Download a video:
```bash
sm-downloader https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### Audio Only

Download audio only (converts to MP3):
```bash
sm-downloader -a https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### Get Information

Get video information without downloading:
```bash
sm-downloader --info https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### Custom Output Directory

Specify a custom output directory:
```bash
sm-downloader -o /path/to/downloads https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### Custom Filename

Specify a custom filename:
```bash
sm-downloader --filename "my_video.mp4" https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### JSON Output

Get results in JSON format (useful for automation):
```bash
sm-downloader --json --info https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

## Command-Line Options

```
usage: sm-downloader [-h] [-o OUTPUT] [-a] [-f FORMAT] [--filename FILENAME]
                     [--info] [--json] [-v]
                     url

positional arguments:
  url                   URL of the content to download

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output directory for downloaded files (default: downloads)
  -a, --audio-only      Download audio only (converts to MP3)
  -f FORMAT, --format FORMAT
                        Format preference: best, worst, or specific format (default: best)
  --filename FILENAME   Custom filename for the downloaded file
  --info                Get video information without downloading
  --json                Output results in JSON format
  -v, --version         show program's version number and exit
```

## Examples

### Download a YouTube video
```bash
sm-downloader https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### Download audio from a music video
```bash
sm-downloader -a https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### Download Instagram video
```bash
sm-downloader https://www.instagram.com/p/ABC123/
```

### Download TikTok video
```bash
sm-downloader https://www.tiktok.com/@username/video/1234567890
```

### Get video information
```bash
sm-downloader --info https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

## Python API

You can also use the downloader programmatically in your Python code:

```python
from downloader.core import SocialMediaDownloader

# Initialize the downloader
downloader = SocialMediaDownloader(output_dir="my_downloads")

# Download a video
result = downloader.download(
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    format_type="best",
    audio_only=False
)

if result['success']:
    print(f"Downloaded: {result['title']}")
    print(f"Saved to: {result['filename']}")
else:
    print(f"Error: {result['error']}")

# Get video information
info = downloader.get_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(f"Title: {info['title']}")
print(f"Duration: {info['duration']} seconds")
print(f"Views: {info['view_count']:,}")
```

## Requirements

- Python 3.7+
- yt-dlp >= 2023.10.13
- requests >= 2.31.0

## Troubleshooting

### Download fails with "Video unavailable"
This usually means the video is private, age-restricted, or requires authentication. Some platforms may also block downloads.

### Audio extraction fails
Make sure you have `ffmpeg` installed on your system:
- Ubuntu/Debian: `sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### Slow downloads
This is usually due to network speed or server limitations. The tool downloads at the maximum speed allowed by the platform.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for personal use only. Please respect the copyright and terms of service of the platforms you download from. Do not use this tool to download copyrighted content without permission.

## Acknowledgments

- Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp), a powerful video downloader
- Inspired by the need for a simple, unified interface for downloading social media content
