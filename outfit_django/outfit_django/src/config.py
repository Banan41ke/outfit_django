from pathlib import Path

# Пути - идём вверх от src/ → outfit_django/ → outfit_django/ → outfit_django (корень)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = ROOT_DIR / "models" #MODELS_DIR = ROOT_DIR / "models" / "faiss_indices"

# Создаём папки при импорте
DATA_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Настройки CLIP
CLIP_MODEL_NAME = "ViT-B/32"
IMAGE_SIZE = 224

# Категории
CATEGORIES = ["tops", "bottoms", "shoes", "accessories"]

# Цветовые настройки
NEUTRAL_COLORS = [
    (255, 255, 255), (0, 0, 0), (128, 128, 128),
    (245, 245, 220), (210, 180, 140)
]