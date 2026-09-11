import os
import json
import structlog
from vosk import Model, KaldiRecognizer
import wave

logger = structlog.get_logger()

class VoskService:
    def __init__(self, model_path: str = "models/vosk-model-small-ru-0.22"):
        self.model_path = model_path
        self.model = None
        if os.path.exists(model_path):
            self.model = Model(model_path)
            logger.info("Vosk model loaded", path=model_path)
        else:
            logger.warning("Vosk model not found", path=model_path)

    def transcribe(self, audio_path: str) -> str:
        if not self.model:
            raise FileNotFoundError(f"Vosk model not found at {self.model_path}")

        wf = wave.open(audio_path, "rb")
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            raise ValueError("Audio file must be WAV mono PCM")

        rec = KaldiRecognizer(self.model, wf.getframerate())
        rec.SetWords(True)

        results = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                part = json.loads(rec.Result())
                if part.get("text"):
                    results.append(part["text"])

        part = json.loads(rec.FinalResult())
        if part.get("text"):
            results.append(part["text"])

        wf.close()
        return " ".join(results).strip()
