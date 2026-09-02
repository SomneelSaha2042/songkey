from __future__ import annotations

import io
import wave

from songkey.audio.models import AudioFormat
from songkey.audio.wav import encode_wav


def test_wav_header_matches_format():
    audio_format = AudioFormat(sample_rate=48000, channels=2, sample_width=2)
    pcm = b"\x00\x01" * 100

    wav_bytes = encode_wav(pcm, audio_format)

    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        assert wav_file.getnchannels() == 2
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 48000
        assert wav_file.readframes(wav_file.getnframes()) == pcm


def test_six_seconds_at_48khz_stereo_has_expected_frame_count():
    audio_format = AudioFormat(sample_rate=48000, channels=2, sample_width=2)
    frame_count = 48000 * 6
    pcm = b"\x00\x00" * frame_count * audio_format.channels

    wav_bytes = encode_wav(pcm, audio_format)

    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        assert wav_file.getnframes() == frame_count


def test_empty_pcm_produces_valid_zero_length_wav():
    audio_format = AudioFormat(sample_rate=48000, channels=2, sample_width=2)

    wav_bytes = encode_wav(b"", audio_format)

    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        assert wav_file.getnframes() == 0
