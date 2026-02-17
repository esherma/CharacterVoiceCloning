#!/bin/bash
# Claude Code "Stop" hook: speak Claude's last response using a cloned voice.
# Reads hook JSON from stdin, extracts the transcript path, parses the last
# assistant message, and passes it to mlx_audio TTS with a reference clip.
#
# Setup:
#   1. Install mlx-audio globally:  uv tool install mlx-audio --prerelease=allow
#   2. Copy your reference WAV and transcript to REF_DIR (see below)
#   3. Update REF_DIR, REF_AUDIO, and model ID to match your setup
#   4. Add the hook to ~/.claude/settings.json (see settings-snippet.json)

set -euo pipefail

# ── Configuration ──────────────────────────────────────────
# Point these at your reference audio and transcript file.
REF_DIR="$HOME/.config/cmdr-data-voice"
REF_AUDIO="$REF_DIR/clip_14.wav"
REF_TEXT="$(cat "$REF_DIR/ref_transcript.txt")"
MODEL="mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit"
MAX_CHARS=2000

# ── Logging ────────────────────────────────────────────────
LOG="$REF_DIR/speak.log"

log() {
    echo "$(date '+%H:%M:%S') [$$] $1" >> "$LOG"
}

log "Hook fired"

# ── Kill previous instance ─────────────────────────────────
PIDFILE="$REF_DIR/speak.pid"
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    log "Killing old PID $OLD_PID"
    kill "$OLD_PID" 2>/dev/null || true
    pkill -P "$OLD_PID" 2>/dev/null || true
    rm -f "$PIDFILE"
fi
echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT

# ── Read hook input ────────────────────────────────────────
INPUT=$(cat)
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // empty')
log "Transcript: $TRANSCRIPT_PATH"

if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
    log "No transcript, exiting"
    exit 0
fi

# Wait for transcript to be flushed to disk
sleep 1

# ── Extract last assistant message ─────────────────────────
TEXT=$(tail -50 "$TRANSCRIPT_PATH" | \
    jq -r 'select(.type == "assistant") |
        if (.message.content | type) == "array" then
            [.message.content[] | select(.type == "text") | .text] | join(" ")
        elif (.message.content | type) == "string" then
            .message.content
        else
            empty
        end' 2>/dev/null | \
    tail -1)

log "Text (first 100): ${TEXT:0:100}"

if [ -z "$TEXT" ]; then
    log "Empty text, exiting"
    exit 0
fi

TEXT="${TEXT:0:$MAX_CHARS}"

# ── Generate and play ──────────────────────────────────────
log "Starting TTS"
mlx_audio.tts.generate \
    --model "$MODEL" \
    --text "$TEXT" \
    --ref_audio "$REF_AUDIO" \
    --ref_text "$REF_TEXT" \
    --play \
    --stream \
    2>/dev/null
log "TTS finished"

exit 0
