import os
import sys
from pathlib import Path

PYTHON_VERSION = str(sys.version_info.major) + "." + str(sys.version_info.minor)

PROJECT_NAME = "strands"

SRC_PREFIX = "src"

ROOT_PATH = Path(__file__).parent.parent
SRC_PATH = os.path.join(ROOT_PATH, SRC_PREFIX)
MEDIA_PATH = os.path.join(ROOT_PATH, "media")
TMP_PATH = os.path.join(ROOT_PATH, "tmp")

STRANDS_BUCKET_NAME = f"didier-durand-{PROJECT_NAME}"
STRANDS_LAYER_ZIP = f"{PROJECT_NAME}-layer.zip"
STRANDS_CODE_ZIP = f"{PROJECT_NAME}-code.zip"

STRANDS_HTTP_HOST = "0.0.0.0"
STRANDS_HTTP_PORT = 8888

CHAINLIT_APP_ROOT = "/tmp"
CHAINLIT_URL_PATH = "/chainlit/"
CHAINLIT_AUTH_SECRET = "3q7.s1>zk*PRG46E,uip@03qOXY0CvCq.vuztOA7^-JuInv2l2hPv1TnfuV5bJzv"

REQUEST = "request"
