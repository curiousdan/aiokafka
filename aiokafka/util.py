import os
import sys
import asyncio
from distutils.version import StrictVersion

from .structs import TopicPartition, OffsetAndMetadata

__all__ = ["ensure_future", "create_future", "PY_35"]


try:
    from asyncio import ensure_future
except ImportError:
    exec("from asyncio import async as ensure_future")


def create_future(loop):
    try:
        return loop.create_future()
    except AttributeError:
        return asyncio.Future(loop=loop)


def parse_kafka_version(api_version):
    version = StrictVersion(api_version).version
    if not (0, 9) <= version < (3, 0):
        raise ValueError(api_version)
    return version


@asyncio.coroutine
def wait_for_reponse_or_error(coro, error_tasks, *, shield=False, loop):
    """ Common pattern for Facade classes to run some coroutine but still proxy
    any other critical exception happening in background tasks.
    """
    data_task = ensure_future(coro, loop=loop)

    try:
        yield from asyncio.wait(
            [data_task] + error_tasks,
            return_when=asyncio.FIRST_COMPLETED,
            loop=loop)
    except asyncio.CancelledError:
        if not shield:
            data_task.cancel()
        raise

    # Check for errors in other tasks
    for error_task in error_tasks:
        if error_task.done():
            error_task.result()  # Raises set exception if any

    return (yield from data_task)


def commit_structure_validate(offsets):
    # validate `offsets` structure
    if not offsets or not isinstance(offsets, dict):
        raise ValueError(offsets)

    formatted_offsets = {}
    for tp, offset_and_metadata in offsets.items():
        if not isinstance(tp, TopicPartition):
            raise ValueError("Key should be TopicPartition instance")

        if isinstance(offset_and_metadata, int):
            offset, metadata = offset_and_metadata, ""
        else:
            try:
                offset, metadata = offset_and_metadata
            except Exception:
                raise ValueError(offsets)

            if not isinstance(metadata, str):
                raise ValueError("Metadata should be a string")

        formatted_offsets[tp] = OffsetAndMetadata(offset, metadata)
    return formatted_offsets


PY_341 = sys.version_info >= (3, 4, 1)
PY_35 = sys.version_info >= (3, 5)
PY_352 = sys.version_info >= (3, 5, 2)
PY_36 = sys.version_info >= (3, 6)
NO_EXTENSIONS = bool(os.environ.get('AIOKAFKA_NO_EXTENSIONS'))

INTEGER_MAX_VALUE = 2 ** 31 - 1
INTEGER_MIN_VALUE = - 2 ** 31
