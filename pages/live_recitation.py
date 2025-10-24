import streamlit as st
import requests
import os

st.set_page_config(page_title="Live Recitation", layout="centered")
st.title("Live Recitation (experimental)")
st.write("This page captures microphone audio in the browser and streams to the FastAPI+Vosk server (must be running on port 8000).")

session_id = st.text_input("Session ID (any short string)", value="live1")
cols = st.columns([1, 1, 2])
with cols[0]:
    st.button("Start live (see embedded panel below)")
with cols[1]:
    st.button("Stop live")
with cols[2]:
    if st.button("Import last live transcript"):
        try:
            r = requests.get(f"http://localhost:8000/transcript?session={session_id}", timeout=5)
            if r.status_code == 200:
                data = r.json()
                st.success("Fetched live transcript")
                st.text_area("Live transcript (imported)", value=data.get("text", ""), height=200, key="live_imported")
            else:
                st.error(f"Could not fetch transcript (status {r.status_code})")
        except Exception as e:
            st.error(f"Error contacting streaming server: {e}")

# Embedded live client HTML/JS (identical behavior as previous in-app panel)
live_html = '''
<div>
    <p><b>Live recitation panel</b> — allow microphone access when prompted. Partial and final results will appear below.</p>
    <button id="start">Start</button>
    <button id="stop" disabled>Stop</button>
    <div style="margin-top:0.5rem; background:#FBFBFB; padding:0.5rem; border-radius:6px; min-height:3rem;">
        <div id="partial" style="color:#274358"></div>
    <div id="final" style="color:#FFAAA5; font-weight:600; margin-top:0.5rem"></div>
    </div>
</div>
<script>
const session = "{SESSION}";
const wsUrl = (location.hostname === 'localhost' || location.hostname === '127.0.0.1') ? 'ws://'+location.hostname+':8000/ws' : 'ws://'+location.hostname+':8000/ws';
let ws = null;
let audioContext, processor, source;

function floatTo16BitPCM(float32Array) {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    let offset = 0;
    for (let i = 0; i < float32Array.length; i++, offset += 2) {
        let s = Math.max(-1, Math.min(1, float32Array[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    return view;
}

async function startStream(){
    ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';
    ws.onopen = ()=>{ console.log('ws open'); ws.send(JSON.stringify({sampleRate:16000, session: session})); }
    ws.onmessage = (ev)=>{
        try{ const obj = JSON.parse(ev.data); if(obj.type==='partial'){ document.getElementById('partial').innerText = obj.text; } else if(obj.type==='final'){ document.getElementById('final').innerText = obj.text; } }
        catch(e){ console.log('ws msg parse', e); }
    }

    audioContext = new (window.AudioContext || window.webkitAudioContext)({sampleRate:16000});
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    source = audioContext.createMediaStreamSource(stream);
    processor = audioContext.createScriptProcessor(4096, 1, 1);
    source.connect(processor);
    processor.connect(audioContext.destination);
    processor.onaudioprocess = function(e){
        const input = e.inputBuffer.getChannelData(0);
        const pcmView = floatTo16BitPCM(input);
        try{ ws.send(pcmView.buffer); }catch(err){ console.warn('ws send err', err); }
    }
}

document.getElementById('start').addEventListener('click', async ()=>{
    document.getElementById('start').disabled = true;
    document.getElementById('stop').disabled = false;
    try{ await startStream(); } catch(e){ alert('Could not start microphone capture: '+e); document.getElementById('start').disabled=false; document.getElementById('stop').disabled=true; }
});

document.getElementById('stop').addEventListener('click', ()=>{
    document.getElementById('start').disabled = false;
    document.getElementById('stop').disabled = true;
    try{ if(processor) processor.disconnect(); if(source) source.disconnect(); if(audioContext) audioContext.close(); if(ws){ ws.send('__close__'); ws.close(); } } catch(e){ console.warn(e); }
});
</script>
'''

# replace session placeholder with the current session id
try:
    html = live_html.replace('{SESSION}', session_id)
except Exception:
    html = live_html.replace('{SESSION}', 'live1')

st.components.v1.html(html, height=360)
