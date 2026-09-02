from __future__ import annotations

import io
import wave

from songkey.audio.models import AudioFormat


def encode_wav(pcm: bytes, audio_format: AudioFormat) -> bytes:
    """Pure in-memory RIFF/WAV encoder. Never touches the filesystem."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(audio_format.channels)
        wav_file.setsampwidth(audio_format.sample_width)
        wav_file.setframerate(audio_format.sample_rate)
        wav_file.writeframes(pcm)
    return buf.getvalue()
