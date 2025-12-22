# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install Chinese fonts for matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    fontconfig \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# Copy the requirements file into the container at /usr/src/app
COPY requirements.txt ./

# Install dependencies
# Configure pip to use a proxy if specified
ARG HTTP_PROXY
ARG HTTPS_PROXY
RUN if [ -n "$HTTP_PROXY" ] ; then pip config set global.proxy $HTTP_PROXY ; fi
RUN if [ -n "$HTTPS_PROXY" ] ; then pip config set global.proxy $HTTPS_PROXY ; fi
RUN pip install --no-cache-dir -r requirements.txt

# Clear matplotlib font cache so it will detect newly installed fonts on first run
RUN rm -rf /root/.cache/matplotlib /root/.matplotlib

# Copy the rest of the application's code into the container
COPY ./config ./config
COPY ./app ./app

# Run main.py when the container launches
# The host 0.0.0.0 makes the server accessible from outside the container
# --ws-max-size: Maximum WebSocket message size in bytes (default 16MB, set to 50MB)
# --timeout-keep-alive: Keep alive timeout in seconds (default 5)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--ws-max-size", "52428800", "--timeout-keep-alive", "75"]
