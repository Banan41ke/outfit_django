"""Async API клиент для работы с Django/Recommendations"""
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import asyncio
import random

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class DjangoInitializer:
    """Ленивая инициализация Django (thread-safe)"""
    _initialized = False
    _lock = asyncio.Lock()

    @classmethod
    async def setup(cls):
        if cls._initialized:
            return

        async with cls._lock:
            if cls._initialized:
                return

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, cls._setup_sync)
            cls._initialized = True

    @staticmethod
    def _setup_sync():
        """Синхронная инициализация Django"""
        sys.path.insert(0, str(BASE_DIR))
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'outfit_django.settings')
        import django
        django.setup()


class StyleAPI:
    """API с интеграцией локальных индексов и БД парсера"""

    def __init__(self):
        from outfit_django.src.matcher import OutfitMatcher
        from outfit_django.src.feature_extractor import CLIPEncoder
        from recommendations.models import ClothingItem
        from telegram_bot.services.gender_classifier import GenderClassifier

        self.matcher = OutfitMatcher()
        self.encoder = CLIPEncoder()
        self.gender_classifier = GenderClassifier()
        self.ClothingItem = ClothingItem

    def analyze_photo(self, photo_path: Path, category: str = None) -> dict:
        """Анализирует фото с определением пола и смешанным поиском"""
        gender_result = self.gender_classifier.classify(photo_path)
        detected_gender = gender_result['gender']
        gender_confidence = gender_result['confidence']

        print(f"👤 Определён пол: {detected_gender} (уверенность: {gender_confidence:.2f})")

        # 1. Получаем локальные рекомендации из FAISS
        local_recommendations = self.matcher.suggest_outfit_full(
            query_image_path=photo_path,
            query_category=category or 'tops',
            top_k=5,
        )

        # 2. Получаем товары из парсера (БД)
        db_recommendations = self._get_db_recommendations(
            photo_path, category or 'tops', detected_gender
        )

        # 3. Объединяем и фильтруем по полу
        merged_recommendations = self._merge_recommendations(
            local_recommendations, db_recommendations, detected_gender
        )

        return {
            'success': True,
            'category': category or 'tops',
            'category_ru': self._category_to_ru(category or 'tops'),
            'gender': detected_gender,
            'gender_ru': {'M': 'Мужское', 'F': 'Женское', 'U': 'Унисекс'}[detected_gender],
            'gender_confidence': gender_confidence,
            'recommendations': merged_recommendations,
            'total_items': sum(len(items) for items in merged_recommendations.values()),
            'sources': {
                'local': sum(len(items) for items in local_recommendations.values()),
                'database': sum(len(items) for items in db_recommendations.values())
            }
        }

    def _get_db_recommendations(self, photo_path: Path, query_category: str, gender: str) -> dict:
        """Получает рекомендации из БД парсера по цвету"""
        query_color = self._extract_color(photo_path)

        recommendations = {}
        categories = ['bottoms', 'shoes', 'accessories'] if query_category == 'tops' else \
                     ['tops', 'shoes', 'accessories'] if query_category == 'bottoms' else \
                     ['tops', 'bottoms', 'accessories']

        for cat in categories:
            # ← ИСПРАВЛЕНО: image_path вместо image
            db_items = self.ClothingItem.objects.filter(
                category=cat,
                gender__in=[gender, 'U']
            ).exclude(image_path__isnull=True).exclude(image_path='')[:20]

            scored_items = []
            for item in db_items:
                if item.color_rgb:
                    # Парсим color_rgb (формат "R,G,B")
                    try:
                        rgb = [int(x) for x in item.color_rgb.split(',')]
                        item_color = tuple(rgb)
                        color_dist = self._color_distance(query_color, item_color)
                        similarity = max(0, 100 - color_dist * 0.5)  # Масштабируем
                    except:
                        similarity = 50
                else:
                    similarity = 50

                scored_items.append((similarity, item))

            scored_items.sort(reverse=True, key=lambda x: x[0])

            recommendations[cat] = []
            for similarity, item in scored_items[:5]:
                # ← ИСПРАВЛЕНО: image_path вместо image
                filename = str(item.image_path).split('/')[-1] if item.image_path else f'{cat}_{item.id}.jpg'

                # Парсим color_rgb
                color_r, color_g, color_b = 128, 128, 128
                if item.color_rgb:
                    try:
                        rgb = [int(x) for x in item.color_rgb.split(',')]
                        color_r, color_g, color_b = rgb[0], rgb[1], rgb[2]
                    except:
                        pass

                recommendations[cat].append({
                    'id': str(item.id),
                    'filename': filename,
                    'category': cat,
                    'color_r': color_r,
                    'color_g': color_g,
                    'color_b': color_b,
                    'similarity_score': similarity / 100,
                    'source': 'parser',
                    'name': item.name or 'Без названия',
                    'price': str(item.price) if item.price else 'Цена не указана',
                    'store': item.store or 'Unknown',
                    'product_url': item.product_url or '',
                    'gender_match': item.gender,
                    'gender_emoji': {'M': '👨', 'F': '👩', 'U': '👤'}.get(item.gender, '👤'),
                })

        return recommendations

    def _extract_color(self, photo_path: Path) -> tuple:
        """Извлекает доминирующий цвет из фото"""
        try:
            from PIL import Image
            import numpy as np

            img = Image.open(photo_path).convert('RGB')
            img = img.resize((100, 100))
            pixels = np.array(img)
            mean_color = tuple(pixels.mean(axis=(0, 1)).astype(int))
            return mean_color
        except Exception:
            return (128, 128, 128)

    def _color_distance(self, color1: tuple, color2: tuple) -> float:
        """Евклидово расстояние между цветами"""
        return sum((a - b) ** 2 for a, b in zip(color1, color2)) ** 0.5

    def _merge_recommendations(self, local: dict, db: dict, gender: str) -> dict:
        """Объединяет локальные и БД рекомендации"""
        merged = {}

        all_categories = set(local.keys()) | set(db.keys())

        for cat in all_categories:
            local_items = local.get(cat, [])
            db_items = db.get(cat, [])

            for item in local_items:
                item['source'] = 'local'
                item = self._enrich_local_item(item)

            combined = local_items + db_items
            random.shuffle(combined)

            filtered = []
            for item in combined:
                item_gender = item.get('gender_match', 'U')
                if item_gender in [gender, 'U', 'unknown']:
                    filtered.append(item)

            merged[cat] = filtered[:5]

        return merged

    def _enrich_local_item(self, item: dict) -> dict:
        """Пытается обогатить локальный товар данными из БД"""
        db_item = self._find_in_db(item)
        if db_item:
            item['name'] = db_item.name or item.get('filename', 'Без названия')
            item['price'] = str(db_item.price) if db_item.price else 'Цена не указана'
            item['store'] = db_item.store or 'Local'
            item['product_url'] = db_item.product_url or ''
            item['gender_match'] = db_item.gender
            item['gender_emoji'] = {'M': '👨', 'F': '👩', 'U': '👤'}.get(db_item.gender, '👤')
        else:
            item['name'] = item.get('filename', 'Без названия')
            item['price'] = 'Нет в базе'
            item['store'] = 'Local'
            item['product_url'] = ''
            item['gender_match'] = 'unknown'
            item['gender_emoji'] = '👤'
        return item

    def _find_in_db(self, item: dict):
        """Ищет товар в БД"""
        item_id = item.get('id', '')
        if item_id:
            try:
                return self.ClothingItem.objects.get(id=item_id)
            except self.ClothingItem.DoesNotExist:
                pass

        filename = item.get('filename', '')
        if filename:
            name_clean = filename.replace('.jpg', '').replace('.webp', '').replace('.png', '')
            if '_' in name_clean:
                name_clean = name_clean.split('_', 1)[1]

            try:
                return self.ClothingItem.objects.get(id=name_clean)
            except self.ClothingItem.DoesNotExist:
                pass

            # ← ИСПРАВЛЕНО: image_path__icontains вместо image__icontains
            try:
                return self.ClothingItem.objects.filter(image_path__icontains=name_clean).first()
            except Exception:
                pass

        return None

    def _category_to_ru(self, category: str) -> str:
        mapping = {
            'tops': 'Верх',
            'bottoms': 'Низ',
            'shoes': 'Обувь',
            'accessories': 'Аксессуары'
        }
        return mapping.get(category, category)


