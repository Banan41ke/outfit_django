import numpy as np
from PIL import Image
from outfit_django.src.matcher import OutfitMatcher
from outfit_django.src.feature_extractor import CLIPEncoder

class OutfitMatcherService:
    def __init__(self):
        self.matcher = OutfitMatcher()
        self.encoder = CLIPEncoder()

    def get_recommendations(self, image_path, top_k=6, user_gender=None, user_style=None):
        """Получить рекомендации для загруженного изображения"""
        # Определяем категорию загруженного фото
        query_category, confidence = self.predict_category(image_path)

        # Получаем рекомендации
        recs = self.matcher.suggest_outfit_full(
            image_path,
            query_category,
            top_k=top_k,
            season="all",
            user_gender=user_gender,
            user_style=user_style
        )

        return {
            'query_category': query_category,
            'confidence': confidence,
            'recommendations': recs
        }

    def predict_category(self, image_path):
        """Определить категорию одежды на фото"""
        import clip
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        texts = ["shirt top", "pants jeans", "shoes sneakers", "bag accessory"]
        tokens = clip.tokenize(texts).to(device)

        with torch.no_grad():
            text_feat = self.encoder.model.encode_text(tokens)
            text_feat /= text_feat.norm(dim=-1, keepdim=True)

            emb = self.encoder.encode_image(image_path)
            if emb is None:
                return "tops", 0.5

            img_emb = torch.tensor(emb).float().to(device)
            img_emb = img_emb / img_emb.norm()
            sim = (100.0 * img_emb @ text_feat.T).softmax(dim=-1)

            cats = ["tops", "bottoms", "shoes", "accessories"]
            idx = sim.argmax().item()
            return cats[idx], sim[idx].item()