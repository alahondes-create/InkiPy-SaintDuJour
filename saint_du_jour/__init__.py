"""
Plugin InkyPi pour afficher le saint du jour depuis Nominis.
"""

from .saint_du_jour import saint_du_jour

__all__ = ["saint_du_jour"]
__plugin__ = saint_du_jour