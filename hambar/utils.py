import time
from contextlib import contextmanager
import tempfile
from path import path


def get_result(job):
    while not job.is_finished:
        time.sleep(.5)
    if job.is_failed:
        raise RuntimeError("Job failed :(")
    return job.result


@contextmanager
def temp_dir():
    tmp = path(tempfile.mkdtemp())
    try:
        yield tmp
    finally:
        tmp.rmtree()
