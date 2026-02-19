from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="social-media-downloader",
    version="1.0.0",
    author="Social Media Downloader Team",
    description="A tool to download content from social media platforms",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sophearun/Social-Media-Downloader",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "yt-dlp>=2023.10.13",
        "requests>=2.31.0",
    ],
    entry_points={
        "console_scripts": [
            "sm-downloader=downloader.main:main",
        ],
    },
)
