#!/usr/bin/env python3
"""
Test voice cloning with Qwen3-TTS Base models on MLX.
Tries different reference clips and model sizes to compare quality and speed.
"""

import argparse
import sys
import time
from pathlib import Path

import mlx.core as mx
import numpy as np
import soundfile as sf
from mlx_audio.tts.utils import load_model


MODELS = {
    "0.6B-8bit": "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit",
    "0.6B-bf16": "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-bf16",
    "1.7B-8bit": "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit",
    "1.7B-bf16": "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16",
}

# Reference clips with hand-written transcripts (longest clips first)
# Update these transcripts to match the actual audio content
REFERENCE_CLIPS = {
    "clip_14": {
        "path": "data_output/clips/clip_14.wav",
        "transcript": (
            "I feel nothing at all. That is part of my dilemma. "
            "I have the curiosity of humans, but there are questions that I will never have the answers to: "
            "what it is like to laugh, to cry, or to experience any hu-"
        ),
        "duration": "14s",
    },
}

TEST_SENTENCES = [
    "I am functioning within normal parameters.",
    "Captain, I believe I have found an anomaly in the sensor readings that warrants further investigation.",
    (
        "It is curious. I am apparently motivated by a desire to understand human behavior, "
        "and yet I frequently find it baffling."
    ),
]

OUTPUT_DIR = Path("clone_outputs")


def run_clone_test(model, model_key, clip_key, clip_info, use_transcript=True):
    """Run voice cloning with a single reference clip and generate test sentences."""
    ref_audio = clip_info["path"]
    ref_text = clip_info["transcript"] if use_transcript else None
    mode = "transcript" if (use_transcript and ref_text) else "xvector"

    print(f"\n  --- Ref: {clip_key} ({clip_info['duration']}) | Mode: {mode} ---")

    if use_transcript and ref_text is None:
        print(f"    Skipping transcript mode (no transcript provided for {clip_key})")
        return None

    out_dir = OUTPUT_DIR / model_key / f"{clip_key}_{mode}"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, text in enumerate(TEST_SENTENCES, 1):
        print(f"    Sentence {i}: \"{text[:60]}{'...' if len(text) > 60 else ''}\"")

        gen_results = list(model.generate(
            text=text,
            ref_audio=ref_audio,
            ref_text=ref_text,
            verbose=False,
        ))

        audio_arrays = []
        total_proc_time = 0.0
        sr = None
        for r in gen_results:
            audio_arrays.append(np.array(r.audio, copy=False))
            total_proc_time += r.processing_time_seconds
            sr = r.sample_rate

        audio = np.concatenate(audio_arrays) if len(audio_arrays) > 1 else audio_arrays[0]
        audio_duration = len(audio) / sr
        rtf = total_proc_time / audio_duration

        out_path = out_dir / f"sentence_{i}.wav"
        sf.write(str(out_path), audio, sr)

        results.append({
            "gen_time": total_proc_time,
            "audio_duration": audio_duration,
            "rtf": rtf,
        })

        print(f"      {total_proc_time:.2f}s -> {audio_duration:.2f}s audio (RTF: {rtf:.2f}x) -> {out_path}")

    avg_rtf = sum(r["gen_time"] for r in results) / sum(r["audio_duration"] for r in results)
    print(f"    Average RTF: {avg_rtf:.2f}x")
    return {"clip": clip_key, "mode": mode, "avg_rtf": avg_rtf, "results": results}


def benchmark_model(model_key, clips_to_test):
    model_id = MODELS[model_key]
    print(f"\n{'=' * 60}")
    print(f"Model: {model_id}")
    print(f"{'=' * 60}")

    print("Loading model...")
    load_start = time.time()
    model = load_model(model_id)
    load_time = time.time() - load_start
    print(f"Model loaded in {load_time:.1f}s")

    all_test_results = []

    for clip_key in clips_to_test:
        clip_info = REFERENCE_CLIPS[clip_key]
        if not Path(clip_info["path"]).exists():
            print(f"\n  Skipping {clip_key}: file not found at {clip_info['path']}")
            continue

        # x_vector mode (no transcript needed)
        result = run_clone_test(model, model_key, clip_key, clip_info, use_transcript=False)
        if result:
            all_test_results.append(result)

        # With transcript (if available)
        if clip_info["transcript"]:
            result = run_clone_test(model, model_key, clip_key, clip_info, use_transcript=True)
            if result:
                all_test_results.append(result)

    del model
    mx.clear_cache()

    return {"model": model_key, "load_time": load_time, "tests": all_test_results}


def main():
    parser = argparse.ArgumentParser(description="Test Qwen3-TTS voice cloning on Apple Silicon (MLX)")
    parser.add_argument(
        "models",
        nargs="*",
        default=["0.6B-8bit"],
        choices=list(MODELS.keys()),
        help=f"Which model(s) to test (default: 0.6B-8bit). Options: {list(MODELS.keys())}",
    )
    parser.add_argument(
        "--clips",
        nargs="+",
        default=["clip_14"],
        choices=list(REFERENCE_CLIPS.keys()),
        help=f"Which reference clips to use (default: clip_14). Options: {list(REFERENCE_CLIPS.keys())}",
    )
    args = parser.parse_args()

    print("Qwen3-TTS Voice Cloning Test (MLX)")
    print(f"Output directory: {OUTPUT_DIR}/")

    all_results = []
    for model_key in args.models:
        try:
            result = benchmark_model(model_key, args.clips)
            all_results.append(result)
        except Exception as e:
            print(f"\nError testing {model_key}: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    if all_results:
        print(f"\n{'=' * 60}")
        print("SUMMARY")
        print(f"{'=' * 60}")
        for r in all_results:
            print(f"\n  {r['model']} (load: {r['load_time']:.1f}s):")
            for t in r["tests"]:
                print(f"    {t['clip']} [{t['mode']}]: avg RTF {t['avg_rtf']:.2f}x")

    print(f"\nAll outputs saved to {OUTPUT_DIR}/")
    print("Listen and compare quality across models and clips!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
