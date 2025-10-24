import os
import json
import asyncio
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
import uvicorn

try:
    from vosk import Model, KaldiRecognizer
except Exception:
    Model = None  # will raise later if used

app = FastAPI()

# simple in-memory store for final transcripts by session id
transcripts: Dict[str, str] = {}


def get_vosk_model(model_path: str = None):
    if Model is None:
        raise RuntimeError("vosk not installed. Install with `pip install vosk` and add a model.`")
    model_path = model_path or os.environ.get("VOSK_MODEL_PATH", "./model")
    if not os.path.exists(model_path):
        raise RuntimeError(f"Vosk model not found at {model_path}. Please download a model and set VOSK_MODEL_PATH.")
    return Model(model_path)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session = None
    model = None
    recognizer = None
    try:
        # expect first message to be a small JSON with sampleRate and session id
        init_data = await websocket.receive_text()
        try:
            info = json.loads(init_data)
            sample_rate = int(info.get("sampleRate", 16000))
            session = info.get("session") or "default"
        except Exception:
            sample_rate = 16000
            session = "default"

        # load model lazily
        try:
            model = get_vosk_model()
            recognizer = KaldiRecognizer(model, sample_rate)
        except Exception as e:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
            await websocket.close()
            return

        await websocket.send_text(json.dumps({"type": "ready", "session": session}))

        while True:
            msg = await websocket.receive()
            if 'bytes' in msg:
                data = msg['bytes']
                if recognizer.AcceptWaveform(data):
                    res = recognizer.Result()
                    await websocket.send_text(json.dumps({"type": "final", "text": json.loads(res).get("text", "")}))
                    # store final
                    transcripts[session] = json.loads(res).get("text", "")
                else:
                    pres = recognizer.PartialResult()
                    await websocket.send_text(json.dumps({"type": "partial", "text": json.loads(pres).get("partial", "")}))
            else:
                # text messages (control)
                text = msg.get('text')
                if text is None:
                    continue
                if text == "__close__":
                    break
                # ignore other control texts

    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@app.post("/submit_transcript")
async def submit_transcript(req: Request):
    body = await req.json()
    session = body.get("session", "default")
    text = body.get("text", "")
    transcripts[session] = text
    return JSONResponse({"ok": True, "session": session})


@app.get("/transcript")
async def get_transcript(session: str = "default"):
    return JSONResponse({"session": session, "text": transcripts.get(session, "")})


if __name__ == "__main__":
    # run with: python streaming_server.py
    port = int(os.environ.get("STREAM_SERVER_PORT", 8000))
    uvicorn.run("streaming_server:app", host="0.0.0.0", port=port, reload=False)
