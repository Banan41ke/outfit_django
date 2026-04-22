from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from typing import List
from .base_parser import BaseParser, ParsedItem
import re
import os

class MadFashionParser(BaseParser):
    STORE_NAME = "MadFashion"

    # Ссылки на разделы каталога
    CATEGORY_URLS = {
        "F": {
            "tops": [
                "dlya_nee1/filter/sections-is-16238/apply/",
                "dlya_nee1/filter/sections-is-16194/apply/",
                "dlya_nee1/filter/sections-is-16242/apply/",
                "dlya_nee1/filter/sections-is-16229/apply/",
                "dlya_nee1/filter/sections-is-16176/apply/",
                "dlya_nee1/filter/sections-is-16208/apply/",
                "dlya_nee1/filter/sections-is-16230/apply/",
                "dlya_nee1/filter/sections-is-16180/apply/"
            ],
            "bottoms": [
                "dlya_nee1/filter/sections-is-16216/apply/",
                "dlya_nee1/filter/sections-is-16249/apply/",
                "dlya_nee1/filter/sections-is-16243/apply/",
                "dlya_nee1/filter/sections-is-16181/apply/"
            ],
            "accessories": [
                "dlya_nee1/filter/sections-is-16132/apply/",
                "dlya_nee1/filter/sections-is-16130/apply/",
                "dlya_nee1/filter/sections-is-16104/apply/",
                "dlya_nee1/filter/sections-is-16112/apply/",
                "dlya_nee1/filter/sections-is-16131/apply/"
            ]
        },
        "M": {
            "tops": [
                "dlya_nego0/filter/sections-is-16345/apply/",
                "dlya_nego0/filter/sections-is-16340/apply/",
                "dlya_nego0/filter/sections-is-16312/apply/",
                "dlya_nego0/filter/sections-is-16326/apply/"
            ],
            "bottoms": [
                "dlya_nego0/filter/sections-is-16334/apply/",
                "dlya_nego0/filter/sections-is-16342/apply/",
                "dlya_nego0/filter/sections-is-16306/apply/",
                "dlya_nego0/filter/sections-is-16349/apply/"
            ],
            "accessories": [
                "dlya_nego0/filter/sections-is-16261/apply/",
                "dlya_nego0/filter/sections-is-16270/apply/",
                "dlya_nego0/filter/sections-is-16271/apply/",
                "dlya_nego0/filter/sections-is-16273/apply/"
            ]
        }
    }

    def __enter__(self):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'browser'):
            self.browser.close()
        if hasattr(self, '_pw'):
            self._pw.stop()

    def parse_item_detail(self, url: str):
        return None

    def parse_category(self, category: str, gender: str = "F", pages: int = 1) -> List[ParsedItem]:
        if gender not in self.CATEGORY_URLS or category not in self.CATEGORY_URLS[gender]:
            return []

        items = []
        seen_ids = set()
        base_domain = "https://madfashion.by"

        context = self.browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        for path in self.CATEGORY_URLS[gender][category]:
            for p_num in range(1, pages + 1):
                url = f"{base_domain}/catalog/{path}?PAGEN_1={p_num}"
                print(f"🌐 Открываю MadFashion ({gender}): {url}")

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_selector('.item-card, .catalog-item, .product-item', timeout=15000)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(3000)

                    products = page.query_selector_all('.item-card, .catalog-item, .product-item')
                    print(f"Найдено карточек: {len(products)}")

                    if not products:
                        continue

                    for p in products:
                        try:
                            # ССЫЛКА И ID
                            # ССЫЛКА И ID
                            link = p.query_selector('a')
                            if not link:
                                continue

                            href = link.get_attribute('href')
                            if not href:
                                continue

                            # абсолютная ссылка
                            p_url = href if href.startswith('http') else base_domain + href

                            # 🔥 НАДЁЖНОЕ получение ID (берём последнее число)
                            match = re.search(r'/(\d+)/?$', href)
                            p_id = match.group(1) if match else None

                            # 🔥 ЕСЛИ ID СТРАННЫЙ (короткий) — попробуем позже из картинки

                            if p_id in seen_ids:
                                continue
                            seen_ids.add(p_id)

                            # НАЗВАНИЕ
                            name_el = p.query_selector('.item-title, .product-title, .card-title, .product-name')
                            if name_el:
                                name = name_el.inner_text().strip()
                            else:
                                name = href.split('/')[-2] if href.split('/')[-2] else f"Товар {p_id}"
                                name = name.replace('-', ' ').title()

                            if not name or name == '':
                                name = f"Товар {p_id}"

                            # КАРТИНКА
                            img_url = None
                            img = p.query_selector('img')
                            if img:
                                img_url = img.get_attribute('src')

                            if not img_url and img:
                                img_url = (img.get_attribute('data-src') or
                                          img.get_attribute('data-lazy') or
                                          img.get_attribute('data-original'))

                            if img_url:
                                img_url = img_url.strip().replace('%20', '')

                            if not img_url:
                                bg = p.query_selector('[style*="background-image"]')
                                if bg:
                                    style_attr = bg.get_attribute('style')
                                    if style_attr and 'url(' in style_attr:
                                        img_url = style_attr.split('url(')[-1].split(')')[0].replace('"', '')

                            if not img_url:
                                print(f"⚠️ Нет картинки для {p_id}, пропускаем")
                                continue

                            if img_url.startswith('//'):
                                img_url = "https:" + img_url
                            elif img_url.startswith('/'):
                                img_url = base_domain + img_url

                            # 🔥 ДОСТАЁМ ID ИЗ КАРТИНКИ ЕСЛИ НУЖНО
                            if (not p_id or len(p_id) < 5) and img_url:
                                img_id_match = re.search(r'(\d{5,7})', img_url)
                                if img_id_match:
                                    p_id = img_id_match.group(1)

                            # ЦЕНА
                            price = 0
                            price_el = p.query_selector('.price, .product-price, .item-price, .current-price')
                            if price_el:
                                price_text = price_el.inner_text().strip()
                                price_match = re.search(r'(\d+[\s]?\d*)', price_text)
                                if price_match:
                                    price = int(price_match.group(1).replace(' ', ''))

                            # СТИЛЬ
                            name_low = name.lower()
                            style = "Casual"
                            if any(x in name_low for x in ["sport", "nike", "adidas", "puma", "кросс", "бокс", "кеды"]):
                                style = "Sport"
                            elif any(x in name_low for x in ["класс", "туф", "пиджак", "костюм", "рубашк"]):
                                style = "Classic"
                            elif any(x in name_low for x in ["куртк", "пальт", "пухов", "трекинг"]):
                                style = "Outdoor"

                            # ПУТЬ ДЛЯ СОХРАНЕНИЯ (без скачивания здесь!)
                            filename = f"mad_{p_id}.jpg"
                            relative_path = os.path.join('data', 'raw', gender, category, filename)

                            # СОХРАНЯЕМ ТОВАР (картинка скачается позже в обработчике)
                            items.append(ParsedItem(
                                id=f"mad_{p_id}",
                                name=name,
                                category=category,
                                gender=gender,
                                price=price,
                                currency="BYN",
                                image_url=img_url,
                                image_path=relative_path,  # ← просто путь, без ContentFile!
                                product_url=p_url,
                                store=self.STORE_NAME,
                                color=style
                            ))

                        except Exception as e:
                            print(f"⚠️ Ошибка item: {e}")
                            continue

                    print(f"✅ Добавлено товаров: {len(items)}")

                except Exception as e:
                    print(f"❌ Ошибка страницы {url}: {e}")
                    continue

        print(f"👉 Всего уникальных товаров собрано: {len(items)}")
        page.close()
        return items