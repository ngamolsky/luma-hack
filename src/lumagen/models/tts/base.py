from abc import ABC, abstractmethod


class TTSModel(ABC):
    @abstractmethod
    async def generate_audio(self, script: str, sample_rate: int) -> bytes:
        pass
