import os
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, repo_root)

try:
    from app import transcribe_audio, normalize_arabic
except Exception as e:
    print("Failed to import from app.py:", e)
    raise


def main():
    wav_path = os.path.join(repo_root, "recitation.wav")
    if not os.path.exists(wav_path):
        print(f"recitation.wav not found at: {wav_path}")
        return 2

    print("Transcribing:", wav_path)
    try:
        text = transcribe_audio(wav_path)
    except Exception as exc:
        print("Transcription failed:", exc)
        return 3

    print("\n--- Raw recognized text ---")
    print(text or "(empty)")

    norm = normalize_arabic(text or "")
    print("\n--- Normalized text ---")
    print(norm or "(empty)")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
