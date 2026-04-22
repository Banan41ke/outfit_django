"""Матчер для подбора образов"""
import torch
import numpy as np
import faiss
import pickle
from pathlib import Path
from typing import List, Dict
from .feature_extractor import CLIPEncoder
from .config import MODELS_DIR, PROCESSED_DIR, CATEGORIES


class OutfitMatcher:
    def __init__(self, models_dir: Path = None, data_dir: Path = None):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Пути к индексам и данным
        self.models_dir = models_dir or MODELS_DIR
        self.data_dir = data_dir or PROCESSED_DIR

        # Загружаем индексы FAISS
        self.indices = {}
        self.metadata = {}
        self._load_indices()

        # Инициализируем энкодер для новых изображений
        self.encoder = CLIPEncoder()

    def _load_indices(self):
        """Загрузка FAISS индексов для всех категорий"""
        import pandas as pd

        for cat in CATEGORIES:
            index_path = self.models_dir / f"{cat}.index"
            meta_path = self.models_dir / f"{cat}_meta.pkl"

            if index_path.exists() and meta_path.exists():
                self.indices[cat] = faiss.read_index(str(index_path))
                with open(meta_path, 'rb') as f:
                    loaded = pickle.load(f)

                # Конвертируем DataFrame в список словарей
                if isinstance(loaded, pd.DataFrame):
                    self.metadata[cat] = loaded.reset_index().to_dict('records')
                elif isinstance(loaded, list):
                    self.metadata[cat] = loaded
                else:
                    self.metadata[cat] = []

                print(f"✅ Загружен индекс {cat}: {len(self.metadata[cat])} items, тип: {type(self.metadata[cat])}")
            else:
                print(f"⚠️ Индекс {cat} не найден")
                self.indices[cat] = None
                self.metadata[cat] = []

    def suggest_outfit_full(
            self,
            query_image_path: Path,
            query_category: str,
            top_k: int = 6,
            season: str = "all"
    ) -> Dict[str, List[Dict]]:

        query_embedding = self.encoder.encode_image(query_image_path)
        if query_embedding is None:
            return {cat: [] for cat in CATEGORIES}

        # 1. ОПРЕДЕЛЕНИЕ ПОЛА (Исправлено для твоей структуры папок)
        query_path_str = str(query_image_path).replace("\\", "/")  # Унифицируем слеши

        if "/M/" in query_path_str or "_M_" in query_path_str:
            query_gender = "M"
        elif "/F/" in query_path_str or "_F_" in query_path_str:
            query_gender = "F"
        else:
            query_gender = None

        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        faiss.normalize_L2(query_embedding)

        complementary = {
            'tops': ['bottoms', 'shoes', 'accessories'],
            'bottoms': ['tops', 'shoes', 'accessories'],
            'shoes': ['tops', 'bottoms', 'accessories'],
            'accessories': ['tops', 'bottoms', 'shoes']
        }

        results = {}
        target_cats = complementary.get(query_category, CATEGORIES)

        for cat in target_cats:
            print(f"\n🔍 Обработка категории: {cat}")

            if self.indices.get(cat) is None:
                print(f"  ❌ Индекс {cat} не загружен")
                results[cat] = []
                continue

            print(f"  ✅ Индекс загружен, метаданных: {len(self.metadata[cat])}")

            # 2. ПОИСК
            search_k = min(500, len(self.metadata[cat]))
            print(f"  🔎 Поиск {search_k} ближайших соседей...")

            D, I = self.indices[cat].search(query_embedding, search_k)

            print(f"  📊 Результаты поиска: D shape={D.shape}, I shape={I.shape}")
            print(f"  📊 Первые 5 расстояний: {D[0][:5]}")
            print(f"  📊 Первые 5 индексов: {I[0][:5]}")

            items = []
            seen_ids = set()
            seen_names = set()

            for idx, dist in zip(I[0], D[0]):
                idx = int(idx)

                if idx < 0 or idx >= len(self.metadata[cat]):
                    continue

                meta = self.metadata[cat][idx]

                filename = meta.get('raw_filename', meta.get('filename', ''))
                if not filename:
                    continue

                print(f"DEBUG META CATEGORY: {meta.get('category')} | INDEX CAT: {cat} | FILE: {filename}")

                real_category = meta.get('category')

                # ❌ если категории нет — сразу пропускаем
                if not real_category:
                    continue

                # ❌ если категория не совпадает — пропускаем
                if real_category != cat:
                    continue

                item_id = meta.get('id', idx)

                # ✅ УБИРАЕМ ДУБЛИКАТЫ ПО ID
                if item_id in seen_ids:
                    continue

                # ✅ УБИРАЕМ ДУБЛИКАТЫ ПО ИМЕНИ (НО ПРАВИЛЬНО)
                name_key = filename.lower()
                if name_key in seen_names:
                    continue

                # ❗ УБРАЛИ dist > 1.0 (это ломало всё)

                similarity = float(1 / (1 + dist))

                item = {
                    'id': item_id,
                    'name': filename,
                    'filename': filename,  # ← ДОБАВЛЕНО
                    'image_path': meta.get('image_path', ''),  # ← ДОБАВЛЕНО (полный путь)
                    'gender': meta.get('gender', ''),
                    'category': cat,
                    'color': meta.get('color_rgb', [128, 128, 128]),
                    'similarity_score': similarity * 100,
                    'style': meta.get('style', 'casual')
                }

                items.append(item)

                seen_ids.add(item_id)
                seen_names.add(name_key)

                if len(items) >= top_k:
                    break

            results[cat] = items

        return results

    def find_similar(self, category: str, embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """Найти похожие вещи в конкретной категории"""
        if self.indices.get(category) is None:
            return []

        embedding = embedding.reshape(1, -1).astype('float32')
        D, I = self.indices[category].search(embedding, top_k)

        results = []
        for idx, dist in zip(I[0], D[0]):
            idx = int(idx)  # <-- ДОБАВЬТЕ ЭТО
            if idx < len(self.metadata[category]):
                meta = self.metadata[category][idx]
                if isinstance(meta, dict):
                    meta = meta.copy()
                else:
                    # Если это Series от DataFrame
                    meta = dict(meta)
                meta['similarity'] = 1 / (1 + dist)
                results.append(meta)

        return results