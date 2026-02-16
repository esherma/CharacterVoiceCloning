#!/usr/bin/env python3
"""
Combine multiple Data voice clips into a single reference file for TTS
"""

import subprocess
import sys
from pathlib import Path

def combine_clips(clip_files, output_file="data_reference.wav"):
    """Combine multiple audio clips into one file"""
    
    if not clip_files:
        print("No clip files provided")
        return False
    
    # Check all files exist
    for clip in clip_files:
        if not Path(clip).exists():
            print(f"Error: File not found: {clip}")
            return False
    
    print(f"Combining {len(clip_files)} clips...")
    for i, clip in enumerate(clip_files, 1):
        print(f"  {i}. {clip}")
    
    # Create a temporary file list for ffmpeg concat
    concat_list = "concat_list.txt"
    with open(concat_list, 'w') as f:
        for clip in clip_files:
            # ffmpeg concat requires absolute paths or proper escaping
            abs_path = Path(clip).resolve()
            f.write(f"file '{abs_path}'\n")
    
    # Use ffmpeg concat demuxer for lossless concatenation
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_list,
        '-c', 'copy',
        '-y',
        output_file
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        print(f"\n✓ Combined clips saved to: {output_file}")
        
        # Get duration of final file
        duration_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            output_file
        ]
        result = subprocess.run(duration_cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        print(f"  Total duration: {duration:.1f} seconds")
        
        if duration < 20:
            print("\n⚠ Warning: Combined audio is less than 20 seconds.")
            print("  Voice cloning works better with 30-60 seconds of audio.")
        elif duration > 90:
            print("\n⚠ Warning: Combined audio is longer than 90 seconds.")
            print("  Consider using fewer clips for faster processing.")
        else:
            print("\n✓ Duration is good for voice cloning!")
        
        # Clean up temp file
        Path(concat_list).unlink()
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error combining clips: {e}")
        if Path(concat_list).exists():
            Path(concat_list).unlink()
        return False

def main():
    if len(sys.argv) < 2:
        print("Combine Data Voice Clips")
        print("=" * 60)
        print("\nUsage:")
        print(f"  {sys.argv[0]} clip1.wav clip2.wav clip3.wav [output.wav]")
        print("\nExample:")
        print(f"  {sys.argv[0]} data_clips/data_clip_01.wav data_clips/data_clip_02.wav")
        print(f"  {sys.argv[0]} data_clips/*.wav data_reference.wav")
        print("\nThis will combine the clips into a single reference file for TTS.")
        return 1
    
    # Parse arguments
    clip_files = []
    output_file = "data_reference.wav"
    
    for arg in sys.argv[1:]:
        if arg.endswith('.wav') and '*' not in arg:
            if Path(arg).exists():
                clip_files.append(arg)
            else:
                # Might be the output file
                if arg != sys.argv[-1]:
                    print(f"Warning: {arg} not found, skipping")
                else:
                    output_file = arg
        elif arg.endswith('.wav'):
            # Output file specified
            output_file = arg
    
    # If last argument doesn't exist, it's probably the output filename
    if clip_files and not Path(sys.argv[-1]).exists() and sys.argv[-1].endswith('.wav'):
        output_file = sys.argv[-1]
        clip_files = [f for f in clip_files if f != output_file]
    
    if not clip_files:
        print("Error: No valid clip files found")
        return 1
    
    if combine_clips(clip_files, output_file):
        print("\n" + "=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"\nYour Data voice reference is ready: {output_file}")
        print("\nYou can now use this with Qwen3-TTS for voice cloning!")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())