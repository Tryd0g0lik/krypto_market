"""
cryptomarket/models/__init__.py
"""

from cryptomarket.models.model_abstract import Base
from cryptomarket.models.model_base import BaseModel

__all__ = ["Base", "BaseModel", "PriceTicker", "PersonModel"]

from cryptomarket.models.persons.model_person import PersonModel
from cryptomarket.models.schemes.model_prices import PriceTicker
