# Smart Recitation Tracker

![CI](https://github.com/nxr-dine/smart_recitation_tracker/actions/workflows/ci.yml/badge.svg)

## Project description

A simple Streamlit application to check the accuracy of a Quran recitation. The user uploads an audio file of their recitation and provides the reference verse text. The app transcribes the audio (speech-to-text), compares the transcribed text to the original verse, and shows a similarity percentage as well as words that are different or missing.

## Requirements

- Python 3.8 or newer
- streamlit
- SpeechRecognition
- pydub
- ffmpeg (system-level dependency required by pydub to handle MP3 conversion)

## Installation

1. (Optional) Create and activate a virtual environment.
2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. If you want MP3 support, install `ffmpeg` and make sure it is on your PATH.

## Quick Windows ffmpeg install

- Download a static build from https://www.gyan.dev/ffmpeg/builds/ or https://ffmpeg.org/download.html
- Extract and add the `bin` folder to your PATH (Control Panel → System → Advanced system settings → Environment Variables → Path).

## Optional TTS dependency

If you want the app to generate a test audio sample via text-to-speech (gTTS), install:

```bash
pip install gTTS
```

## Development and running tests

For development and running tests locally, install the dev dependencies (this keeps test-only packages out of production installs):

```bash
pip install -r dev-requirements.txt
```

Then run the test suite from the project root:

```bash
pytest -q
```

## CI

The project includes a simple GitHub Actions workflow that will run the tests on push/PR. See `.github/workflows/ci.yml`.

## Pre-commit hooks (recommended)

This repo includes a `.pre-commit-config.yaml` to run formatting and linting hooks (Black, Ruff, isort, and common hygiene hooks).

To set up pre-commit locally:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

This will automatically format and lint files before commits.

## Run the app

From the project directory run:

```bash
streamlit run app.py
```

## Docker / docker-compose (optional)

If you prefer to run the app in Docker, a simple Dockerfile and a docker-compose setup are included. The compose stack runs the Streamlit app and an nginx container as a reverse proxy/landing page.

Build and start the stack:

```bash
cd I:/smart_recitation_tracker
docker compose build
docker compose up -d
```

The Streamlit app will be proxied by nginx and reachable at:

- http://localhost (nginx proxy) or
- http://localhost:8501 (direct Streamlit)

Notes:

- The Docker image installs ffmpeg in the container so pydub can perform conversions.
- If you change dependencies, rebuild the image.

## Docker health & build tips

- A `.dockerignore` file is included to keep the Docker build context small and avoid copying the virtualenv or other local artifacts into the image.
- The `app` service in `docker-compose.yml` has a healthcheck that queries the Streamlit root URL. Docker Compose will report when the app becomes healthy; nginx depends on the app but may still start earlier — if you depend on strict ordering in production, consider orchestrators with service health awareness.

## Secrets

If you store secrets for the app, do not commit them. Use `.env` files or your orchestrator's secret mechanism. `.gitignore` excludes common secret filenames and `.streamlit/secrets.toml`.

## CI

A GitHub Actions workflow is included (`.github/workflows/ci-fixed.yml`) which runs tests, basic lint checks, and builds the Docker image. There's also an original `ci.yml` in the repo; if you prefer the fixed workflow, consider removing or renaming the old one to avoid duplicate triggers.

## Streamlit telemetry

This repository includes a project-level Streamlit config that disables anonymous usage telemetry. The file is located at `.streamlit/config.toml` and contains:

```
[browser]
gatherUsageStats = false
```

This keeps CI logs quieter and ensures the app won't send anonymous usage stats from development or CI environments. If you prefer local-only control, remove the file and create the same file under your user profile (`%USERPROFILE%/.streamlit/config.toml`).

## Usage

- Upload a WAV or MP3 audio file containing your Quran recitation.
- Paste the original verse text (in Arabic) into the text area.
- Click the "Analyze Recitation" button.
- The app will display:
  - Recognized text (speech-to-text output)
  - Similarity percentage
  - Words that differ or are missing highlighted in red

## Notes and limitations

- The app uses the Google Web Speech API via the `SpeechRecognition` library with `language="ar-SA"`. This is suitable for small/demo uses but may not be ideal for accurate Quranic recitation recognition.
- For comparison, the app applies a simple Arabic normalization (`normalize_arabic`) and uses `difflib.SequenceMatcher` for similarity and difference highlighting. You can tune normalization rules to your needs.
- For better accuracy on Quran recitation specifically, consider using a specialized STT model trained on Quranic audio or a paid speech-to-text service.

## License

This is a small educational project.
