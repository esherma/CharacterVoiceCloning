# Claude Code Voice Hook

Speaks Claude Code's responses aloud using a cloned voice. Uses the [Stop hook](https://docs.anthropic.com/en/docs/claude-code/hooks) to trigger TTS after each response.

## Requirements

- macOS with Apple Silicon
- [uv](https://docs.astral.sh/uv/)
- [jq](https://jqlang.github.io/jq/) (`brew install jq`)
- A reference WAV clip of the voice you want to clone, plus a text transcript of what's said in the clip

## Setup

### 1. Install mlx-audio globally

```bash
uv tool install mlx-audio --prerelease=allow
```

This makes `mlx_audio.tts.generate` available as a CLI command everywhere.

### 2. Prepare reference audio

Create a config directory and copy your reference clip and transcript:

```bash
mkdir -p ~/.config/cmdr-data-voice
cp /path/to/your/reference_clip.wav ~/.config/cmdr-data-voice/clip_14.wav
echo "The exact words spoken in the reference clip" > ~/.config/cmdr-data-voice/ref_transcript.txt
```

The reference clip should be a clean speech sample (10-30 seconds). The transcript should match the audio exactly.

### 3. Install the hook script

Copy `speak.sh` to your config directory and make it executable:

```bash
cp speak.sh ~/.config/cmdr-data-voice/speak.sh
chmod +x ~/.config/cmdr-data-voice/speak.sh
```

Edit the script to update `REF_AUDIO`, `REF_TEXT`, and `MODEL` if needed.

### 4. Register the hook

Merge the contents of `settings-snippet.json` into your `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/.config/cmdr-data-voice/speak.sh",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

### 5. Test it

Start a new Claude Code session and send a message. After Claude responds, you should hear the response spoken aloud.

Check `~/.config/cmdr-data-voice/speak.log` for debug output if it doesn't work.

## Notes

- The first run downloads the model weights (~600MB for 0.6B-8bit). Subsequent runs use the cached model.
- The hook kills any previous TTS instance before starting a new one, so rapid responses won't overlap.
- A 1-second delay before reading the transcript ensures the latest response is captured.
- Text is truncated to 2000 characters to keep generation time reasonable.
- To disable, remove the `Stop` hook from `~/.claude/settings.json`.
