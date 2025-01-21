from httpx import AsyncClient
from sqlalchemy.orm import Session

class TestCase:
    def __init__(self, url: str, session: Session):
        self.setup()
        self.run()
        self.client = AsyncClient(base_url=url)
        self.session = session

    def setup(self):
        pass

    def sequence(self):
        return [
            getattr(self, method)
            for method in dir(self)
            if callable(getattr(self, method))
            and not method.startswith("__")
            and not method == "run"
        ]

    def run(self):
        for method in self.sequence():
            method()
