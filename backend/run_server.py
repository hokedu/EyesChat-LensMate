import subprocess, sys, os

os.chdir(r"C:\Users\hoked\Documents\New project\eyeschat-lensmate\backend")

# Kill any existing on port 8001
subprocess.run(["netstat","-ano"], capture_output=True)

print("Starting EyesChat-LensMate on http://127.0.0.1:8001")
print("Open http://127.0.0.1:8001 in your browser")
print("Press Ctrl+C to stop")
sys.stdout.flush()

import uvicorn
uvicorn.run(
    "app.main:app",
    host="0.0.0.0",
    port=8001,
    log_level="info",
    reload=False,
)
