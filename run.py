import os
from app.main import create_app
import uvicorn

def _get_env(key: str, default: str) -> str:
    v = os.getenv(key)
    return v.strip() if v and v.strip() else default

app = create_app()

if __name__ == "__main__":
    host = _get_env("FOCUSPILOT_HOST", "127.0.0.1")
    port = int(_get_env("FOCUSPILOT_PORT", "8001"))
    uvicorn.run(app, host=host, port=port)