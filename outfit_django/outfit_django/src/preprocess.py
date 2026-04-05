"""Обработка изображений: resize + извлечение цвета"""
import os
import cv2
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.cluster import KMeans
from tqdm import tqdm
from .config import RAW_DIR, PROCESSED_DIR, IMAGE_SIZE, CATEGORIES


def get_dominant_color(image_path: Path, k: int = 3) -> tuple:
    """Извлекает доминантный цвет через KMeans"""
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return (128, 128, 128)  # Default gray

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (100, 100))

        pixels = img.reshape(-1, 3)
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(pixels)

        counts = np.bincount(kmeans.labels_)
        dominant = kmeans.cluster_centers_[np.argmax(counts)]

        return tuple(int(x) for x in dominant)
    except Exception:
        return (128, 128, 128)


def process_category(category: str) -> list:
    """Обрабатывает все фото одной категории"""
    input_dir = RAW_DIR / category
    if not input_dir.exists():
        print(f"⚠️  Папка {input_dir} не найдена, пропускаем")
        return []

    # Поддерживаемые форматы
    extensions = ["*.jpg", "*.jpeg", "*.png", "*.webp", "*.JPG", "*.PNG"]
    image_files = []
    for ext in extensions:
        image_files.extend(list(input_dir.glob(ext)))

    records = []
    print(f"Обработка {category}: {len(image_files)} фото...")

    for img_path in tqdm(image_files):
        try:
            # Читаем и ресайзим
            img = cv2.imread(str(img_path))
            if img is None:
                continue

            img = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE))

            # Сохраняем
            output_name = f"{category}_{img_path.stem}.jpg"
            output_path = PROCESSED_DIR / output_name
            cv2.imwrite(str(output_path), img)

            # Извлекаем цвет с оригинала (чтобы точнее)
            color = get_dominant_color(img_path)

            records.append({
                'original_name': img_path.name,
                'filename': output_name,
                'category': category,
                'color_r': color[0],
                'color_g': color[1],
                'color_b': color[2],
                'path': str(output_path.relative_to(Path(__file__).parent.parent))
            })

        except Exception as e:
            print(f"Ошибка с {img_path}: {e}")

    return records


def run_preprocessing():
    """Главная функция preprocessing"""
    print("🚀 Начинаем обработку данных...")

    all_records = []
    for category in CATEGORIES:
        records = process_category(category)
        all_records.extend(records)

    # Сохраняем CSV
    df = pd.DataFrame(all_records)
    csv_path = RAW_DIR.parent / "metadata.csv"
    df.to_csv(csv_path, index=False)

    print(f"\n✅ Готово! Обработано {len(df)} изображений")
    print(f"📁 Файл метаданных: {csv_path}")
    print("\nРаспределение по категориям:")
    print(df['category'].value_counts())

    return df


if __name__ == "__main__":
    run_preprocessing()