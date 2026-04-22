from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from typing import List
from base_parser import BaseParser, ParsedItem


class LamodaParser(BaseParser):
    STORE_NAME = "Lamoda"

    CATEGORY_URLS = {
        "M": {
            "shoes": [
                "5318/shoes-vysokiekrossovkimuj", "159/shoes-muzhskie-krossovki",
                "5320/shoes-vysokiebotinkimuj", "151/shoes-muzhskie-botinki",
                "111/shoes-muzhskie-tufli", "2980/shoes-muzskie-loufery",
                "61/shoes-muzhskie-kedy", "5321/shoes-chelseamuj"
            ]
        },
        "F": {
            "shoes": [
                "37/shoes-baletki", "7769/shoes-baletkiskvadratnymnosom",
                "5866/shoes-baletkiskruglymnosom", "5865/shoes-baletkisostrymnosom",
                "7675/shoes-women-eveningshoes", "209/shoes-domashnaja",
                "8076/default-women_dutaya_obuv", "8080/default-women_dutiye_botinki",
                "8086/default-women_dutyie_kedi", "8084/default-women_dutiye_krossovki",
                "8078/default-women_dutye_sapogi", "8082/default-women_dutyie_sliponi",
                "7628/shoes-women-shoes-cossacks", "5855/shoes-zhenkedy",
                "5301/shoes-vysokiekedyzhen", "129/shoes-kedy",
                "5300/shoes-vysokiekrossyzhen", "43/shoes-krossovki",
                "35/shoes-mokasiny", "4077/shoes-sizeplusshoes"
            ]
        }
    }

    def __enter__(self):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=False)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'browser'): self.browser.close()
        if hasattr(self, '_pw'): self._pw.stop()

    def parse_item_detail(self, url: str):
        return None

    def parse_category(self, category: str, gender: str = "M", pages: int = 1) -> List[ParsedItem]:
        if gender not in self.CATEGORY_URLS or category not in self.CATEGORY_URLS[gender]:
            return []

        items = []
        base_domain = "https://www.lamoda.by"
        context = self.browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        for path in self.CATEGORY_URLS[gender][category]:
            url = f"{base_domain}/c/{path}/?page=1"
            print(f"🌐 Открываю ({gender}): {url}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)
                page.evaluate("window.scrollTo(0, 1000)")

                soup = BeautifulSoup(page.content(), 'html.parser')
                products = soup.select('.x-product-card__card') or soup.find_all('div', attrs={'data-product-id': True})

                if not products: continue

                for p in products:
                    try:
                        link = p.find('a', href=True)
                        if not link or '/p/' not in link['href']: continue

                        brand = p.select_one('[class*="brand-name"]')
                        name_tag = p.select_one('[class*="product-name"]')
                        img = p.find('img')
                        src = img.get('data-src') or img.get('src') if img else None
                        if not src: continue

                        full_name = f"{brand.text.strip() if brand else ''} {name_tag.text.strip() if name_tag else ''}".strip()
                        p_id = link['href'].strip('/').split('/')[-1]

                        # --- УЛУЧШЕННАЯ ЛОГИКА СТИЛЯ (Мужской + Женский) ---
                        name_low = full_name.lower()
                        style = "Casual"

                        if any(x in name_low for x in
                               ["krossovki", "kedy", "adidas", "nike", "sport", "vans", "бегов"]):
                            style = "Sport"
                        elif any(x in name_low for x in
                                 ["tufli", "baletki", "lodochki", "vechern", "classic", "klassich"]):
                            style = "Classic"
                        elif any(x in name_low for x in ["botinki", "sapogi", "dutiki", "uggi", "timberland", "zima"]):
                            style = "Outdoor"
                        elif any(x in name_low for x in ["lofery", "mokasiny", "chelsi", "slipony", "mulo", "sabo"]):
                            style = "Smart Casual"
                        elif "domash" in name_low or "tapochki" in name_low:
                            style = "Home"

                        items.append(ParsedItem(
                            id=f"lamoda_{p_id}",
                            name=full_name,
                            category=category, gender=gender, price=0, currency="BYN",
                            image_url="https:" + src if src.startswith("//") else src,
                            product_url=base_domain + link['href'],
                            store=self.STORE_NAME,
                            color=style
                        ))
                    except:
                        continue
                print(f"✅ Собрано: {len(products)} (Style: {style})")
            except Exception as e:
                print(f"❌ Ошибка: {e}")

        page.close()
        return items