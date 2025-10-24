import os
import re
import tempfile
from difflib import SequenceMatcher

import streamlit as st
import speech_recognition as sr
from pydub import AudioSegment
from pydub.utils import which as pydub_which
import io



def normalize_arabic(text: str, normalize_ta: bool = True) -> str:
    """Normalize Arabic text for better comparison:
    - Remove tashkeel (diacritics)
    - Normalize alef variations
    - Remove tatweel and punctuation
    - Collapse multiple spaces
    """
    # remove tashkeel and tatweel
    text = re.sub(r"[ًٌٍَُِّْـ]", "", text)
    # normalize alef variants
    text = re.sub(r"[إأآا]", "ا", text)
    text = re.sub(r"ى", "ي", text)
    text = re.sub(r"ؤ", "و", text)
    text = re.sub(r"ئ", "ي", text)
    # optional: normalize ta marbuta to heh (keeping can be better depending on needs)
    if normalize_ta:
        text = re.sub(r"ة", "ه", text)
    # remove punctuation (keep Arabic letters and numbers and spaces)
    text = re.sub(r"[^\w\s\u0600-\u06FF]", " ", text)
    # collapse spaces and strip
    text = re.sub(r"\s+", " ", text).strip()
    return text


def highlight_differences(orig: str, rec: str) -> tuple[str, str]:
    """Return HTML-marked original and recognized strings where differences are highlighted in red.

    We operate at word level using difflib.SequenceMatcher opcodes.
    Returns (orig_html, rec_html).
    """
    orig_words = orig.split()
    rec_words = rec.split()

    s = SequenceMatcher(None, orig_words, rec_words)

    orig_html_parts = []
    rec_html_parts = []

    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == "equal":
            # add words normally
            orig_html_parts.extend(orig_words[i1:i2])
            rec_html_parts.extend(rec_words[j1:j2])
        elif tag == "replace":
            # words differ: mark both sides in red
            orig_html_parts.extend([f"<span style='color:#b00020'>{w}</span>" for w in orig_words[i1:i2]])
            rec_html_parts.extend([f"<span style='color:#b00020'>{w}</span>" for w in rec_words[j1:j2]])
        elif tag == "delete":
            # missing words in recitation: mark original red
            orig_html_parts.extend([f"<span style='color:#b00020'>{w}</span>" for w in orig_words[i1:i2]])
        elif tag == "insert":
            # extra words in recitation: mark recognized red
            rec_html_parts.extend([f"<span style='color:#b00020'>{w}</span>" for w in rec_words[j1:j2]])

    orig_html = " ".join(orig_html_parts)
    rec_html = " ".join(rec_html_parts)
    # fallback: if empty, show original strings
    if not orig_html:
        orig_html = " ".join(orig_words)
    if not rec_html:
        rec_html = " ".join(rec_words)

    return orig_html, rec_html


def get_diff_words(orig: str, rec: str) -> dict:
    """Return lists of differing words: missing (in orig not in rec), extra (in rec not in orig), replaced pairs."""
    orig_words = orig.split()
    rec_words = rec.split()
    s = SequenceMatcher(None, orig_words, rec_words)
    missing = []
    extra = []
    replaced = []
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == 'replace':
            for o, r in zip(orig_words[i1:i2], rec_words[j1:j2]):
                replaced.append((o, r))
        elif tag == 'delete':
            missing.extend(orig_words[i1:i2])
        elif tag == 'insert':
            extra.extend(rec_words[j1:j2])
    return {'missing': missing, 'extra': extra, 'replaced': replaced}


def transcribe_audio(file_path: str) -> str:
    """Transcribe an audio file (wav) to Arabic text using Google's Web Speech API.

    The uploaded file may be mp3 or wav. If mp3, caller should convert to wav before calling.
    """
    r = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio = r.record(source)
    # use Google Web Speech API (no key required for small/demo use)
    return r.recognize_google(audio, language="ar-SA")


