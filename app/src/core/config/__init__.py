from src.core.config.agent import AgentSettings
from src.core.config.database import DatabaseSettings
from src.core.config.google_oauth import GoogleOAuthSettings
from src.core.config.jwt import JWTSettings


class Configs:
    db: DatabaseSettings
    google: GoogleOAuthSettings
    jwt: JWTSettings
    agent: AgentSettings

    def __init__(self) -> None:
        self.db = DatabaseSettings()
        self.google = GoogleOAuthSettings()
        self.jwt = JWTSettings()
        self.agent = AgentSettings()

    def validate_api_settings(self) -> None:
        pass


settings = Configs()
