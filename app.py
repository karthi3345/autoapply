import os
import shutil
import asyncio
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pypdf import PdfReader
from engine.runner import RealApplicationRunner as ApplicationRunner

app = FastAPI(title="AutoApply AI Platform")

os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Active live websocket connections
connected_websockets: List[WebSocket] = []
application_logs = []
current_runner: Optional[ApplicationRunner] = None
parsed_resume_data = {
    "filename": "",
    "skills": [],
    "text_sample": ""
}

async def notify_clients(data: dict):
    application_logs.insert(0, data)
    disconnected = []
    for ws in connected_websockets:
        try:
            await ws.send_json(data)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in connected_websockets:
            connected_websockets.remove(ws)

def sync_log_callback(entry: dict):
    # bridge synchronous runner callback to event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(notify_clients(entry))
        else:
            loop.run_until_complete(notify_clients(entry))
    except Exception:
        pass

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    # Send historical logs immediately
    await websocket.send_json({"type": "history", "logs": application_logs})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)

@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    global parsed_resume_data
    file_path = os.path.join("uploads", file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    extracted_text = ""
    skills = []
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            extracted_text += (page.extract_text() or "") + "\n"

        # Basic keyword detection
        common_keywords = ["Python", "Java", "JavaScript", "React", "Node.js", "FastAPI", "SQL", "Docker", "AWS", "Git", "Machine Learning", "Data Analysis", "HTML", "CSS", "TypeScript"]
        skills = [kw for kw in common_keywords if kw.lower() in extracted_text.lower()]
    except Exception as e:
        extracted_text = f"Error reading PDF content: {str(e)}"

    parsed_resume_data = {
        "filename": file.filename,
        "path": file_path,
        "skills": skills,
        "text_sample": extracted_text[:500]
    }

    return JSONResponse(content={"status": "success", "data": parsed_resume_data})

@app.post("/api/start-bot")
async def start_bot(
    titles: str = Form(...),
    location: str = Form("India"),
    platforms: str = Form("indeed,linkedin,naukri"),
    max_jobs: int = Form(5)
):
    global current_runner
    if current_runner and current_runner.is_running:
        return JSONResponse(status_code=400, content={"error": "Bot is already actively running!"})

    title_list = [t.strip() for t in titles.split(",") if t.strip()]
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()]

    resume_path = parsed_resume_data.get("path", "")
    current_runner = ApplicationRunner(log_callback=sync_log_callback)

    preferences = {
        "job_titles": title_list,
        "location": location,
        "platforms": platform_list,
        "max_jobs_per_platform": max_jobs
    }

    asyncio.create_task(current_runner.run(preferences, resume_path))
    return JSONResponse(content={"status": "started", "preferences": preferences})

@app.post("/api/stop-bot")
async def stop_bot():
    global current_runner
    if current_runner:
        current_runner.stop()
        return JSONResponse(content={"status": "stopped"})
    return JSONResponse(content={"status": "not_running"})

@app.get("/api/status")
async def get_status():
    return {
        "is_running": current_runner.is_running if current_runner else False,
        "resume": parsed_resume_data,
        "total_applications": len([l for l in application_logs if l.get("status") == "Applied"]),
        "logs_count": len(application_logs)
    }

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
