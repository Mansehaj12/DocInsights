import os
import sys
import subprocess
import time
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

import spaces
import gradio as gr
import uvicorn
from backend.main import app

# Ensure data and cache directories exist
os.makedirs("data/uploads", exist_ok=True)
os.makedirs("data", exist_ok=True)

# ZeroGPU requires a decorated function linked to a Gradio event
@spaces.GPU
def gpu_inference_bridge(prompt: str) -> str:
    return prompt

with gr.Blocks(title="DocInsights") as blocks:
    t = gr.Textbox(visible=False)
    b = gr.Button(visible=False)
    b.click(fn=gpu_inference_bridge, inputs=t, outputs=t)

demo = gr.mount_gradio_app(app, blocks, path="/gradio")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    
    # Diagnostics & Stale Process Cleanup
    print("=== ENVIRONMENT & PORT DIAGNOSTICS ===")
    try:
        ps_out = subprocess.run(["ps", "aux"], capture_output=True, text=True).stdout
        print("Active processes:\n", ps_out)
    except Exception as e:
        print("ps aux error:", e)

    try:
        fuser_out = subprocess.run(["fuser", f"{port}/tcp"], capture_output=True, text=True).stdout
        print(f"PIDs on port {port}: {fuser_out}")
        pids = [p for p in fuser_out.strip().split() if p and p != str(os.getpid())]
        for pid in pids:
            print(f"Terminating lingering process {pid} on port {port}")
            subprocess.run(["kill", "-9", pid])
        if pids:
            time.sleep(1)
    except Exception as e:
        print("fuser cleanup error:", e)

    print(f"Starting Uvicorn on 0.0.0.0:{port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
