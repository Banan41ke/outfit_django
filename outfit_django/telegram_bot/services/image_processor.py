"""Обработка изображений"""
import os
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import aiohttp


class ImageProcessor:
    """Обработчик изображений"""

    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(exist_ok=True)

    async def download_photo(self, file_id: str, bot) -> Optional[Path]:
        """Скачивает фото из Telegram"""
        try:
            file = await bot.get_file(file_id)
            file_path = file.file_path

            # Определяем расширение
            ext = Path(file_path).suffix or '.jpg'
            local_path = self.temp_dir / f"{file_id}{ext}"

            # Скачиваем
            await bot.download_file(file_path, local_path)

            return local_path

        except Exception as e:
            print(f"Error downloading photo: {e}")
            return None

    def validate_image(self, image_path: Path) -> Tuple[bool, str]:
        """Проверяет изображение"""
        # Проверка существования
        if not image_path.exists():
            return False, "Файл не найден"

        # Проверка размера
        size = image_path.stat().st_size
        if size > 20 * 1024 * 1024:  # 20 MB
            return False, "file_too_large"

        # Проверка формата
        try:
            with Image.open(image_path) as img:
                format = img.format.lower()
                if format not in ['jpeg', 'jpg', 'png', 'webp']:
                    return False, "invalid_format"

                # Проверка размеров (минимум 200x200)
                if img.width < 200 or img.height < 200:
                    return False, "Слишком маленькое изображение (мин. 200x200)"

                return True, "OK"

        except Exception as e:
            return False, f"Ошибка чтения изображения: {e}"

    def optimize_image(self, image_path: Path, max_size: int = 1024) -> Path:
        """Оптимизирует изображение для быстрой обработки"""
        try:
            with Image.open(image_path) as img:
                # Конвертируем в RGB если нужно
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # Масштабируем если слишком большое
                if max(img.width, img.height) > max_size:
                    ratio = max_size / max(img.width, img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                # Сохраняем оптимизированную версию
                optimized_path = image_path.parent / f"opt_{image_path.name}"
                img.save(optimized_path, 'JPEG', quality=85, optimize=True)

                return optimized_path

        except Exception as e:
            print(f"Optimization error: {e}")
            return image_path

    def cleanup(self, *paths: Path):
        """Удаляет временные файлы"""
        for path in paths:
            try:
                if path.exists():
                    path.unlink()
            except Exception as e:
                print(f"Cleanup error: {e}")