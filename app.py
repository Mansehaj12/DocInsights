import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

import gradio as gr
import uvicorn
from backend.main import app

# Ensure data and cache directories exist
os.makedirs("data/uploads", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Mount Gradio onto FastAPI so Hugging Face Spaces detects the Gradio SDK
demo = gr.mount_gradio_app(app, gr.Blocks(title="DocInsights"), path="/gradio")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
