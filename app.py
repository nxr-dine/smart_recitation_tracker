import os
import re
import tempfile
from difflib import SequenceMatcher

import streamlit as st
import speech_recognition as sr
from pydub import AudioSegment
from pydub.utils import which as pydub_which
import io

# Simple translations (English + Arabic)
TRANSLATIONS = {
    'en': {
        'page_title': 'Smart Recitation Tracker',
        'header_sub': 'Upload audio (WAV or MP3) and compare it with the original verse — similarity, highlights and simple reports.',
        'diag_ffmpeg_found': 'ffmpeg found: {path}',
        'diag_ffmpeg_missing': 'ffmpeg not found. MP3 conversion may fail. Please install ffmpeg and add it to PATH.',
        'quick_install_tips': '**Quick install tips:**\n- Windows: download ffmpeg static build and add its `bin` folder to PATH.\n- Install optional TTS: `pip install gTTS`\n',
        'no_internal_sample': 'No internal sample audio found next to app.py (recitation.wav). You can add one for an automatic test.',
        'upload_label': 'Choose audio file (WAV or MP3)',
        'original_text_label': 'Enter the original verse text (Arabic)',
        'load_sample_verse': 'Load sample verse',
        'generate_sample_audio': 'Generate sample audio (TTS)',
        'normalize_ta': "Normalize 'ة' → 'ه' (normalization)",
        'use_normalized': 'Use normalized text for comparison',
        'analyze_button': 'Analyze Recitation',
        'please_upload': 'Please upload an audio file first.',
        'please_enter_original': 'Please enter the original verse text.',
        'results': 'Results',
        'recognized_label': 'Recognized text (speech-to-text):',
        'similarity_label': 'Similarity',
        'comparison_mode_caption': "Comparison mode: {mode} • Normalize 'ة'→'ه': {ta}",
        'original_diff_label': 'Original text (differences highlighted):',
        'recognized_diff_label': 'Recognized text (differences/extra highlighted):',
        'info_note': 'Note: some automatic normalizations were applied (remove diacritics and unify letters) to improve comparison.',
        'diagnostics': 'Diagnostics',
        'found_internal_sample': 'Found internal sample audio: {path}',
        'run_internal_stt': 'Run internal STT test',
        'running_stt': 'Running speech-to-text on internal sample...',
        'auto_stt_result': 'Auto STT result:',
        'gtts_not_available': 'gTTS is not available. Install it with pip install gTTS to generate sample audio.',
        'generated_sample_audio_at': 'Generated sample audio at {path}',
        'auto_fill_success': 'Original text area auto-filled with recognized text for quick comparison.',
        'generated_audio_not_understood': 'Generated audio could not be understood by STT.',
        'stt_request_error_after_generation': 'STT request error after generation: {e}',
        'transcribing': 'Transcribing audio...',
        'could_not_understand_audio': 'Could not understand the audio (no speech recognized).',
        'stt_request_error': 'STT request error: {e}',
        'report_original_label': 'Original (used for comparison):',
        'report_recognized_label': 'Recognized (used for comparison):',
        'report_similarity_label': 'Similarity:',
        'report_missing_label': 'Missing words (in original but not recognized):',
        'report_extra_label': 'Extra words (recognized but not in original):',
        'report_replaced_label': 'Replaced word pairs (original -> recognized):',
        'download_comparison': 'Download comparison report',
        'download_csv': 'Download CSV report',
        'missing_count': 'Missing: {n}',
        'extra_count': 'Extra: {n}',
        'replacements_count': 'Replacements: {n}',
    },
    'ar': {
        'page_title': 'متتبع دقة التلاوة',
        'header_sub': 'ارفع ملف صوتي (WAV أو MP3) وقارنه بالنص الأصلي — نسبة التشابه، تمييز الأخطاء وتقارير بسيطة.',
        'diag_ffmpeg_found': 'تم العثور على ffmpeg: {path}',
        'diag_ffmpeg_missing': 'لم يتم العثور على ffmpeg. قد يفشل تحويل MP3 → WAV. الرجاء تثبيت ffmpeg وإضافة مجلده إلى PATH.',
        'quick_install_tips': '**نصائح تثبيت سريعة:**\n- ويندوز: حمّل ffmpeg وأضف مجلد `bin` إلى PATH.\n- لتوليد الصوت (اختياري): `pip install gTTS`\n',
        'no_internal_sample': 'لم يتم العثور على ملف صوتي تجريبي بجانب app.py (recitation.wav). يمكنك إضافته لاختبار تلقائي.',
        'upload_label': 'اختر ملف صوتي (WAV أو MP3)',
        'original_text_label': 'أدخل نص الآية الأصلية (بالعربية)',
        'load_sample_verse': 'تحميل آية نموذجية',
        'generate_sample_audio': 'توليد عينة صوتية (TTS)',
        'normalize_ta': "طبيعة تحويل 'ة' → 'ه' (تطبيع)",
        'use_normalized': 'استخدم النص المطبع للمقارنة',
        'analyze_button': 'حلّل التلاوة',
        'please_upload': 'الرجاء رفع ملف صوتي أولاً.',
        'please_enter_original': 'الرجاء إدخال النص الأصلي للآية.',
        'results': 'النتائج',
        'recognized_label': 'النص المعترف به (تحويل الكلام إلى نص):',
        'similarity_label': 'نسبة التطابق',
        'comparison_mode_caption': 'وضع المقارنة: {mode} • تطبيع "ة"→"ه": {ta}',
        'original_diff_label': 'النص الأصلي (الاختلافات مُظللة):',
        'recognized_diff_label': 'النص المعترف به (الاختلافات/الإضافات مُظللة):',
        'info_note': 'ملاحظة: تم تطبيق بعض عمليات التطبيع التلقائية (إزالة التشكيل وتوحيد الحروف) لتحسين المقارنة.',
        'diagnostics': 'تشخيص النظام',
        'found_internal_sample': 'تم العثور على عينة صوتية داخلية: {path}',
        'run_internal_stt': 'تشغيل اختبار تحويل الكلام إلى نص',
        'running_stt': 'جارٍ تشغيل تحويل الكلام إلى نص على العينة الداخلية...',
        'auto_stt_result': 'نتيجة STT التلقائية:',
        'gtts_not_available': 'gTTS غير متوفر. ثبّته عبر pip install gTTS لتوليد الصوت.',
        'generated_sample_audio_at': 'تم توليد العينة الصوتية في {path}',
        'auto_fill_success': 'تمت تعبئة مربع النص الأصلي تلقائياً بالنص المعترف به للمقارنة السريعة.',
        'generated_audio_not_understood': 'لم يتمكن STT من فهم العينة المولدة.',
        'stt_request_error_after_generation': 'خطأ في STT بعد التوليد: {e}',
        'transcribing': 'جارٍ تفريغ الصوت إلى نص...',
        'could_not_understand_audio': 'لم أتمكن من فهم الصوت (لم يتم التعرف على كلام).',
        'stt_request_error': 'خطأ في طلب STT: {e}',
        'report_original_label': 'الأصلي (المستخدم للمقارنة):',
        'report_recognized_label': 'المعترف به (المستخدم للمقارنة):',
        'report_similarity_label': 'التشابه:',
        'report_missing_label': 'كلمات مفقودة (في الأصلي وغير موجودة في المعترف):',
        'report_extra_label': 'كلمات إضافية (في المعترف وغير في الأصلي):',
        'report_replaced_label': 'أزواج الكلمات المستبدلة (الأصلي -> المعترف):',
        'download_comparison': 'تحميل تقرير المقارنة',
        'download_csv': 'تحميل تقرير CSV',
        'missing_count': 'مفقود: {n}',
        'extra_count': 'إضافي: {n}',
        'replacements_count': 'استبدالات: {n}',
    }
}



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
            # highlight mismatches with a pastel pink (softer on the eyes)
            orig_html_parts.extend([f"<span style='color:var(--accent-pink)'>{w}</span>" for w in orig_words[i1:i2]])
            rec_html_parts.extend([f"<span style='color:var(--accent-pink)'>{w}</span>" for w in rec_words[j1:j2]])
        elif tag == "delete":
            # missing words in recitation: mark original red
            orig_html_parts.extend([f"<span style='color:var(--accent-pink)'>{w}</span>" for w in orig_words[i1:i2]])
        elif tag == "insert":
            # extra words in recitation: mark recognized red
            rec_html_parts.extend([f"<span style='color:var(--accent-pink)'>{w}</span>" for w in rec_words[j1:j2]])

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
    # language selector (English / Arabic)
    lang = st.selectbox("Language / اللغة", options=["en", "ar"], index=0, format_func=lambda x: ("English" if x == "en" else "العربية"))
    t = lambda key, **kw: TRANSLATIONS[lang][key].format(**kw)

    # Inject a small pastel UI theme (CSS)
    st.markdown(
        """
        <style>
        :root{
            --pastel-mint: #7EE7C6;
            --pastel-peach: #FFD3B6;
            --accent-pink: #FF6B6B;
            --pastel-blue: #60A5FA;
            --muted: #FFFFFF;
            --text-strong: #08263A;
            --muted-ink: #274358;
            --info-bg: #083B5B;
        }
        .custom-header {background:var(--pastel-blue); padding:14px 18px; border-radius:10px; color:var(--text-strong); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;}
        .custom-sub {color: var(--muted-ink); margin-top:6px}
        .pastel-button button { background: linear-gradient(90deg,var(--pastel-mint),var(--pastel-peach)); color: var(--text-strong); border: none; padding: 8px 12px; border-radius:8px }
        .pastel-card { background: var(--muted); padding: 12px; border-radius:10px; box-shadow: 0 6px 18px rgba(4,10,20,0.18) }
        button { border-radius: 8px }
        @media (prefers-color-scheme: dark) {
            :root{ --pastel-mint: #3ecf9f; --pastel-peach: #ffbfa0; --accent-pink: #ff8b8b; --pastel-blue: #3b82f6; --muted: rgba(255,255,255,0.02); --text-strong: #dff6ff; --muted-ink: #9fb4c6; --info-bg: #083b5b; }
            .custom-header { background: linear-gradient(90deg, rgba(59,130,246,0.08), rgba(62,207,159,0.06)); color: var(--text-strong) }
            .pastel-card { background: var(--muted); border: 1px solid rgba(255,255,255,0.04); box-shadow: none }
            .info-note { background: var(--info-bg); color: rgba(255,255,255,0.95); padding: 14px; border-radius: 8px }
            .custom-sub { color: var(--muted-ink) }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # header HTML (translation-aware)
    st.markdown(f"<div class='custom-header'><h1 style='margin:0;'>{t('page_title')}</h1><div class='custom-sub'>{t('header_sub')}</div></div>", unsafe_allow_html=True)

    # Diagnostics / troubleshooting helper
    with st.expander(t('diagnostics')):
        # check ffmpeg availability
        ffmpeg_path = pydub_which("ffmpeg")
        if ffmpeg_path:
            st.success(t('diag_ffmpeg_found', path=ffmpeg_path))
        else:
            st.error(t('diag_ffmpeg_missing'))
        st.markdown(t('quick_install_tips'), unsafe_allow_html=False)

        # check for an internal example WAV in the same directory as this script
        example_path = os.path.join(os.path.dirname(__file__), "recitation.wav")
        if os.path.exists(example_path):
            st.write(t('found_internal_sample', path=example_path))
            if st.button(t('run_internal_stt')):
                with st.spinner(t('running_stt')):
                    try:
                        sample_recognized = transcribe_audio(example_path)
                        st.markdown(f"**{t('auto_stt_result')}**")
                        st.write(sample_recognized)
                    except sr.UnknownValueError:
                        st.error("Could not understand the internal sample audio.")
                    except sr.RequestError as e:
                        st.error(f"STT request error: {e}")
        else:
            st.info(t('no_internal_sample'))

    uploaded_file = st.file_uploader(t('upload_label'), type=["wav", "mp3"] )
    # sample verse default (used by the quick-fill button)
    DEFAULT_SAMPLE_VERSE = "بismillah ar-rahman ar-rahim"

    # Text area for the original verse. Use a key so we can programmatically fill it.
    # set RTL direction when Arabic selected for better typing experience
    if lang == 'ar':
        original_text = st.text_area(t('original_text_label'), height=120, key="original_text")
    else:
        original_text = st.text_area(t('original_text_label'), height=120, key="original_text")

    # controls: quick-fill sample and normalization options
    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button(t('load_sample_verse')):
            st.session_state["original_text"] = DEFAULT_SAMPLE_VERSE
        if st.button(t('generate_sample_audio')):
            # Try to generate a simple TTS sample using gTTS. This is optional and requires gTTS and network.
            try:
                from gtts import gTTS
            except Exception as e:
                st.error(t('gtts_not_available'))
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
                        st.success(t('generated_sample_audio_at', path=out_wav))
                        # Automatically run STT on the generated sample and show result
                        try:
                            sample_recognized = transcribe_audio(out_wav)
                            st.markdown(f"**{t('auto_stt_result')}**")
                            st.write(sample_recognized)
                            # Auto-fill the original text area so user can immediately compare
                            try:
                                st.session_state["original_text"] = sample_recognized
                                st.success(t('auto_fill_success'))
                            except Exception:
                                # session_state may not be available in some older Streamlit versions
                                pass
                        except sr.UnknownValueError:
                            st.warning(t('generated_audio_not_understood'))
                        except sr.RequestError as e:
                            st.error(t('stt_request_error_after_generation', e=str(e)))
                    except Exception as e:
                        st.error(f"Failed to convert mp3 -> wav: {e}")
                except Exception as e:
                    st.error(f"Failed to generate TTS sample: {e}")
    with c2:
        normalize_ta = st.checkbox(t('normalize_ta'), value=True)
        use_normalized_for_comparison = st.checkbox(t('use_normalized'), value=True)

    st.markdown("---")

    if st.button(t('analyze_button')):
        if not uploaded_file:
            st.error(t('please_upload'))
            return
        if not original_text or original_text.strip() == "":
            st.error(t('please_enter_original'))
            return

        # save uploaded file to a temporary file
        suffix = ".wav" if uploaded_file.name.lower().endswith(".wav") else os.path.splitext(uploaded_file.name)[1]
        tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            tmp_in.write(uploaded_file.read())
            tmp_in.flush()
            tmp_in.close()

            # prepare a wav path (convert if necessary)
            wav_path = tmp_in.name
            if not wav_path.lower().endswith(".wav"):
                try:
                    wav_path = convert_to_wav(tmp_in.name)
                except Exception as e:
                    st.error(f"Failed to convert audio to WAV: {e}")
                    # fall back to the uploaded file path (may fail STT)
                    wav_path = tmp_in.name

            # run STT
            try:
                with st.spinner(t('transcribing')):
                    recognized = transcribe_audio(wav_path)
            except sr.UnknownValueError:
                st.warning(t('could_not_understand_audio'))
                recognized = ""
            except sr.RequestError as e:
                st.error(t('stt_request_error', e=str(e)))
                recognized = ""

            # apply normalization options
            orig_norm = normalize_arabic(original_text, normalize_ta)
            rec_norm = normalize_arabic(recognized, normalize_ta)

            # choose which texts to compare (normalized or raw)
            comp_orig = orig_norm if use_normalized_for_comparison else original_text
            comp_rec = rec_norm if use_normalized_for_comparison else recognized

            # similarity ratio (character-level)
            ratio = SequenceMatcher(None, comp_orig, comp_rec).ratio()
            percent = round(ratio * 100, 2)

            # Build highlighted versions (word-level) using the chosen comparison texts
            orig_html, rec_html = highlight_differences(comp_orig, comp_rec)

            # visual similarity bar (colored) using CSS variables (adapts to dark/light)
            color_css = "var(--pastel-mint)" if percent >= 80 else ("var(--pastel-peach)" if percent >= 50 else "var(--accent-pink)")
            bar_html = f"<div style='width:100%; background:var(--muted); border-radius:6px; height:18px;'>"
            bar_html += f"<div style='width:{percent}%; background:{color_css}; height:18px; border-radius:6px;'></div></div>"
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

            # Two-column results: left = highlighted texts, right = summary + downloads
            c_left, c_right = st.columns([3, 1])

            with c_right:
                st.markdown("<div class='pastel-card' style='text-align:center'>", unsafe_allow_html=True)
                st.markdown(f"<h2 style='margin:6px 0; color:var(--text-strong);'>{percent} %</h2>", unsafe_allow_html=True)
                st.markdown(f"<div style='color:var(--muted-ink); font-size:14px;'>{t('similarity_label')}</div>", unsafe_allow_html=True)
                st.markdown("<hr />", unsafe_allow_html=True)
                st.write(t('missing_count', n=len(diffs['missing'])))
                st.write(t('extra_count', n=len(diffs['extra'])))
                st.write(t('replacements_count', n=len(diffs['replaced'])))
                # downloads
                st.download_button(t('download_comparison'), data=report_text, file_name="comparison_report.txt", mime="text/plain")
                st.download_button(t('download_csv'), data=csv_data, file_name="comparison_report.csv", mime="text/csv")
                st.markdown("</div>", unsafe_allow_html=True)

            with c_left:
                st.subheader(t('results'))
                st.markdown(f"**{t('recognized_label')}** {recognized}")
                # show which comparison mode and normalization are used
                try:
                    mode_label = 'normalized' if use_normalized_for_comparison else 'raw'
                    ta_label = 'yes' if normalize_ta else 'no'
                    st.caption(t('comparison_mode_caption', mode=mode_label, ta=ta_label))
                except Exception:
                    # if the variables are not present for some reason, skip the caption
                    pass

                # show highlighted comparison (inside pastel cards)
                st.markdown(f"**{t('original_diff_label')}**")
                # keep RTL on the highlighted blocks when original language is Arabic
                dir_attr = 'rtl' if lang == 'ar' else 'ltr'
                st.markdown(f"<div class='pastel-card' dir='{dir_attr}'>{orig_html}</div>", unsafe_allow_html=True)
                st.markdown(f"**{t('recognized_diff_label')}**")
                st.markdown(f"<div class='pastel-card' dir='{dir_attr}'>{rec_html}</div>", unsafe_allow_html=True)

                # small note about normalization (custom-styled so we control dark-mode colors)
                st.markdown(
                    f"<div class='info-note'>{t('info_note')}</div>",
                    unsafe_allow_html=True,
                )

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
