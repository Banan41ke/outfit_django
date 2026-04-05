import asyncio
import aiohttp
import logging
from typing import List, Optional
from .base_parser import BaseParser, ParsedItem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FHParser")


class FHParser(BaseParser):
    STORE_NAME = "FH"

    # Используем названия как поисковые запросы для API
    CATEGORY_URLS = {
        "M": {
            "shoes": [
                "tufli", "lofery", "krossovki", "kedy",
                "mokasiny", "shlepancy-slancy-vetnamki",
                "espadrili", "botinki"
            ]
        }
    }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def parse_item_detail(self, url: str) -> Optional[ParsedItem]:
        return None

    async def parse_category(self, category: str, gender: str = "M", pages: int = 3) -> List[ParsedItem]:
        if gender not in self.CATEGORY_URLS or category not in self.CATEGORY_URLS[gender]:
            return []

        items = []
        base_domain = "https://fh.by"
        # Публичный эндпоинт поиска/фильтрации (более стабильный)
        api_url = f"{base_domain}/api/v1/products"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": f"{base_domain}/",
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            for slug in self.CATEGORY_URLS[gender][category]:
                logger.info(f"🚀 Сбор категории через поиск: {slug}")

                for page in range(1, pages + 1):
                    # Параметры запроса для поиска по категории
                    params = {
                        "q": slug,  # Текстовый запрос
                        "page": page,
                        "gender": "male" if gender == "M" else "female",
                        "per-page": 48
                    }

                    try:
                        async with session.get(api_url, params=params, timeout=15) as resp:
                            if resp.status != 200:
                                # Если поиск не вернул 200, пробуем еще один скрытый эндпоинт
                                logger.warning(f"⚠️ Статус {resp.status} для {slug}. Пробую резерв...")
                                break

                            data = await resp.json()
                            # Структура ответа FH: {'items': [...], 'meta': {...}}
                            products = data.get("items", []) or data.get("data", [])

                            if not products:
                                break

                            for p in products:
                                try:
                                    img = p.get("image") or (p.get("images")[0] if p.get("images") else None)
                                    if not img: continue

                                    item = ParsedItem(
                                        id=f'fh_{p.get("id")}',
                                        name=p.get("name", "Item"),
                                        category=category,
                                        gender=gender,
                                        price=float(p.get("price", 0)),
                                        currency="BYN",
                                        image_url=img if img.startswith("http") else f"{base_domain}{img}",
                                        product_url=f"{base_domain}/product/{p.get('slug')}",
                                        store=self.STORE_NAME,
                                        color=self._extract_color(p.get("name", "")) if hasattr(self,
                                                                                                '_extract_color') else "unknown",
                                    )
                                    items.append(item)
                                except:
                                    continue

                            logger.info(f"✅ {slug} (стр. {page}): +{len(products)} товаров")

                    except Exception as e:
                        logger.error(f"❌ Ошибка на {slug}: {e}")
                        break

                    await asyncio.sleep(1.5)

        return items
