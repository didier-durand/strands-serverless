# docker run --rm -p 5000:5000 -e CHAINLIT_PORT=5000 -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY --name strands-chainlit strands-chainlit
FROM python:3.12-slim-bookworm
# streaming extension for Python lambda: https://github.com/awslabs/aws-lambda-web-adapter
# COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter

ARG CHAINLIT_SRC_DIR="/app"
ARG CHAINLIT_APP_ROOT="/tmp"
ARG CHAINLIT_HOST="0.0.0.0"
ARG CHAINLIT_PORT=8888


# Enforce direct send of streams to stderr, stdout without Python buffering
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR ${CHAINLIT_SRC_DIR}

# Copy your application's requirements and install them
COPY requirements.txt .

RUN pip install --upgrade --no-cache-dir pip  \
    && pip install --no-cache-dir -r /app/requirements.txt

# Copy your application code into the container
COPY src/constants.py src/
COPY src/utils.py src/
COPY src/strands_utils.py src/
COPY src/strands_chainlit/ src/strands_chainlit/

# to be able to use AWS services when container instance does not reside on AWS
ENV AWS_ACCESS_KEY_ID=""
ENV AWS_SECRET_ACCESS_KEY=""

# define a valid JWT token in CHAINLIT_AUTH_SECRET when running the app productively
ENV CHAINLIT_SRC_DIR=${CHAINLIT_SRC_DIR}
ENV CHAINLIT_APP_ROOT=${CHAINLIT_APP_ROOT}
ENV CHAINLIT_AUTH_SECRET="3q7.s1>zk*PRG46E,uip@03qOXY0CvCq.vuztOA7^-JuInv2l2hPv1TnfuV5bJzv"
ENV CHAINLIT_APP_ROOT=${CHAINLIT_APP_ROOT}
ENV CHAINLIT_HOST=${CHAINLIT_HOST}
ENV CHAINLIT_PORT=${CHAINLIT_PORT}

EXPOSE ${CHAINLIT_PORT}

CMD ["bash", "-c", "printenv && export PYTHONPATH=${CHAINLIT_SRC_DIR}/src && chainlit run --headless --host ${CHAINLIT_HOST} --port ${CHAINLIT_PORT} ${CHAINLIT_SRC_DIR}/src/strands_chainlit/strands_weather.py"]