"""
Speech-to-Text with Wake Word Detection for Voice Assistant.
Uses RealTimeSTT for real-time transcription with built-in wake word detection.
Optimized so STT runs on CPU, leaving GPU available for the LLM.
"""

import threading
import time
from typing import Callable
from config import (
    WAKE_WORD,
    REALTIMESTT_MODEL,
    WAKE_WORD_SENSITIVITY,
    GRAY,
    RESET,
    CYAN,
    YELLOW,
    GREEN,
)


class STTListener:
    """
    Real-time STT listener with wake word detection using RealTimeSTT.
    Uses RealTimeSTT's built-in wake word detection and text() method.
    Optimized for lower GPU use by forcing STT onto CPU.
    """

    def __init__(self, wake_word_callback: Callable, speech_callback: Callable):
        self.wake_word_callback = wake_word_callback
        self.speech_callback = speech_callback
        self.running = False
        self.listening_thread = None

        # RealTimeSTT recorder
        self.recorder = None
        self.initialized = False

        print(f"{CYAN}[STT] Initializing RealTimeSTT listener...{RESET}")
        print(f"{CYAN}[STT] Wake word: '{WAKE_WORD}'{RESET}")

    def initialize(self) -> bool:
        """Initialize RealTimeSTT with wake word detection."""
        try:
            from RealtimeSTT import AudioToTextRecorder
            import torch

            print(f"{CYAN}[STT] Loading RealTimeSTT...{RESET}")

            # Check CUDA only for visibility/debugging
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                cuda_device = torch.cuda.current_device()
                cuda_name = torch.cuda.get_device_name(cuda_device)
                print(f"{GREEN}[STT] CUDA available: {cuda_name}{RESET}")
            else:
                print(f"{YELLOW}[STT] CUDA not available{RESET}")

            # Force STT to CPU so GPU is reserved for Ollama/LLM
            device = "cpu"
            print(f"{CYAN}[STT] Initializing AudioToTextRecorder on {device}...{RESET}")

            self.recorder = AudioToTextRecorder(
                model=REALTIMESTT_MODEL,   # should be "tiny" in config for best speed
                language="en",
                device=device,
                spinner=False,
                wakeword_backend="pvporcupine",
                wake_words=WAKE_WORD,
                wake_words_sensitivity=WAKE_WORD_SENSITIVITY,
                on_wakeword_detected=self._on_wakeword_detected,
            )

            self.initialized = True
            print(
                f"{GREEN}[STT] Ready (model: {REALTIMESTT_MODEL}, "
                f"wake word: '{WAKE_WORD}', device: {device}){RESET}"
            )
            return True

        except ImportError:
            print(
                f"{GRAY}[STT] RealTimeSTT not installed. "
                f"Install with: pip install realtimestt{RESET}"
            )
            return False
        except Exception as e:
            print(f"{GRAY}[STT] Initialization error: {e}{RESET}")
            import traceback
            traceback.print_exc()
            return False

    def _on_wakeword_detected(self):
        """Callback when wake word is detected."""
        print(f"{GREEN}[STT] Wake word '{WAKE_WORD}' detected{RESET}")
        if self.wake_word_callback:
            self.wake_word_callback()

    def start(self):
        """Start listening."""
        if not self.initialized:
            print(f"{YELLOW}[STT] Not initialized. Call initialize() first.{RESET}")
            return False

        if self.running:
            print(f"{YELLOW}[STT] Already running.{RESET}")
            return True

        self.running = True
        print(f"{CYAN}[STT] Starting listener...{RESET}")

        try:
            self.listening_thread = threading.Thread(
                target=self._run_listener,
                daemon=True
            )
            self.listening_thread.start()
            print(f"{GREEN}[STT] Listener started{RESET}")
            return True
        except Exception as e:
            print(f"{GRAY}[STT] Failed to start listener: {e}{RESET}")
            self.running = False
            return False

    def _run_listener(self):
        """
        Main listening loop using RealTimeSTT's text() method.
        recorder.text() blocks until wake word is detected, then returns transcribed text.
        """
        try:
            while self.running:
                if not self.recorder:
                    break

                transcription_start = time.time()
                text = self.recorder.text()
                transcription_time = time.time() - transcription_start

                if text and text.strip():
                    # Remove wake word if it appears in returned text
                    text_clean = (
                        text.replace(WAKE_WORD, "")
                        .replace(WAKE_WORD.capitalize(), "")
                        .strip()
                    )

                    print(
                        f"{CYAN}[STT] Transcribed in {transcription_time:.2f}s: "
                        f"'{text_clean}'{RESET}"
                    )

                    if text_clean:
                        self.speech_callback(text_clean)
                else:
                    # Avoid noisy logging here
                    continue

        except Exception as e:
            print(f"{GRAY}[STT] Listener error: {e}{RESET}")
            import traceback
            traceback.print_exc()
            self.running = False

    def stop(self):
        """Stop listening."""
        self.running = False

        if self.recorder:
            try:
                print(f"{CYAN}[STT] Shutting down recorder...{RESET}")
                self.recorder.shutdown()
            except Exception as e:
                print(f"{GRAY}[STT] Error stopping recorder: {e}{RESET}")

        if self.listening_thread:
            self.listening_thread.join(timeout=2.0)

        print(f"{CYAN}[STT] Listener stopped{RESET}")