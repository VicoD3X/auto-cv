from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RemoteStatus:
    enabled: bool
    host: str
    port: int

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

