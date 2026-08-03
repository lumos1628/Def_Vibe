import json
from pathlib import Path
from repositories.chat_wheel_repository import ChatWheelRepository


class ChatWheelService:
    def __init__(self, repository: ChatWheelRepository):
        self.repository = repository

    def ensure_synced(self) -> None:
        if self.repository.count() == 0:
            self.sync()
        else:
            print(f"Usando {self.repository.count()} chat wheels ya sincronizados.")

    def sync(self) -> int:
        print("Sincronizando chat wheels desde el catálogo local...")
        chat_wheel_path = Path(__file__).parent.parent / "data" / "chat_wheel.json"
        if not chat_wheel_path.exists():
            raise FileNotFoundError(f"No se encontró el catálogo de chat wheels: {chat_wheel_path}")

        with open(chat_wheel_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        entries = []
        for key, value in data.items():
            entry = dict(value)
            entry["id"] = int(key)
            entries.append(entry)

        self.repository.upsert(entries)
        print(f"{len(entries)} chat wheels sincronizados.")
        return len(entries)
