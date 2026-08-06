from api.client import StratzClient
from api.opendota_client import OpenDotaClient
from database import Database
from repositories.chat_wheel_repository import ChatWheelRepository
from repositories.hero_repository import HeroRepository
from repositories.match_repository import MatchRepository
from services.chat_wheel_service import ChatWheelService
from services.export_service import ExportService
from services.hero_service import HeroService
from services.parse_service import ParseService
from services.discovery.rampage_service import RampageService
from services.discovery.specific_top_service import SpecificTopService
from services.discovery.top_heroes_service import TopHeroesService


class ServiceFactory:
    def __init__(self) -> None:
        self.db = Database()
        self.client = StratzClient()
        self.opendota_client = OpenDotaClient()
        self.hero_repo = HeroRepository(self.db)
        self.match_repo = MatchRepository(self.db)
        self.chat_wheel_repo = ChatWheelRepository(self.db)

    def hero_service(self) -> HeroService:
        return HeroService(self.client, self.hero_repo)

    def chat_wheel_service(self) -> ChatWheelService:
        return ChatWheelService(self.chat_wheel_repo)

    def rampage_service(self) -> RampageService:
        return RampageService(self.client, self.hero_repo, self.match_repo)

    def top_heroes_service(self) -> TopHeroesService:
        return TopHeroesService(self.client, self.hero_repo, self.match_repo)

    def specific_top_service(self) -> SpecificTopService:
        return SpecificTopService(self.client, self.hero_repo, self.match_repo)

    def parse_service(self) -> ParseService:
        return ParseService(self.opendota_client, self.match_repo)

    def export_service(self) -> ExportService:
        return ExportService(self.hero_repo, self.match_repo, self.chat_wheel_repo)
