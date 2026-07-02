"""
Piper text-to-speech service.

Piper ships as a small, fast native binary rather than a Python package, so
this service shells out to it via subprocess instead of importing it. This
keeps the Python process lightweight and lets Piper run as a separate,
independently-updatable component (matching the "swap providers easily"
principle used for Ollama/Whisper).

Voice models (.onnx + .onnx.json) must be downloaded separately — see
README.md "Installation" for the download command.
"""
import asyncio
from pathlib import Path

from app.config import settings
from app.core.exceptions import SpeechSynthesisError
from app.logger import get_logger

logger = get_logger(__name__)


class PiperService:
    def __init__(self) -> None:
        self.binary_path = settings.piper_binary_path
        self.voice_model_path = settings.piper_voice_model_path
        self.voice_config_path = settings.piper_voice_config_path

    def is_available(self) -> bool:
        return Path(self.voice_model_path).exists() and Path(self.voice_config_path).exists()

    async def synthesize(self, text: str) -> bytes:
        """
        Run `piper --model <voice> --output_file -` with `text` piped to
        stdin, and return the raw WAV bytes produced on stdout.
        """
        if not self.is_available():
            raise SpeechSynthesisError(
                "Piper voice model not found. Download a voice model into "
                f"{self.voice_model_path} — see README.md."
            )

        cmd = [
            self.binary_path,
            "--model",
            self.voice_model_path,
            "--config",
            self.voice_config_path,
            "--output_file",
            "-",
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=text.encode("utf-8")), timeout=30
            )
        except FileNotFoundError as exc:
            raise SpeechSynthesisError(
                f"Piper binary not found at '{self.binary_path}'. Is it installed and on PATH?"
            ) from exc
        except asyncio.TimeoutError as exc:
            raise SpeechSynthesisError("Piper synthesis timed out after 30s.") from exc

        if process.returncode != 0:
            logger.error("Piper failed: %s", stderr.decode(errors="ignore"))
            raise SpeechSynthesisError("Piper failed to synthesize speech.")

        if not stdout:
            raise SpeechSynthesisError("Piper produced no audio output.")

        logger.info("Synthesized %d bytes of audio for %d chars of text", len(stdout), len(text))
        return stdout


piper_service = PiperService()
