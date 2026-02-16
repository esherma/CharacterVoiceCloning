# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CharacterVoiceCloning is a toolkit for extracting clean voice clips from YouTube and preparing reference audio for TTS voice cloning. It's for personal, non-commercial use only. No Python audio libraries are used -- everything runs through subprocess calls to `yt-dlp` and `ffmpeg`.

## Commands

```bash
# Full workflow: search YouTube, download, extract clips interactively
python data_extractor.py "Data Star Trek voice lines"
python data_extractor.py -n 10 -o data_output "query here"

# Extract clips from already-downloaded files
python data_extractor.py --clip -o data_output

# Combine clips into a single TTS reference file
python combine_clips.py clips/clip_01.wav clips/clip_02.wav output.wav
```

External tools required: `yt-dlp`, `ffmpeg` (both via `brew install`).

## Architecture

Two scripts forming a three-stage pipeline:

1. **`data_extractor.py`** -- Handles stages 1 and 2: YouTube search/download and interactive clip extraction. Downloads go to `<output-dir>/downloads/`, clips to `<output-dir>/clips/`. A markdown manifest tracks which YouTube videos were downloaded. Extracted clips get audio filtering (highpass, lowpass, noise reduction, loudness normalization) and are resampled to 22.05kHz mono.

2. **`combine_clips.py`** -- Stage 3: concatenates selected clips into a single reference WAV file using ffmpeg's concat demuxer. Warns if total duration is outside the 20-90 second range (30-60s is ideal for voice cloning).

Both scripts are interactive CLI tools with user prompts for selection and time-range entry.

## Next Steps: Voice Cloning Experiments

### Target Models

Use the **Base** variants (not CustomVoice) for voice cloning:
- `Qwen/Qwen3-TTS-12Hz-1.7B-Base` -- higher quality
- `Qwen/Qwen3-TTS-12Hz-0.6B-Base` -- lighter/faster

Key API: `model.generate_voice_clone(text, language, ref_audio, ref_text, x_vector_only_mode)`. Use `create_voice_clone_prompt()` to pre-compute the voice prompt and reuse across generations for efficiency. The model accepts ref_audio as a file path, URL, base64, or numpy array tuple.

### Experiment Matrix

Run each of the following 5 configurations against both model sizes (10 experiments total). Evaluate on quality and speed.

**1. Individual long clips (with hand-written transcripts)**
Use the longest extracted clips individually as reference audio: the 14s clip, 13s clip, and two 11s clips. Hand-write an accurate transcript for each. This tests whether a single clean clip is sufficient.

**2. All clips concatenated, x_vector_only_mode=True (no transcript)**
Concatenate all clips with `combine_clips.py`. Pass to the model with `x_vector_only_mode=True` and `ref_text=None`. Simplest approach -- no transcription needed. Per Qwen docs, cloning quality may be reduced without a transcript.

**3. All clips concatenated, with auto-generated transcript**
Same concatenated audio, but generate a transcript using a speech-to-text model (e.g. Whisper) rather than transcribing manually. Tests whether a full transcript improves over x_vector_only_mode for longer/concatenated audio.

**4. All clips concatenated with silence padding, with auto-generated transcript**
Insert silence (0.5s is a reasonable starting point; try 0.25s-1.0s range) between clips before concatenating. This gives the model cleaner boundaries between utterances. Transcribe with STT. May need to extend `combine_clips.py` to support inserting silence gaps.

**5. All clips concatenated with silence padding, x_vector_only_mode=True**
Same padded concatenation as #4 but without transcript. Tests whether silence padding alone helps the x_vector extraction.

### Evaluation

For each experiment, generate the same set of test sentences and compare:
- Voice similarity to the character
- Naturalness / coherence
- Inference speed (wall-clock time per generation)
- Any artifacts, glitches, or drift

### Future Ideas

- Add batch/non-interactive mode for clip extraction with a timestamps file
- Explore speaker diarization to auto-isolate a specific character's voice from multi-speaker scenes
