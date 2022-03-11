# noinspection PyUnresolvedReferences
from celery import shared_task

from unittest.mock import patch


def mock_signature(**kwargs):
    return {}


def mocked_shared_task(*_decorator_args, **_decorator_kwargs):
    def mocked_shared_decorator(func):
        func.signature = func.si = func.s = mock_signature
        return func

    return mocked_shared_decorator


patch('celery.shared_task', mocked_shared_task).start()
