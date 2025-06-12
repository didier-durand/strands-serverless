import asyncio
import functools
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from pathlib import Path
import contextlib

import boto3
from starlette.requests import Request


def check_response(resp: dict, http_status_code=200) -> bool:
    assert (resp['ResponseMetadata']['HTTPStatusCode']
            == http_status_code), ("unexpected HTTP status code: "
                                   + str(http_status_code)
                                   + " <> " +
                                   str(resp['ResponseMetadata']['HTTPStatusCode']))
    return True


def exec_os_command(command: list[str] | str = None,
                    check: bool = False,
                    shell: bool = False,
                    debug: bool = False) \
        -> tuple[Exception | None, int | None, str | None, str | None]:
    if isinstance(command, str):
        with_quote = False
        if "'" in command:
            with_quote = True
        command = command.split(" ")
        if with_quote:
            adapted = []
            concat = ""
            for chunk in command:
                if chunk.startswith("'"):
                    concat = chunk[1:]
                elif chunk.endswith("'"):
                    concat += " " + chunk[:-1]
                    adapted.append(concat)
                    concat = ""
                else:
                    if concat == "":
                        adapted.append(chunk)
                    else:
                        concat += " " + chunk
            command = adapted
    if debug:
        print("\nexec_os_command:", " ".join(command))
    try:
        process: subprocess.CompletedProcess = subprocess.run(command,
                                                              stdout=subprocess.PIPE,
                                                              stderr=subprocess.PIPE,
                                                              shell=shell,
                                                              text=True,
                                                              check=check)
    except Exception as exception:  # noqa pylint: disable=W0718
        return exception, None, None, None
    return None, process.returncode, process.stdout, process.stderr


def copy_from_disk_to_s3(bucket_name: str, src_paths: list[Path] = None, dest_folder="") -> list[str] | None:
    file_paths: list[str] = list[str]()
    for src_path in src_paths:
        assert src_path.exists(), "file to upload to S3 does not exist:" + str(src_path)
        obj_key = dest_folder + "/" + os.path.basename(src_path)
        boto3.resource("s3").Bucket(bucket_name).upload_file(str(src_path), obj_key)
        file_paths.append(obj_key)
    if len(file_paths) > 0:
        return file_paths
    return None


def list_lambdas(name_filter: str = "") -> list[dict] | dict | None:
    response = boto3.client("lambda").list_functions()
    check_response(response)
    if name_filter != "":
        functions: list[dict] = []
        for function in response["Functions"]:
            if name_filter in function["FunctionName"]:
                functions.append(function)
        return functions
    return response["Functions"]


def to_async(fn):
    """
    turns a sync function to async function using threads
    """
    pool = ThreadPoolExecutor()

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        future = pool.submit(fn, *args, **kwargs)
        return asyncio.wrap_future(future)  # make it awaitable

    return wrapper


# see https://stackoverflow.com/questions/5136611/capture-stdout-from-a-script
@contextlib.contextmanager
def out_capture():
    old_out, old_err = sys.stdout, sys.stderr
    try:
        out = [StringIO(), StringIO()]
        sys.stdout, sys.stderr = out
        yield out
    finally:
        sys.stdout, sys.stderr = old_out, old_err
        out[0] = out[0].getvalue()
        out[1] = out[1].getvalue()


def is_lambda() -> bool:
    if len(os.getenv("AWS_LAMBDA_FUNCTION_NAME")) > 0:
        return True
    return False

def get_lambda_url(name_filter: str = "") -> str | None:
    lambda_functions = list_lambdas(name_filter=name_filter)
    assert len(lambda_functions) == 1
    lambda_function = lambda_functions[0]
    assert isinstance(lambda_function, dict)
    response = boto3.client("lambda").get_function_url_config(FunctionName=lambda_function["FunctionName"])
    check_response(response)
    lambda_url = response['FunctionUrl']
    if lambda_url.endswith("/"):
        lambda_url = lambda_url[:-1]
    return lambda_url

def on_github() -> bool:
    if (os.getenv("GITHUB_JOB") is not None
            and len(os.getenv("GITHUB_JOB")) > 0
            and os.getenv("GITHUB_SHA") is not None
            and len(os.getenv("GITHUB_SHA")) > 0):
        return True
    return False


def request_as_dict(request: Request) -> dict:
    request_dict = {}
    for k, v in request.items():
        if v is None:
            request_dict[k] = "None"
        elif isinstance(v, str):
            request_dict[k] = v
        elif isinstance(v, bytes):
            request_dict[k] = v.decode("utf-8")
        elif isinstance(v, (dict, list)):
            request_dict[k] = v
        else:
            request_dict[k] = str(type(v))
    return request_dict
