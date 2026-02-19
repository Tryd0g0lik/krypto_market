"""
cryptomarket/project/__init__.py
"""

__all__ = ["celery_deribit", "TaskRegisteryType"]

from cryptomarket.project.celery_ import celery_deribit
from cryptomarket.project.task_registeration import TaskRegisteryType
