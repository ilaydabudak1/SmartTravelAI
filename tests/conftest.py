import os
import sys

import pytest

# Testler ağsız ve LLM'siz çalışır; gerçek veritabanına dokunmaz.
os.environ["SMARTTRAVEL_OFFLINE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def gecici_db(tmp_path, monkeypatch):
    import db
    import memory
    monkeypatch.setattr(db, "VERI_KLASORU", str(tmp_path))
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    memory.init_memory()
    yield tmp_path
