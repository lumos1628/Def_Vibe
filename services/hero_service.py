from api.client import StratzClient
from api.queries import HEROES_QUERY
from repositories.hero_repository import HeroRepository

class HeroService:
    def __init__(self, client: StratzClient, repository: HeroRepository):
        self.client = client
        self.repository = repository

    def sync(self) -> int:
        print("Sincronizando héroes desde Stratz...")
        data = self.client.execute(HEROES_QUERY)
        heroes = data["constants"]["heroes"]
        self.repository.upsert(heroes)
        print(f"{len(heroes)} héroes sincronizados.")
        return len(heroes)

    def ensure_synced(self) -> None:
        if self.repository.count() == 0:
            self.sync()
        else:
            print(f"Usando {self.repository.count()} héroes ya sincronizados.")