def convert_to_wav(input_path: str) -> str:
    """Convert input audio (mp3, etc.) to WAV using pydub. Returns path to WAV file.

    Requires ffmpeg in PATH (platform-level requirement).
    """
    sound = AudioSegment.from_file(input_path)
    tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp_wav_path = tmp_wav.name
    tmp_wav.close()
    sound.export(tmp_wav_path, format="wav")
    return tmp_wav_path


def main():
    """Main Streamlit app function.

    Simple interface to upload a recitation audio file, enter the original verse,
    and analyze the recitation. Shows the transcribed text, similarity percentage,
    and highlights differing/missing words in red.
    """
    st.set_page_config(page_title="Smart Recitation Tracker", layout="centered")
    st.title("Smart Recitation Tracker")
    st.write("Upload your recitation audio (WAV or MP3) and compare it with the original verse.")

    # Diagnostics / troubleshooting helper
    with st.expander("Diagnostics"):
        # check ffmpeg availability
        ffmpeg_path = pydub_which("ffmpeg")
        if ffmpeg_path:
            st.success(f"ffmpeg found: {ffmpeg_path}")
        else:
            st.error("ffmpeg not found. MP3 conversion may fail. Please install ffmpeg and add it to PATH.")
        st.markdown(
            "**Quick install tips:**\n- Windows: download ffmpeg static build and add its `bin` folder to PATH.\n- Install optional TTS: `pip install gTTS`\n",
            unsafe_allow_html=False,
        )

        # check for an internal example WAV in the same directory as this script
        example_path = os.path.join(os.path.dirname(__file__), "recitation.wav")
        if os.path.exists(example_path):
            st.write(f"Found internal sample audio: {example_path}")
            if st.button("Run internal STT test"):
                with st.spinner("Running speech-to-text on internal sample..."):
                    try:
                        sample_recognized = transcribe_audio(example_path)
                        st.markdown("**Recognized text:**")
                        st.write(sample_recognized)
                    except sr.UnknownValueError:
                        st.error("Could not understand the internal sample audio.")
                    except sr.RequestError as e:
                        st.error(f"STT request error: {e}")
        else:
            st.info("No internal sample audio found next to app.py (recitation.wav). You can add one for an automatic test.")

    uploaded_file = st.file_uploader("Choose audio file (WAV or MP3)", type=["wav", "mp3"] )
    # sample verse default (used by the quick-fill button)
    DEFAULT_SAMPLE_VERSE = "بismillah ar-rahman ar-rahim"

    # Text area for the original verse. Use a key so we can programmatically fill it.
    original_text = st.text_area("Enter the original verse text (Arabic)", height=120, key="original_text")

    # controls: quick-fill sample and normalization options
    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("Load sample verse"):
            st.session_state["original_text"] = DEFAULT_SAMPLE_VERSE
        if st.button("Generate sample audio (TTS)"):
            # Try to generate a simple TTS sample using gTTS. This is optional and requires gTTS and network.
            try:
                from gtts import gTTS
            except Exception as e:
                st.error("gTTS is not available. Install it with pip install gTTS to generate sample audio.")
            else:
                try:
                    tts = gTTS(text=DEFAULT_SAMPLE_VERSE, lang='ar')
                    mp3_buf = io.BytesIO()
                    tts.write_to_fp(mp3_buf)
                    mp3_buf.seek(0)
                    # save mp3 to disk then convert to wav using pydub if ffmpeg available
                    out_mp3 = os.path.join(os.path.dirname(__file__), 'recitation_sample.mp3')
                    with open(out_mp3, 'wb') as f:
                        f.write(mp3_buf.read())
                    # convert to wav
                    try:
                        sound = AudioSegment.from_file(out_mp3, format='mp3')
                        out_wav = os.path.join(os.path.dirname(__file__), 'recitation.wav')
                        sound.export(out_wav, format='wav')
                        st.success(f"Generated sample audio at {out_wav}")
                        # Automatically run STT on the generated sample and show result
                        try:
                            sample_recognized = transcribe_audio(out_wav)
                            st.markdown("**Auto STT result:**")
                            st.write(sample_recognized)
                            # Auto-fill the original text area so user can immediately compare
                            try:
                                st.session_state["original_text"] = sample_recognized
                                st.success("Original text area auto-filled with recognized text for quick comparison.")
                            except Exception:
                                # session_state may not be available in some older Streamlit versions
                                pass
                        except sr.UnknownValueError:
                            st.warning("Generated audio could not be understood by STT.")
                        except sr.RequestError as e:
                            st.error(f"STT request error after generation: {e}")
                    except Exception as e:
                        st.error(f"Failed to convert mp3 -> wav: {e}")
                except Exception as e:
                    st.error(f"Failed to generate TTS sample: {e}")
    with c2:
        normalize_ta = st.checkbox("Normalize 'ة' → 'ه' (normalization)", value=True)
        use_normalized_for_comparison = st.checkbox("Use normalized text for comparison", value=True)

        st.markdown("---")
        st.header("Live recitation (experimental)")
        st.write("Start a live recitation session using your browser microphone. This uses an external FastAPI + Vosk streaming server (must be running on port 8000).")

        session_id = st.text_input("Session ID (any short string)", value="live1")
        cols = st.columns([1, 1, 2])
        with cols[0]:
                st.button("Start live (see embedded panel below)")
        with cols[1]:
                st.button("Stop live")
        with cols[2]:
                if st.button("Import last live transcript"):
                        # fetch last transcript saved by streaming server
                        import requests

                        try:
                                r = requests.get(f"http://localhost:8000/transcript?session={session_id}", timeout=5)
                                if r.status_code == 200:
                                        data = r.json()
                                        st.success("Fetched live transcript")
                                        st.text_area("Live transcript (imported)", value=data.get("text", ""), height=160, key="live_imported")
                                else:
                                        st.error(f"Could not fetch transcript (status {r.status_code})")
                        except Exception as e:
                                st.error(f"Error contacting streaming server: {e}")

                # embedded client component: captures mic and shows live partial/final text
                live_html = """
<div>
    <p><b>Live recitation panel</b> — allow microphone access when prompted. Partial and final results will appear below.</p>
    <button id="start">Start</button>
    <button id="stop" disabled>Stop</button>
    <div style="margin-top:0.5rem; background:#f6f6f6; padding:0.5rem; border-radius:6px; min-height:3rem;">
        <div id="partial" style="color:#444"></div>
        <div id="final" style="color:#b00020; font-weight:600; margin-top:0.5rem"></div>
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
        // convert float32 -> 16-bit PCM
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
""".replace('{SESSION}', session_id)

                st.components.v1.html(live_html, height=300)

    if st.button("Analyze Recitation"):
        if not uploaded_file:
            st.error("Please upload an audio file first.")
            return
        if not original_text or original_text.strip() == "":
            st.error("Please enter the original verse text.")
            return

        # save uploaded file to a temporary file
        suffix = ".wav" if uploaded_file.name.lower().endswith(".wav") else os.path.splitext(uploaded_file.name)[1]
        tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            tmp_in.write(uploaded_file.read())
            tmp_in.flush()
        finally:
            tmp_in.close()

        try:
            # if mp3, convert to wav
            if tmp_in.name.lower().endswith(".mp3"):
                wav_path = convert_to_wav(tmp_in.name)
            else:
                # ensure wav
                wav_path = tmp_in.name

            with st.spinner("Converting audio to text — please wait..."):
                try:
                    recognized = transcribe_audio(wav_path)
                except sr.UnknownValueError:
                    st.error("Could not understand the audio. Please check recording quality and clarity.")
                    return
                except sr.RequestError as e:
                    st.error(f"An error occurred while contacting the speech recognition service: {e}")
                    return

            # normalize both texts for comparison (depending on the toggle)
            orig_norm = normalize_arabic(original_text, normalize_ta=normalize_ta)
            rec_norm = normalize_arabic(recognized, normalize_ta=normalize_ta)

            # choose which texts to compare (normalized or raw)
            comp_orig = orig_norm if use_normalized_for_comparison else original_text
            comp_rec = rec_norm if use_normalized_for_comparison else recognized

            # similarity ratio (character-level)
            ratio = SequenceMatcher(None, comp_orig, comp_rec).ratio()
            percent = round(ratio * 100, 2)

            # Build highlighted versions (word-level) using the chosen comparison texts
            orig_html, rec_html = highlight_differences(comp_orig, comp_rec)

            # visual similarity bar (colored) using simple inline HTML
            color = "#2ecc71" if percent >= 80 else ("#f1c40f" if percent >= 50 else "#e74c3c")
            bar_html = f"<div style='width:100%; background:#eee; border-radius:6px; height:18px;'>"
            bar_html += f"<div style='width:{percent}%; background:{color}; height:18px; border-radius:6px;'></div></div>"
            st.markdown(bar_html, unsafe_allow_html=True)

            # compute differing words for the report and display
            diffs = get_diff_words(comp_orig, comp_rec)

            # add a download button for a short text report
            report_lines = [
                f"Original (used for comparison): {comp_orig}",
                f"Recognized (used for comparison): {comp_rec}",
                f"Similarity: {percent} %",
                "",
                "Missing words (in original but not recognized):",
                ", ".join(diffs['missing']) or "None",
                "",
                "Extra words (recognized but not in original):",
                ", ".join(diffs['extra']) or "None",
                "",
                "Replaced word pairs (original -> recognized):",
            ]
            if diffs['replaced']:
                report_lines.extend([f"{o} -> {r}" for o, r in diffs['replaced']])
            else:
                report_lines.append("None")

            report_text = "\n".join(report_lines)
            st.download_button("Download comparison report", data=report_text, file_name="comparison_report.txt", mime="text/plain")
            # also offer CSV download for spreadsheet-friendly format
            import csv
            import io as _io

            csv_buf = _io.StringIO()
            writer = csv.writer(csv_buf)
            writer.writerow(["field", "value"])
            writer.writerow(["original_used", comp_orig])
            writer.writerow(["recognized_used", comp_rec])
            writer.writerow(["similarity_percent", percent])
            writer.writerow(["missing_words", ";".join(diffs['missing']) or "None"])
            writer.writerow(["extra_words", ";".join(diffs['extra']) or "None"])
            if diffs['replaced']:
                writer.writerow(["replaced_pairs", " | ".join([f"{o}->{r}" for o, r in diffs['replaced']])])
            else:
                writer.writerow(["replaced_pairs", "None"])
            csv_data = csv_buf.getvalue()
            st.download_button("Download CSV report", data=csv_data, file_name="comparison_report.csv", mime="text/csv")

            st.subheader("Results")
            st.markdown(f"**Recognized text (speech-to-text):** {recognized}")
            st.markdown(f"**Similarity:** {percent} %")
            # show which comparison mode and normalization are used
            try:
                mode_label = 'normalized' if use_normalized_for_comparison else 'raw'
                ta_label = 'yes' if normalize_ta else 'no'
                st.caption(f"Comparison mode: {mode_label} • Normalize 'ة'→'ه': {ta_label}")
            except Exception:
                # if the variables are not present for some reason, skip the caption
                pass

            # show highlighted comparison
            st.markdown("**Original text (differences highlighted in red):**")
            st.markdown(orig_html, unsafe_allow_html=True)
            st.markdown("**Recognized text (differences/extra highlighted in red):**")
            st.markdown(rec_html, unsafe_allow_html=True)

            # small note about normalization
            st.info("Note: some automatic normalizations were applied (remove diacritics and unify letters) to improve comparison.")

        finally:
            # clean temporary files
            try:
                os.remove(tmp_in.name)
            except Exception:
                pass
            try:
                if 'wav_path' in locals() and wav_path != tmp_in.name:
                    os.remove(wav_path)
            except Exception:
                pass


if __name__ == "__main__":
    main()
