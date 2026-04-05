"""Утилиты для работы с цветом"""
import numpy as np
from typing import Tuple, List
from .config import NEUTRAL_COLORS


def color_distance(c1: Tuple[int, int, int], c2: Tuple[int, int, int]) -> float:
    """Евклидово расстояние между цветами в RGB"""
    return np.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


def is_neutral(color: Tuple[int, int, int], threshold: int = 30) -> bool:
    """Проверяет, является ли цвет нейтральным (универсальным)"""
    for neutral in NEUTRAL_COLORS:
        if color_distance(color, neutral) < threshold:
            return True
    return False


def colors_compatible(
        color1: Tuple[int, int, int],
        color2: Tuple[int, int, int],
        complementary_threshold: int = 100
) -> bool:
    """
    Простая проверка совместимости цветов:
    1. Если один из них нейтральный — совместимы
    2. Если расстояние в цветовом пространстве > threshold (контраст)
    3. Или < 50 (монохром)
    """
    # Нейтральные цвета совместимы со всем
    if is_neutral(color1) or is_neutral(color2):
        return True

    dist = color_distance(color1, color2)

    # Монохром (похожие цвета) или контраст
    return dist < 80 or dist > 150