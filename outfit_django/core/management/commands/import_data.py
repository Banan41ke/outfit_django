from django.core.management.base import BaseCommand
import pandas as pd
from pathlib import Path
from core.models import Category, Item


class Command(BaseCommand):
    help = 'Import items from pickle file'

    def handle(self, *args, **kwargs):
        # Создаём категории
        categories = {
            'tops': Category.objects.get_or_create(name='tops', defaults={'name_ru': 'Верх', 'emoji': '👕'})[0],
            'bottoms': Category.objects.get_or_create(name='bottoms', defaults={'name_ru': 'Низ', 'emoji': '👖'})[0],
            'shoes': Category.objects.get_or_create(name='shoes', defaults={'name_ru': 'Обувь', 'emoji': '👟'})[0],
            'accessories':
                Category.objects.get_or_create(name='accessories', defaults={'name_ru': 'Аксессуар', 'emoji': '👜'})[0],
        }

        # Загружаем pickle файл
        pickle_path = Path('/outfit_django/data/metadata_enriched.csv')

        try:
            df = pd.read_pickle(pickle_path)
            self.stdout.write(f"Loaded pickle! Shape: {df.shape}")
            self.stdout.write(f"Columns: {list(df.columns)}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to load pickle: {e}'))
            return

        # Сохраняем как CSV для будущего использования (опционально)
        csv_path = pickle_path.with_suffix('.csv')
        df.to_csv(csv_path, index=False, encoding='utf-8')
        self.stdout.write(f"Saved as CSV: {csv_path}")

        # Импортируем в базу
        imported = 0
        for _, row in df.iterrows():
            try:
                Item.objects.get_or_create(
                    filename=row['filename'],
                    defaults={
                        'category': categories[row['category']],
                        'color_r': int(row.get('color_r', 128)),
                        'color_g': int(row.get('color_g', 128)),
                        'color_b': int(row.get('color_b', 128)),
                    }
                )
                imported += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Skip {row.get("filename", "unknown")}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Imported {imported} items! Total in DB: {Item.objects.count()}'))