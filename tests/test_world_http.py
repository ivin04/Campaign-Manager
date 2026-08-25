from __future__ import annotations

import database

from fastapi.testclient import TestClient

from app import app
from models.world_state import Entity


client = TestClient(app)