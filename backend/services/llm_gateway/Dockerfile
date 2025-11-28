# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file
COPY requirements.txt ./

# Install dependencies
# Configure pip to use a proxy if specified
ARG HTTP_PROXY
ARG HTTPS_PROXY
RUN if [ -n "$HTTP_PROXY" ] ; then pip config set global.proxy $HTTP_PROXY ; fi
RUN if [ -n "$HTTPS_PROXY" ] ; then pip config set global.proxy $HTTPS_PROXY ; fi
RUN pip uninstall -y google-api-python-client google-auth-httplib2 google-auth google-api-core googleapis-common-protos && pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY ./app ./app

# Run the application
# The host 0.0.0.0 makes the server accessible from outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
