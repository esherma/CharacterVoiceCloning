# CharacterVoiceCloning

A toolkit for extracting clean voice clips from YouTube videos and preparing them as reference audio for TTS voice cloning. Built for cloning fictional character voices for personal, non-commercial use (e.g. a home assistant that sounds like your favorite starship officer).

**This project is intended exclusively for personal use.** It is not designed for, nor should it be used for, commercial purposes, impersonation, or any use that would infringe on the rights of content creators or voice actors.

## What It Does

1. **Search & Download** -- Search YouTube for videos featuring a character's voice and download them as high-quality audio
2. **Extract Clips** -- Interactively select time ranges to pull clean speech clips, with built-in noise reduction and normalization
3. **Combine Clips** -- Merge your best clips into a single 30-60 second reference file suitable for TTS voice cloning

## Prerequisites

- Python 3.13+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) -- `brew install yt-dlp`
- [ffmpeg](https://ffmpeg.org/) -- `brew install ffmpeg`

## Usage

### Search, download, and extract clips

```bash
python data_extractor.py "Data Star Trek voice lines"
```

Options:
- `-n` / `--max-results` -- Number of YouTube search results (default: 5)
- `-o` / `--output-dir` -- Base output directory (default: `output`)

The tool will walk you through selecting videos to download and then interactively extracting time ranges as individual clips.

### Extract clips from previously downloaded files

```bash
python data_extractor.py --clip -o output
```

### Combine clips into a reference file

```bash
python combine_clips.py output/clips/clip_01.wav output/clips/clip_02.wav output/clips/clip_03.wav combined_reference.wav
```

## Audio Processing

Extracted clips are automatically processed with:
- High-pass filter (80Hz) to remove low rumble
- Low-pass filter (8kHz) to remove hiss
- Adaptive noise reduction
- Loudness normalization (ITU-R BS.1770)
- Downsampled to 22.05kHz mono (optimized for speech/TTS)
