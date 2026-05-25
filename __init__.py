"""
Plugin InkyPi pour afficher le saint du jour depuis Nominis.
"""

from .saint_du_jour import SaintDuJour

__all__ = ["SaintDuJour"]
__plugin__ = SaintDuJour