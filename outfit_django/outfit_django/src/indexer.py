"""Создание FAISS индексов для каждой категории"""
import faiss
import numpy as np
import pandas as pd
import pickle
from pathlib import Path
from .config import MODELS_DIR, CATEGORIES  # Добавлен импорт CATEGORIES


class FAISSIndexer:
    def __init__(self):
        self.indices = {}
        self.metadata = {}

    def build_index(self, df: pd.DataFrame):
        """Строит отдельный индекс для каждой категории"""
        for category in CATEGORIES:
            cat_df = df[df['category'] == category]
            if len(cat_df) == 0:
                print(f"⚠️  Нет данных для {category}")
                continue

            print(f"\nСтроим индекс для {category} ({len(cat_df)} items)...")

            # Извлекаем эмбеддинги
            embeddings = np.array(cat_df['embedding'].tolist()).astype('float32')

            # Создаём индекс Inner Product ~= Cosine Similarity (т.к. векторы нормализованы)
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatIP(dimension)

            # Добавляем векторы
            index.add(embeddings)

            # Сохраняем
            index_path = MODELS_DIR / f"{category}.index"
            faiss.write_index(index, str(index_path))

            # Сохраняем метаданные отдельно (чтобы знать, какому файлу соответствует ID)
            metadata_path = MODELS_DIR / f"{category}_meta.pkl"
            cat_df[['filename', 'category', 'color_r', 'color_g', 'color_b']].to_pickle(metadata_path)

            self.indices[category] = index
            self.metadata[category] = cat_df

            print(f"✅ Сохранён: {index_path}")

    def load_index(self, category: str):
        """Загружает существующий индекс"""
        index_path = MODELS_DIR / f"{category}.index"
        meta_path = MODELS_DIR / f"{category}_meta.pkl"

        if not index_path.exists():
            raise FileNotFoundError(f"Индекс для {category} не найден. Сначала запусти build_database.py")

        import faiss
        index = faiss.read_index(str(index_path))
        metadata = pd.read_pickle(meta_path)

        return index, metadata