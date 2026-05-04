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

    def color_distance(self, c1, c2):
        if not c1 or not c2:
            return 0.5
        return np.linalg.norm(np.array(c1) - np.array(c2)) / 441  # нормализация

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
            season: str = "all",
            user_gender: str = None,
            user_style: str = None
    ) -> Dict[str, List[Dict]]:

        query_embedding = self.encoder.encode_image(query_image_path)
        if user_style:
            query_style = user_style
            style_conf = 1.0
        else:
            query_style, style_conf = self.encoder.predict_style(query_image_path)

        query_style = query_style.lower() if query_style else ""
        print(f"🎯 Определён стиль: {query_style} ({style_conf:.2f})")
        if query_embedding is None:
            return {cat: [] for cat in CATEGORIES}

        # 1. ОПРЕДЕЛЕНИЕ ПОЛА (Исправлено для твоей структуры папок)
        query_path_str = str(query_image_path).replace("\\", "/")  # Унифицируем слеши

        if user_gender:
            query_gender = user_gender
        elif "/M/" in query_path_str or "_M_" in query_path_str:
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

        # === извлекаем цвет запроса один раз ===
        query_color = [128, 128, 128]
        if hasattr(self.encoder, "extract_color"):
            query_color = self.encoder.extract_color(query_image_path)

        for cat in target_cats:

            print(f"\n🔍 Обработка категории: {cat}")

            if self.indices.get(cat) is None:
                print(f"  ❌ Индекс {cat} не загружен")
                results[cat] = []
                continue

            print(f"  ✅ Индекс загружен, метаданных: {len(self.metadata[cat])}")

            # 2. ПОИСК
            search_k = min(1000, len(self.metadata[cat]))
            print(f"  🔎 Поиск {search_k} ближайших соседей...")

            D, I = self.indices[cat].search(query_embedding, search_k)

            print(f"  📊 Результаты поиска: D shape={D.shape}, I shape={I.shape}")
            print(f"  📊 Первые 5 расстояний: {D[0][:5]}")
            print(f"  📊 Первые 5 индексов: {I[0][:5]}")

            items = []
            seen_names = set()


            candidates = []
            for idx, dist in zip(I[0], D[0]):
                idx = int(idx)

                if idx < 0 or idx >= len(self.metadata[cat]):
                    continue

                meta = self.metadata[cat][idx]

                print(
                    "CAT:", cat,
                    "| meta.category:", meta.get('category'),
                    "| original:", meta.get('original_category'),
                    "| path:", meta.get('image_path')
                )

                if meta.get('category') != cat:
                    continue


                item_style = meta.get('style', '').lower()

                # упрощаем стиль

                # === СТИЛЬ (единая логика) ===

                # определяем целевой стиль
                if any(x in query_style for x in ["casual", "smart casual"]):
                    target_style = "casual"
                elif "sport" in query_style:
                    target_style = "sport"
                elif any(x in query_style for x in ["classic", "formal"]):
                    target_style = "classic"
                else:
                    target_style = None

                style_score = 1.0

                # 1. влияние пользовательского/определённого стиля
                if target_style and item_style:
                    if target_style in item_style:
                        style_score *= 1.05
                    else:
                        style_score *= 0.95

                # 2. лёгкий бонус базовому стилю вещи
                meta_style = meta.get('style', '').lower()

                if meta_style == 'casual':
                    style_score *= 1.05
                elif meta_style == 'sport':
                    style_score *= 1.02

                # 👇 ФИЛЬТР ПОЛА
                if query_gender and meta.get('gender') and meta.get('gender') != query_gender:
                    continue

                filename = meta.get('raw_filename', meta.get('filename', ''))
                if not filename:
                    continue

                item_id = meta.get('id', idx)

                similarity = float(1 / (1 + dist))
                if query_category != cat and similarity > 0.92:
                    continue

                if meta.get('image_path') == str(query_image_path):
                    continue

                # 👇 ЦВЕТ

                color_score = 1.0
                if 'color_rgb' in meta:
                    color_score = 1 - self.color_distance(meta.get('color_rgb'), query_color)

                final_score = (
                        similarity * 0.6 +
                        color_score * 0.2 +
                        style_score * 0.2
                )
                if query_category != cat and similarity > 0.8:
                    final_score *= 0.7

                candidates.append((final_score, item_id, filename, meta))
            items = []
            used_colors = []
            seen_ids = set()
            print(f"Кандидатов после поиска: {len(candidates)}")

            candidates.sort(key=lambda x: x[0], reverse=True)
            for score, item_id, filename, meta in candidates:

                if item_id in seen_ids:
                    continue

                unique_key = meta.get('image_path')

                if unique_key in seen_names:
                    continue

                seen_names.add(unique_key)

                print("FINAL ITEM:", filename, meta.get('image_path'))

                color = meta.get('color_rgb', [128, 128, 128])

                adjusted_score = score

                penalty = 1.0
                if any(np.linalg.norm(np.array(color) - np.array(c)) < 40 for c in used_colors):
                    penalty = 0.9

                adjusted_score *= penalty

                item = {
                    'id': item_id,
                    'name': filename,
                    'filename': filename,
                    'image_path': meta.get('image_path', ''),
                    'gender': meta.get('gender', ''),
                    'category': cat,
                    'color': color,
                    'similarity_score': adjusted_score * 100,
                    'style': meta.get('style', 'casual')
                }

                items.append(item)
                seen_ids.add(item_id)
                used_colors.append(color)

                if len(items) >= top_k:
                    break

            print(f"Финальных айтемов: {len(items)}")
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

