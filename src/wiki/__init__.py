"""
Oh My Coder Wiki - projedokumantasyonotomatikolustur

kullan AST ayristir Python kod, otomatikolusturyapiprojedokumantasyon. 
"""

from .generator import WikiGenerator
from .parser import PythonParser

__all__ = ["PythonParser", "WikiGenerator"]
