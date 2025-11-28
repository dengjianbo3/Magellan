# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container at /usr/src/app
COPY requirements.txt ./

# Install dependencies
# Configure pip to use a proxy if specified
ARG HTTP_PROXY
ARG HTTPS_PROXY
RUN if [ -n "$HTTP_PROXY" ] ; then pip config set global.proxy $HTTP_PROXY ; fi
RUN if [ -n "$HTTPS_PROXY" ] ; then pip config set global.proxy $HTTPS_PROXY ; fi
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY ./app ./app

# Run main.py when the container launches
# The host 0.0.0.0 makes the server accessible from outside the container
# --ws-max-size: Maximum WebSocket message size in bytes (default 16MB, set to 50MB)
# --timeout-keep-alive: Keep alive timeout in seconds (default 5)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--ws-max-size", "52428800", "--timeout-keep-alive", "75"]
