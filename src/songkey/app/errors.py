from __future__ import annotations

from enum import Enum, auto


class AppErrorCode(Enum):
    HOTKEY_UNAVAILABLE = auto()
    WASAPI_UNAVAILABLE = auto()
    DEVICE_UNAVAILABLE = auto()
    CAPTURE_FAILED = auto()
    NO_AUDIO = auto()
    OFFLINE = auto()
    RECOGNITION_TIMEOUT = auto()
    NO_MATCH = auto()
    PROVIDER_RESPONSE_INVALID = auto()
    INTERNAL_ERROR = auto()


USER_MESSAGES: dict[AppErrorCode, str] = {
    AppErrorCode.HOTKEY_UNAVAILABLE: "Shortcut is already in use",
    AppErrorCode.WASAPI_UNAVAILABLE: "Windows audio capture is unavailable",
    AppErrorCode.DEVICE_UNAVAILABLE: "No active output device found",
    AppErrorCode.CAPTURE_FAILED: "Couldn't capture system audio",
    AppErrorCode.NO_AUDIO: "No audio is playing",
    AppErrorCode.OFFLINE: "You're offline",
    AppErrorCode.RECOGNITION_TIMEOUT: "Recognition timed out",
    AppErrorCode.NO_MATCH: "No match found",
    AppErrorCode.PROVIDER_RESPONSE_INVALID: "Recognition service returned an unexpected response",
    AppErrorCode.INTERNAL_ERROR: "Something went wrong",
}


class AppError(Exception):
    def __init__(self, code: AppErrorCode, detail: str | None = None) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.name}: {detail}" if detail else code.name)

    @property
    def user_message(self) -> str:
        return USER_MESSAGES[self.code]
