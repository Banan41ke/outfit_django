"""Базовый класс для парсеров"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import json


@dataclass
class ParsedItem:
    """Распарсенный товар"""
    id: str
    name: str
    category: str  # tops, bottoms, shoes, accessories
    gender: str  # M, F, U
    price: float
    currency: str
    image_url: str
    product_url: str
    store: str
    color: Optional[str] = None
    sizes: Optional[list] = None
    description: Optional[str] = None


class BaseParser(ABC):
    """Базовый класс парсера"""

    STORE_NAME: str = ""
    BASE_URL: str = ""

    def __init__(self, output_dir: Path = Path("data/raw")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = None

    @abstractmethod
    async def parse_category(self, category: str, gender: str = None, pages: int = 3) -> List[ParsedItem]:
        """
        Парсит категорию товаров

        Args:
            category: Категория (tops, bottoms, shoes, accessories)
            gender: Фильтр по полу (M, F, U) или None для всех
            pages: Количество страниц для парсинга
        """
        pass

    @abstractmethod
    async def parse_item_detail(self, product_url: str) -> ParsedItem:
        """Парсит детальную страницу товара"""
        pass

    def save_to_json(self, items: List[ParsedItem], filename: str):
        """Сохраняет результаты в JSON"""
        data = [self._item_to_dict(item) for item in items]
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath

    def _item_to_dict(self, item: ParsedItem) -> dict:
        return {
            'id': item.id,
            'name': item.name,
            'category': item.category,
            'gender': item.gender,
            'price': item.price,
            'currency': item.currency,
            'image_url': item.image_url,
            'product_url': item.product_url,
            'store': item.store,
            'color': item.color,
            'sizes': item.sizes,
            'description': item.description,
        }

    async def __aenter__(self):
        import aiohttp
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()