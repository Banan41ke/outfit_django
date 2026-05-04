"""CLIP для извлечения эмбеддингов"""
import torch
import clip
from PIL import Image
import numpy as np
from pathlib import Path
from tqdm import tqdm
import pandas as pd
from .config import CLIP_MODEL_NAME, PROCESSED_DIR


class CLIPEncoder:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Загрузка CLIP на {self.device}...")

        self.model, self.preprocess = clip.load(CLIP_MODEL_NAME, device=self.device)
        self.model.eval()

    def encode_image(self, image_path: Path) -> np.ndarray:
        """Возвращает эмбеддинг (512,) для одного изображения"""
        try:
            image = Image.open(image_path).convert('RGB')
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)

            with torch.no_grad():
                features = self.model.encode_image(image_input)

            # Нормализация (важно для cosine similarity в FAISS)
            features /= features.norm(dim=-1, keepdim=True)
            return features.cpu().numpy().flatten()
        except Exception as e:
            print(f"Ошибка кодирования {image_path}: {e}")
            return None

    def encode_batch(self, image_paths: list, batch_size: int = 16):
        """Кодирует батчем (быстрее)"""
        all_features = []

        for i in tqdm(range(0, len(image_paths), batch_size), desc="Encoding"):
            batch_paths = image_paths[i:i + batch_size]
            batch_images = []

            for path in batch_paths:
                try:
                    img = Image.open(path).convert('RGB')
                    batch_images.append(self.preprocess(img))
                except Exception:
                    batch_images.append(torch.zeros(3, 224, 224))  # Плейсхолдер

            if not batch_images:
                continue

            batch_tensor = torch.stack(batch_images).to(self.device)

            with torch.no_grad():
                features = self.model.encode_image(batch_tensor)
                features /= features.norm(dim=-1, keepdim=True)

            all_features.extend(features.cpu().numpy())

        return np.array(all_features)

    def process_dataframe(self, df: pd.DataFrame):
        """Добавляет колонку с эмбеддингами в DataFrame"""
        print("Извлечение CLIP-эмбеддингов...")

        paths = [PROCESSED_DIR / row['filename'] for _, row in df.iterrows()]

        embeddings = self.encode_batch(paths)
        df['embedding'] = list(embeddings)

        print("✅ Эмбеддинги готовы")
        return df

    def predict_style(self, image_path):
        from PIL import Image
        import torch
        import clip

        styles = [
            "casual outfit",
            "sport outfit",
            "classic elegant outfit",
            "streetwear outfit",
            "formal business outfit",
            "outdoor outfit"
        ]

        image = self.preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0).to(self.device)
        text = clip.tokenize(styles).to(self.device)

        with torch.no_grad():
            image_features = self.model.encode_image(image)
            text_features = self.model.encode_text(text)

            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)

            similarity = (image_features @ text_features.T).softmax(dim=-1)

        best_idx = similarity.argmax().item()
        return styles[best_idx], float(similarity[0][best_idx])

    def predict_category(self, image_path):
        from PIL import Image
        import clip
        import torch
        import numpy as np

        categories = [
            "a t-shirt or shirt (top clothing)",
            "pants or jeans (bottom clothing)",
            "shoes or sneakers",
            "accessories like bag, hat, glasses"
        ]

        image = self.preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0).to(self.device)
        text = clip.tokenize(categories).to(self.device)

        with torch.no_grad():
            image_features = self.model.encode_image(image)
            text_features = self.model.encode_text(text)

            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)

            similarity = (image_features @ text_features.T).softmax(dim=-1)

        probs = similarity.cpu().numpy()[0]
        idx = np.argmax(probs)

        mapping = ["tops", "bottoms", "shoes", "accessories"]

        return mapping[idx], float(probs[idx])