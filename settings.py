import os
try:
    from local_settings import *
except ImportError:
    # Fallback to default settings
    pass

SERVICES = {
    "bluesky": {
        "name": "Bluesky Service",
        "status_url": "http://127.0.0.1:8031/status", # just an example
        "home_url": "",
        "start_cmd": r"Full\\Path\\to\\start.bat",
        "cwd": r"Full\\Path\\to\\working\\directory",
        "details": True, # whether to show /status endpoint response in the UI
    },
    "reddit": {
        "name": "Reddit Service",
        "status_url": "",
        "home_url": "",
        "start_cmd": r"",
        "cwd": r"",
        "details": False,
    },
}