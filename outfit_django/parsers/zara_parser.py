import asyncio
import aiohttp
from typing import List
from .base_parser import BaseParser, ParsedItem


class ZaraParser(BaseParser):
    STORE_NAME = "Zara"

    CATEGORY_MAP = {
        "M": {
            "tops": 1010192001,
            "bottoms": 1010192002,
            "shoes": 1010192010,
        },
        "F": {
            "tops": 1010202001,
            "bottoms": 1010202002,
            "shoes": 1010202010,
        }
    }

    async def parse_category(
        self,
        category: str,
        gender: str = None,
        pages: int = 5
    ) -> List[ParsedItem]:

        items = []
        seen_ids = set()
        genders = [gender] if gender else ["M", "F"]

        async with aiohttp.ClientSession() as session:
            for g in genders:
                cat_id = self.CATEGORY_MAP[g][category]

                for page in range(pages):
                    url = (
                        f"https://www.zara.com/ru/ru/category/{cat_id}/products.json"
                        f"?page={page}"
                    )

                    try:
                        headers = {
                            "User-Agent": "Mozilla/5.0",
                            "Accept": "application/json, text/plain, */*",
                            "Referer": "https://www.zara.com/",
                        }

                        async with session.get(url, headers=headers) as resp:
                            if resp.status != 200:
                                print(f"❌ status {resp.status}")
                                continue

                            data = await resp.json()
                    except Exception as e:
                        print("❌ ошибка запроса:", e)
                        continue

                    product_groups = data.get("productGroups", [])

                    all_products = []
                    for group in product_groups:
                        for el in group.get("elements", []):
                            for comp in el.get("commercialComponents", []):
                                if "product" in comp:
                                    all_products.append(comp["product"])

                    for p in all_products:
                        try:
                            product_id = p["id"]

                            # ❌ убираем дубли
                            if product_id in seen_ids:
                                continue
                            seen_ids.add(product_id)

                            name = p.get("name", "")

                            # 💰 цена
                            price_data = p.get("price", {}).get("price", {})
                            price = price_data.get("value", 0) / 100 if price_data else 0

                            # 🖼️ картинка (с fallback)
                            image_url = None
                            try:
                                image_url = p["detail"]["mainImage"]["url"]
                            except:
                                try:
                                    image_url = p["xmedia"][0]["url"]
                                except:
                                    continue

                            # 🔗 ссылка
                            keyword = p.get("seo", {}).get("keyword", "")
                            product_url = f"https://www.zara.com/ru/ru/{keyword}-p{product_id}.html"

                            item = ParsedItem(
                                id=f"zara_{product_id}",
                                name=name,
                                category=category,
                                gender=g,
                                price=float(price),
                                currency="RUB",
                                image_url=image_url,
                                product_url=product_url,
                                store=self.STORE_NAME,
                                color=self._extract_color(name),
                            )

                            items.append(item)

                        except Exception as e:
                            print("⚠️ ошибка парсинга товара:", e)
                            continue

                    print(f"✅ {category} {g} page {page}: {len(all_products)} товаров")

                    await asyncio.sleep(1)

        return items

    def _extract_color(self, name: str) -> str:
        colors = {
            'black': 'black',
            'white': 'white',
            'blue': 'blue',
            'red': 'red',
            'beige': 'beige',
            'gray': 'gray',
            'brown': 'brown',
            'pink': 'pink',
        }

        name = name.lower()

        for c in colors:
            if c in name:
                return c

        return 'unknown'

    async def parse_item_detail(self, product_url: str):
        """Заглушка (обязательный метод BaseParser)"""
        return None