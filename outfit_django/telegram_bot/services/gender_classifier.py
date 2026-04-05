"""Классификация пола по фото одежды"""
import torch
import numpy as np
from pathlib import Path
from outfit_django.src.feature_extractor import CLIPEncoder


class GenderClassifier:
    """Классификатор пола на основе CLIP"""

    def __init__(self):
        self.encoder = CLIPEncoder()
        self.device = self.encoder.device

        # Текстовые промпты для классификации
        self.text_prompts = {
            'M': ["men's clothing", "male fashion", "for men", "masculine style", "men's wear", "мужская одежда"],
            'F': ["women's clothing", "female fashion", "for women", "feminine style", "women's wear",
                  "женская одежда"],
            'U': ["unisex clothing", "gender neutral fashion", "for everyone", "universal style", "унисекс"]
        }

        # Подготавливаем текстовые эмбеддинги
        self._prepare_text_embeddings()

    def _prepare_text_embeddings(self):
        """Подготавливает текстовые эмбеддинги"""
        import clip

        self.text_features = {}

        for gender, prompts in self.text_prompts.items():
            tokens = clip.tokenize(prompts).to(self.device)
            with torch.no_grad():
                features = self.encoder.model.encode_text(tokens)
                features = features / features.norm(dim=-1, keepdim=True)
                self.text_features[gender] = features.mean(dim=0)

    def classify(self, image_path: Path) -> dict:
        """
        Классифицирует пол одежды на фото

        Returns:
            {
                'gender': 'M' | 'F' | 'U',
                'confidence': float,
                'scores': {'M': float, 'F': float, 'U': float}
            }
        """
        from PIL import Image
        import clip

        # Загружаем и предобрабатываем изображение
        image = Image.open(image_path).convert('RGB')
        image_input = self.encoder.preprocess(image).unsqueeze(0).to(self.device)

        # Получаем эмбеддинг изображения
        with torch.no_grad():
            image_features = self.encoder.model.encode_image(image_input)
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

        return {
            'gender': max_gender,
            'confidence': confidence,
            'scores': probs
        }