#!/usr/bin/env python3
"""
Voice Clip Extractor
Downloads and extracts clean audio clips from YouTube for TTS voice cloning
"""

import argparse
import re
import subprocess
import json
import sys
from pathlib import Path

def slugify(text):
    """Convert a query string to a safe filesystem slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s-]+', '_', text)
    return text.strip('_')


def check_dependencies():
    """Check if required tools are installed"""
    print("Checking dependencies...")
    
    # Check yt-dlp
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        print("✓ yt-dlp found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ yt-dlp not found. Install with: brew install yt-dlp")
        return False
    
    # Check ffmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✓ ffmpeg found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ ffmpeg not found. Install with: brew install ffmpeg")
        return False
    
    return True

def search_youtube(query, max_results=5):
    """Search YouTube for Data voice clips"""
    print(f"\nSearching YouTube for: '{query}'")
    
    cmd = [
        'yt-dlp',
        '--dump-json',
        '--skip-download',
        '--default-search', 'ytsearch' + str(max_results),
        query
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        videos = []
        
        for line in result.stdout.strip().split('\n'):
            if line:
                video = json.loads(line)
                videos.append({
                    'title': video.get('title', 'Unknown'),
                    'url': video.get('webpage_url', ''),
                    'duration': video.get('duration', 0),
                    'id': video.get('id', '')
                })
        
        print(f"\nFound {len(videos)} videos:")
        for i, video in enumerate(videos, 1):
            duration_min = video['duration'] // 60
            duration_sec = video['duration'] % 60
            print(f"{i}. {video['title']}")
            print(f"   Duration: {duration_min}:{duration_sec:02d}")
            print(f"   URL: {video['url']}")
            print()
        
        return videos
    
    except subprocess.CalledProcessError as e:
        print(f"Error searching YouTube: {e}")
        return []

def download_video(url, output_dir, slug, index):
    """Download YouTube video as audio with a slug-based filename.

    Returns the filepath on success, None on failure.
    """
    Path(output_dir).mkdir(exist_ok=True)

    filename = f"{slug}_{index:02d}.%(ext)s"
    output_template = f"{output_dir}/{filename}"

    cmd = [
        'yt-dlp',
        '-x',  # Extract audio only
        '--audio-format', 'wav',  # Convert to wav
        '--audio-quality', '0',  # Best quality
        '-o', output_template,
        url
    ]

    print(f"\nDownloading from: {url}")
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)

        expected = Path(output_dir) / f"{slug}_{index:02d}.wav"
        if expected.exists():
            print(f"✓ Downloaded: {expected}")
            return str(expected)

        # Fallback: find the most recent wav in the directory
        wav_files = list(Path(output_dir).glob(f"{slug}_{index:02d}.*"))
        if wav_files:
            filepath = str(wav_files[0])
            print(f"✓ Downloaded: {filepath}")
            return filepath

    except subprocess.CalledProcessError as e:
        print(f"Error downloading: {e}")
        print(e.stderr)

    return None


def write_manifest(output_dir, slug, entries):
    """Write a manifest mapping downloaded filenames to YouTube metadata."""
    manifest_path = Path(output_dir) / f"DOWNLOADS_{slug}.md"
    with open(manifest_path, 'w') as f:
        f.write(f"# Downloads: {slug}\n\n")
        f.write("| File | YouTube ID | Title | URL |\n")
        f.write("|------|-----------|-------|-----|\n")
        for entry in entries:
            f.write(f"| {entry['file']} | {entry['id']} | {entry['title']} | {entry['url']} |\n")
    print(f"✓ Manifest written: {manifest_path}")

def extract_clip(input_file, start_time, end_time, output_file, apply_filters=True):
    """Extract a clip from the audio file with optional noise reduction"""
    duration = end_time - start_time
    
    # Build ffmpeg command
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-ss', str(start_time),
        '-t', str(duration),
    ]
    
    if apply_filters:
        # Apply audio filters:
        # - highpass: remove low rumble (80Hz and below)
        # - lowpass: remove high hiss (8000Hz and above)
        # - afftdn: adaptive noise reduction
        # - loudnorm: normalize loudness
        filters = [
            'highpass=f=80',
            'lowpass=f=8000',
            'afftdn=nf=-25',
            'loudnorm=I=-16:TP=-1.5:LRA=11'
        ]
        cmd.extend(['-af', ','.join(filters)])
    
    cmd.extend([
        '-ar', '22050',  # 22.05kHz sample rate (good for speech)
        '-ac', '1',  # Mono
        '-y',  # Overwrite output
        output_file
    ])
    
    print(f"Extracting clip: {start_time}s - {end_time}s -> {output_file}")
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        print(f"✓ Extracted: {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error extracting clip: {e}")
        return False

def interactive_clip_extraction(audio_file, output_dir="clips", start_number=1):
    """Interactively extract clips from an audio file.

    Returns the number of clips extracted in this session.
    """
    Path(output_dir).mkdir(exist_ok=True)

    print(f"\n{'='*60}")
    print("CLIP EXTRACTION MODE")
    print(f"{'='*60}")
    print(f"Source file: {audio_file}")
    print("\nYou can now extract specific time ranges as clips.")
    print("Enter times in format: START END (in seconds)")
    print("Examples:")
    print("  10 25     - Extract from 10s to 25s")
    print("  1:30 1:45 - Extract from 1min 30s to 1min 45s")
    print("\nType 'done' when finished, 'help' for commands")

    clip_number = start_number
    
    while True:
        print(f"\n--- Clip {clip_number} ---")
        user_input = input("Enter time range (START END) or command: ").strip().lower()
        
        if user_input == 'done':
            break
        elif user_input == 'help':
            print("\nCommands:")
            print("  START END - Extract clip (e.g., '10 25' or '1:30 1:45')")
            print("  done      - Finish and exit")
            print("  help      - Show this help")
            continue
        elif not user_input:
            continue
        
        try:
            parts = user_input.split()
            if len(parts) != 2:
                print("Please enter exactly two times: START END")
                continue
            
            # Parse time format (supports "seconds" or "MM:SS")
            def parse_time(time_str):
                if ':' in time_str:
                    parts = time_str.split(':')
                    return int(parts[0]) * 60 + float(parts[1])
                return float(time_str)
            
            start = parse_time(parts[0])
            end = parse_time(parts[1])
            
            if start >= end:
                print("Start time must be before end time!")
                continue
            
            output_file = f"{output_dir}/clip_{clip_number:02d}.wav"
            
            if extract_clip(audio_file, start, end, output_file):
                clip_number += 1
            
        except ValueError as e:
            print(f"Invalid time format: {e}")
            print("Use format: 10 25  or  1:30 1:45")
    
    extracted = clip_number - start_number
    print(f"\n✓ Extracted {extracted} clips to {output_dir}/")
    return extracted

def main():
    parser = argparse.ArgumentParser(
        description="Download and extract clean audio clips from YouTube for TTS voice cloning"
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="YouTube search query (e.g. 'Data Star Trek voice lines')"
    )
    parser.add_argument(
        "-n", "--max-results",
        type=int,
        default=5,
        help="Maximum number of search results (default: 5)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="output",
        help="Base output directory (default: output). Downloads go to <dir>/downloads/, clips to <dir>/clips/"
    )
    parser.add_argument(
        "--clip",
        action="store_true",
        help="Skip search/download and extract clips from existing files in the downloads directory"
    )
    args = parser.parse_args()

    download_dir = Path(args.output_dir) / "downloads"

    print("=" * 60)
    print("VOICE CLIP EXTRACTOR")
    print("For TTS Voice Cloning")
    print("=" * 60)

    if args.clip:
        # Clip-only mode: use existing downloaded files
        if not download_dir.exists():
            print(f"\nNo downloads directory found at {download_dir}")
            return 1

        downloaded_files = sorted(download_dir.glob("*.wav"))
        if not downloaded_files:
            print(f"\nNo .wav files found in {download_dir}")
            return 1

        downloaded_files = [str(f) for f in downloaded_files]
        print(f"\nFound {len(downloaded_files)} existing file(s) in {download_dir}")

    else:
        # Full mode: search + download
        query = " ".join(args.query) if args.query else None
        if not query:
            query = input("Enter YouTube search query (e.g. 'Data Star Trek voice lines'): ").strip()
        if not query:
            print("No query provided.")
            return 1

        slug = slugify(query)

        # Check dependencies
        if not check_dependencies():
            print("\nPlease install missing dependencies and try again.")
            print("\nOn Mac:")
            print("  brew install yt-dlp ffmpeg")
            return 1

        # Search for videos
        videos = search_youtube(query, max_results=args.max_results)

        if not videos:
            print("No videos found. Try a different search term.")
            return 1

        # Let user choose videos to download
        print("Enter video numbers to download (e.g. '1', '1 3 5', or 'all').")
        print("Type 'q' to quit.")

        selected_videos = []
        while not selected_videos:
            choice = input("\nVideo(s) to download: ").strip().lower()

            if choice == 'q':
                return 0

            if choice == 'all':
                selected_videos = list(videos)
                break

            try:
                indices = [int(c) - 1 for c in choice.split()]
                for idx in indices:
                    if 0 <= idx < len(videos):
                        selected_videos.append(videos[idx])
                    else:
                        print(f"Skipping invalid number {idx + 1} (must be 1-{len(videos)})")
                if not selected_videos:
                    print("No valid selections. Try again.")
            except ValueError:
                print("Please enter numbers separated by spaces, 'all', or 'q'")

        # Download selected videos
        manifest_entries = []
        downloaded_files = []
        for i, video in enumerate(selected_videos, 1):
            audio_file = download_video(video['url'], str(download_dir), slug, i)
            if audio_file:
                downloaded_files.append(audio_file)
                manifest_entries.append({
                    'file': Path(audio_file).name,
                    'id': video['id'],
                    'title': video['title'],
                    'url': video['url'],
                })
            else:
                print(f"Failed to download: {video['title']}")

        if not downloaded_files:
            print("No videos were downloaded successfully.")
            return 1

        write_manifest(str(download_dir), slug, manifest_entries)

    # Extract clips from downloaded files in a loop
    clip_dir = Path(args.output_dir) / "clips"
    total_clips = 0
    # Start numbering after any existing clips
    existing = list(Path(clip_dir).glob("clip_*.wav")) if clip_dir.exists() else []
    next_clip = len(existing) + 1

    while True:
        if len(downloaded_files) == 1:
            audio_file = downloaded_files[0]
        else:
            print(f"\nDownloaded files:")
            for i, f in enumerate(downloaded_files, 1):
                print(f"  {i}. {Path(f).name}")
            print(f"  q. Quit")

            audio_file = None
            while audio_file is None:
                pick = input("\nWhich file to extract clips from? ").strip().lower()
                if pick == 'q':
                    break
                try:
                    pick_idx = int(pick) - 1
                    if 0 <= pick_idx < len(downloaded_files):
                        audio_file = downloaded_files[pick_idx]
                    else:
                        print(f"Enter a number between 1 and {len(downloaded_files)}")
                except ValueError:
                    print("Enter a valid number, or 'q' to quit")

            if audio_file is None:
                break

        num_clips = interactive_clip_extraction(
            audio_file, output_dir=str(clip_dir), start_number=next_clip
        )
        total_clips += num_clips
        next_clip += num_clips

        if len(downloaded_files) == 1:
            break

        another = input("\nExtract clips from another file? (y/n): ").strip().lower()
        if another != 'y':
            break

    if total_clips > 0:
        print("\n" + "=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"Extracted {total_clips} clips to {clip_dir}/")
        print("\nNext steps:")
        print("1. Listen to the clips and pick the best ones")
        print("2. Concatenate 2-3 good clips for a ~30-60 second reference")
        print("3. Use with your TTS voice cloning tool")

    return 0

if __name__ == "__main__":
    sys.exit(main())