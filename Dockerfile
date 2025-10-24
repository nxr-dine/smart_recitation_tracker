FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install ffmpeg for pydub and the system basics. Also install libsndfile (required by Vosk)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates curl libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for running the app
ARG APP_USER=streamlit
ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd --gid ${APP_GID} ${APP_USER} \
    && useradd --uid ${APP_UID} --gid ${APP_GID} --create-home --home-dir /home/${APP_USER} --shell /bin/bash ${APP_USER}

WORKDIR /app

# Copy only requirements first for better caching
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy the application and ensure permissions for the non-root user
COPY . .
RUN chown -R ${APP_USER}:${APP_USER} /app

USER ${APP_USER}

EXPOSE 8501
EXPOSE 8000

# Run Streamlit on 0.0.0.0 so it is reachable from other containers
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0", "--server.headless", "true"]
