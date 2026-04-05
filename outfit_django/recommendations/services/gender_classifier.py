"""Классификация пола по фото одежды"""
import torch
import numpy as np
from pathlib import Path
from typing import Literal
import clip


class GenderClassifier:
    """Классификатор пола на основе CLIP"""

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)

        # Текстовые промпты для классификации
        self.text_prompts = {
            'male': [
                "men's clothing", "male fashion", "for men",
                "masculine style", "men's wear"
            ],
            'female': [
                "women's clothing", "female fashion", "for women",
                "feminine style", "women's wear"
            ],
            'unisex': [
                "unisex clothing", "gender neutral fashion",
                "for everyone", "universal style"
            ]
        }

        # Подготавливаем текстовые эмбеддинги
        self._prepare_text_embeddings()

    def _prepare_text_embeddings(self):
        """Подготавливает текстовые эмбеддинги"""
        self.text_features = {}

        for gender, prompts in self.text_prompts.items():
            tokens = clip.tokenize(prompts).to(self.device)
            with torch.no_grad():
                features = self.model.encode_text(tokens)
                features = features / features.norm(dim=-1, keepdim=True)
                self.text_features[gender] = features.mean(dim=0)

    def classify(self, image_path: Path) -> dict:
        """
        Классифицирует пол одежды на фото

        Returns:
            {
                'gender': 'M' | 'F' | 'U',
                'confidence': float,
                'scores': {'male': float, 'female': float, 'unisex': float}
            }
        """
        from PIL import Image

        # Загружаем и предобрабатываем изображение
        image = Image.open(image_path).convert('RGB')
        image_input = self.preprocess(image).unsqueeze(0).to(self.device)

        # Получаем эмбеддинг изображения
        with torch.no_grad():
            image_features = self.model.encode_image(image_input)
            image_features = image_features / image_features.norm()

        # Считаем сходство с каждым полом
        scores = {}
        for gender, text_feat in self.text_features.items():
            similarity = (image_features @ text_feat).item()
            scores[gender] = similarity

        # Нормализуем в вероятности (softmax)
        exp_scores = {k: np.exp(v) for k, v in scores.items()}
        total = sum(exp_scores.values())
        probs = {k: v / total for k, v in exp_scores.items()}

        # Определяем результат
        max_gender = max(probs, key=probs.get)
        confidence = probs[max_gender]

        # Маппинг на наши коды
        gender_map = {'male': 'M', 'female': 'F', 'unisex': 'U'}

        return {
            'gender': gender_map[max_gender],
            'confidence': confidence,
            'scores': probs
        }

    def classify_batch(self, image_paths: list[Path]) -> list[dict]:
        """Классифицирует бatch изображений"""
        return [self.classify(p) for p in image_paths]