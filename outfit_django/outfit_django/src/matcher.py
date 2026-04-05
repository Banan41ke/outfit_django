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
        """
        Полный подбор образа на основе загруженного фото
        """
        query_embedding = self.encoder.encode_image(query_image_path)

        # 🔥 определяем пол по имени файла
        query_path_str = str(query_image_path)

        if "_F_" in query_path_str:
            query_gender = "F"
        elif "_M_" in query_path_str:
            query_gender = "M"
        else:
            query_gender = None  # если пользователь загрузил своё фото

        if query_embedding is None:
            return {cat: [] for cat in CATEGORIES}

        query_embedding = query_embedding.reshape(1, -1).astype('float32')

        complementary = {
            'tops': ['bottoms', 'shoes', 'accessories'],
            'bottoms': ['tops', 'shoes', 'accessories'],
            'shoes': ['tops', 'bottoms', 'accessories'],
            'accessories': ['tops', 'bottoms', 'shoes']
        }

        results = {}
        target_cats = complementary.get(query_category, CATEGORIES)

        for cat in target_cats:
            if self.indices[cat] is None:
                results[cat] = []
                continue

            # 🔥 увеличили пул кандидатов
            D, I = self.indices[cat].search(query_embedding, top_k * 5)

            seen_ids = set()
            seen_colors = set()
            items = []

            for idx, dist in zip(I[0], D[0]):
                idx = int(idx)

                if idx >= len(self.metadata[cat]):
                    continue

                meta = self.metadata[cat][idx]
                filename = meta.get('raw_filename', '')

                # 🔥 фильтр по полу
                if query_gender:
                    if f"_{query_gender}_" not in filename:
                        continue
                # фильтр по сезону
                if season != "all" and isinstance(season, list):
                    item_color = meta.get('color_name', '').lower()
                    if item_color not in season:
                        continue

                item_id = meta.get('id', idx)
                color = meta.get('color_name', 'unknown')

                # ❌ убираем дубли
                if item_id in seen_ids:
                    continue

                # 🎨 добавляем разнообразие (но не ломаем выдачу)
                if color in seen_colors and len(items) < top_k:
                    continue

                seen_ids.add(item_id)
                seen_colors.add(color)

                # 🔥 нормальный скор
                similarity = float(np.exp(-dist))

                item = {
                    'id': item_id,
                    'path': f"{cat}/{meta.get('raw_filename', meta.get('filename', ''))}",
                    'filename': meta.get('raw_filename', meta.get('original_name', meta.get('filename', ''))),
                    'category': cat,
                    'color': meta.get('color_rgb', [128, 128, 128]),
                    'color_name': color,
                    'similarity_score': similarity * 100,
                    'style': meta.get('style', 'casual')
                }

                items.append(item)

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