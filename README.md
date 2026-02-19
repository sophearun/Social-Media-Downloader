<<<<<<< HEAD
# Social-Media-Downloader
Social Media Downloader
=======
# TikTok Video Downloader

កម្មវិធីទាញយកវីដេអូ TikTok ដោយឥតគិតថ្លៃ

## Features / មុខងារ

- ទាញយកវីដេអូ TikTok គុណភាពខ្ពស់ (MP4)
- ទាញយកសម្លេង MP3
- ចំណុចប្រទាក់ស្អាត ងាយស្រួលប្រើ
- បង្ហាញព័ត៌មានវីដេអូមុនពេលទាញយក
- បង្ហាញការរីកចម្រើនការទាញយក

## Requirements / តម្រូវការ

- Python 3.8+
- FFmpeg (ចាំបាច់សម្រាប់ការទាញយកសម្លេង MP3)

## Installation / ការដំឡើង

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install FFmpeg (optional - for MP3 download)
# Download from: https://ffmpeg.org/download.html
# Or use: winget install ffmpeg

# 3. Run the application
python app.py
```

## Usage / ការប្រើប្រាស់

1. Run `python app.py`
2. Open browser: http://localhost:5000
3. Paste TikTok video URL
4. Click "ស្វែងរកវីដេអូ" (Search Video)
5. Choose to download video (MP4) or audio (MP3)
6. Wait for download to complete
7. Click "រក្សាទុកឯកសារ" (Save File) to save

## Supported URLs / URL ដែលទាកើត

- `https://www.tiktok.com/@user/video/1234567890`
- `https://vm.tiktok.com/XXXXXXXX`
- `https://vt.tiktok.com/XXXXXXXX`
>>>>>>> d369438 (Initial deployment: Social Media Downloader production code)