class AsyncStyleAPI:
    """Async-обёртка для StyleAPI"""

    def __init__(self, max_workers: int = 2):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="style_api")
        self._api: StyleAPI = None
        self._init_lock = asyncio.Lock()

    async def _get_api(self) -> StyleAPI:
        """Ленивая инициализация API"""
        if self._api is not None:
            return self._api

        async with self._init_lock:
            if self._api is not None:
                return self._api

            await DjangoInitializer.setup()

            loop = asyncio.get_event_loop()
            self._api = await loop.run_in_executor(self._executor, StyleAPI)
            return self._api

    async def analyze_photo(self, photo_path: Path, category: str = None) -> dict:
        """Async-версия analyze_photo"""
        api = await self._get_api()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: api.analyze_photo(photo_path, category)
        )

    async def close(self):
        """Закрытие пула потоков"""
        self._executor.shutdown(wait=True)


# Singleton
_async_api_instance: AsyncStyleAPI = None

async def get_style_api() -> AsyncStyleAPI:
    """Получение инстанса API"""
    global _async_api_instance
    if _async_api_instance is None:
        _async_api_instance = AsyncStyleAPI()
    return _async_api_instance

async def analyze_photo(photo_path: Path, category: str = None) -> dict:
    """Удобная функция для анализа фото"""
    api = await get_style_api()
    return await api.analyze_photo(photo_path, category)