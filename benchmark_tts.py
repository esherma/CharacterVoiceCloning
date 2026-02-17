#!/usr/bin/env python3
"""
Benchmark Qwen3-TTS CustomVoice (predefined speaker) inference speed on Apple Silicon via mlx-audio.
Tests stock and quantized models with a few short sentences using the built-in "Ryan" voice.
This is separate from voice cloning -- see test_voice_clone.py for cloning with a reference clip.
"""

import argparse
import sys
import time

import mlx.core as mx
import numpy as np
import soundfile as sf
from mlx_audio.tts.utils import load_model


MODELS = {
    "0.6B-8bit": "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit",
    "0.6B": "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    "1.7B-8bit": "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit",
    "1.7B": "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16",
}

TEST_SENTENCES = [
    "I am functioning within normal parameters.",
    "Captain, I believe I have found an anomaly in the sensor readings that warrants further investigation.",
    (
        "It is curious. I am apparently motivated by a desire to understand human behavior, "
        "and yet I frequently find it baffling."
    ),
]

SPEAKER = "Ryan"


def benchmark_model(model_key):
    model_id = MODELS[model_key]
    print(f"\n{'=' * 60}")
    print(f"Model: {model_id}")
    print(f"{'=' * 60}")

    print("Loading model...")
    load_start = time.time()
    model = load_model(model_id)
    load_time = time.time() - load_start
    print(f"Model loaded in {load_time:.1f}s")

    results = []
    for i, text in enumerate(TEST_SENTENCES, 1):
        print(f"\n--- Sentence {i} ({len(text)} chars) ---")
        print(f"  \"{text[:80]}{'...' if len(text) > 80 else ''}\"")

        gen_results = list(model.generate(
            text=text,
            voice=SPEAKER,
            verbose=False,
        ))

        # Combine segments if multiple
        audio_arrays = []
        total_tokens = 0
        total_proc_time = 0.0
        sr = None
        for r in gen_results:
            audio_np = np.array(r.audio, copy=False)
            audio_arrays.append(audio_np)
            total_tokens += r.token_count
            total_proc_time += r.processing_time_seconds
            sr = r.sample_rate

        audio = np.concatenate(audio_arrays) if len(audio_arrays) > 1 else audio_arrays[0]
        audio_duration = len(audio) / sr
        rtf = total_proc_time / audio_duration

        results.append({
            "sentence": i,
            "chars": len(text),
            "gen_time": total_proc_time,
            "audio_duration": audio_duration,
            "rtf": rtf,
            "tokens": total_tokens,
        })

        print(f"  Generation: {total_proc_time:.2f}s")
        print(f"  Audio duration: {audio_duration:.2f}s")
        print(f"  Real-time factor: {rtf:.2f}x (< 1.0 = faster than real-time)")
        print(f"  Tokens: {total_tokens}")

        out_path = f"benchmark_{model_key}_{i}.wav"
        sf.write(out_path, audio, sr)
        print(f"  Saved: {out_path}")

    # Summary
    print(f"\n{'─' * 60}")
    print(f"Summary for {model_key}:")
    print(f"  Model load time: {load_time:.1f}s")
    total_gen = sum(r["gen_time"] for r in results)
    total_audio = sum(r["audio_duration"] for r in results)
    print(f"  Total generation: {total_gen:.2f}s for {total_audio:.2f}s of audio")
    print(f"  Average RTF: {total_gen / total_audio:.2f}x")

    # Free memory
    del model
    mx.clear_cache()

    return {"model": model_key, "load_time": load_time, "results": results}


def main():
    parser = argparse.ArgumentParser(description="Benchmark Qwen3-TTS on Apple Silicon (MLX)")
    parser.add_argument(
        "models",
        nargs="*",
        default=["0.6B-8bit"],
        choices=list(MODELS.keys()),
        help=f"Which model(s) to benchmark (default: 0.6B-8bit). Options: {list(MODELS.keys())}",
    )
    args = parser.parse_args()

    print("Qwen3-TTS Benchmark (MLX)")
    print(f"Available models: {list(MODELS.keys())}")

    all_results = []
    for model_key in args.models:
        try:
            result = benchmark_model(model_key)
            all_results.append(result)
        except Exception as e:
            print(f"\nError benchmarking {model_key}: {e}")
            import traceback
            traceback.print_exc()

    if len(all_results) > 1:
        print(f"\n{'=' * 60}")
        print("COMPARISON")
        print(f"{'=' * 60}")
        for r in all_results:
            total_gen = sum(s["gen_time"] for s in r["results"])
            total_audio = sum(s["audio_duration"] for s in r["results"])
            avg_rtf = total_gen / total_audio
            print(f"  {r['model']}: load={r['load_time']:.1f}s  avg RTF={avg_rtf:.2f}x")

    return 0


if __name__ == "__main__":
    sys.exit(main())
