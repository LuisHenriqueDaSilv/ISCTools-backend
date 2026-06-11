from src.core.config.agent import AgentSettings
from src.core.config.cors import CORSSettings
from src.core.config.database import DatabaseSettings
from src.core.config.google_oauth import GoogleOAuthSettings
from src.core.config.jwt import JWTSettings
from src.core.config.langsmith import LangSmithSettings


class Configs:
    db: DatabaseSettings
    google: GoogleOAuthSettings
    jwt: JWTSettings
    agent: AgentSettings
    langsmith: LangSmithSettings
    cors: CORSSettings

    def __init__(self) -> None:
        self.db = DatabaseSettings()
        self.google = GoogleOAuthSettings()
        self.jwt = JWTSettings()
        self.agent = AgentSettings()
        self.langsmith = LangSmithSettings()
        self.cors = CORSSettings()

    def validate_api_settings(self) -> None:
        pass


settings = Configs()
