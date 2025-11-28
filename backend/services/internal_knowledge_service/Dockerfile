# backend/services/internal_knowledge_service/Dockerfile
FROM python:3.11-slim

WORKDIR /usr/src/app

COPY requirements.txt ./
# Configure pip to use a proxy if specified
ARG HTTP_PROXY
ARG HTTPS_PROXY
RUN if [ -n "$HTTP_PROXY" ] ; then pip config set global.proxy $HTTP_PROXY ; fi
RUN if [ -n "$HTTPS_PROXY" ] ; then pip config set global.proxy $HTTPS_PROXY ; fi
RUN pip uninstall -y google-api-python-client google-auth-httplib2 google-auth google-api-core googleapis-common-protos && pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8009", "--reload"]
