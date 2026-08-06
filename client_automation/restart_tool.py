import requests
import time

try:
    print("Stopping tool...")
    requests.post("http://127.0.0.1:3006/api/v1/seeding/tool/stop")
    time.sleep(2)
    print("Starting tool...")
    requests.post("http://127.0.0.1:3006/api/v1/seeding/tool/start", json={"platform": "facebook", "show_browser": False})
    print("Done restarting tool!")
except Exception as e:
    print("Error:", e)
