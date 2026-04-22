import os
import uuid
from django.shortcuts import render, redirect
from django.views import View
from django.conf import settings
from .services.matcher_service import OutfitMatcherService
from .models import ClothingItem


class MainView(View):
    def get(self, request):
        keys_to_pop = ['recommendations', 'uploaded_photo', 'query_category', 'confidence', 'error']
        for key in keys_to_pop:
            request.session.pop(key, None)
        return render(request, 'recommendations/main.html')

    def post(self, request):
        if 'photo' not in request.FILES:
            return redirect('main')

        photo = request.FILES['photo']
        ext = photo.name.split('.')[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, filename)

        with open(temp_path, 'wb+') as destination:
            for chunk in photo.chunks():
                destination.write(chunk)

        try:
            matcher = OutfitMatcherService()
            result = matcher.get_recommendations(temp_path, top_k=6)

            # Исправляем confidence (умножаем на 100 если в долях)
            raw_confidence = float(result.get('confidence', 0))
            confidence = raw_confidence * 100 if raw_confidence <= 1 else raw_confidence

            # Обогащаем данными из БД
            processed_recs = {}
            for category, items in result.get('recommendations', {}).items():
                processed_items = []
                for item in items:
                    if isinstance(item, dict):
                        if 'image_path' in item:
                            item['image_path'] = item['image_path'].replace('\\', '/')
                        self._enrich_from_db(item)
                    processed_items.append(item)
                processed_recs[category] = processed_items

            request.session['recommendations'] = processed_recs
            request.session['uploaded_photo'] = f"temp/{filename}"
            request.session['query_category'] = result.get('query_category', 'unknown')
            request.session['confidence'] = confidence
            request.session['error'] = None

        except Exception as e:
            print(f"Error during matching: {e}")
            import traceback
            traceback.print_exc()
            request.session['error'] = str(e)
            request.session['recommendations'] = {}
            request.session['uploaded_photo'] = f"temp/{filename}"
            request.session['query_category'] = 'error'
            request.session['confidence'] = 0

        return redirect('results')

    def _enrich_from_db(self, item: dict):
        """Подтягивает данные из БД парсера и синхронизирует пути/категории"""

        # 1. Получаем имя файла из доступных полей
        file_name = (item.get('image_path')
                     or item.get('name')
                     or item.get('filename')
                     or '')
        file_name = file_name.replace('\\', '/').split('/')[-1]  # только имя файла

        # 2. Чистый ID для поиска (mad_316775.webp → mad_316775)
        base_name = file_name.replace('.jpg', '').replace('.webp', '').replace('.png', '')
        clean_id = base_name
        if '_' in clean_id:
            parts = clean_id.split('_')
            if parts[0] in ['tops', 'bottoms', 'shoes', 'accessories']:
                clean_id = '_'.join(parts[1:])

        if not clean_id:
            return

        # 3. Поиск в БД
        db_item = None
        try:
            # По external_id (точное совпадение)
            db_item = ClothingItem.objects.filter(external_id=clean_id).first()
            # Если не нашли — ищем по концу пути
            if not db_item:
                db_item = ClothingItem.objects.filter(image_path__endswith=file_name).first()
            # Если не нашли — ищем по имени
            if not db_item:
                db_item = ClothingItem.objects.filter(name__icontains=clean_id).first()
        except Exception as e:
            print(f"DB lookup error: {e}")

        # 4. Обогащение и СИНХРОНИЗАЦИЯ
        if db_item:
            item['name'] = db_item.name or clean_id
            item['price'] = str(db_item.price) if db_item.price else None
            item['currency'] = db_item.currency
            item['store'] = db_item.store
            item['product_url'] = db_item.product_url
            item['image_url'] = db_item.image_url
            item['color_name'] = db_item.color_name

            # 🔥 КЛЮЧЕВОЕ: принудительная синхронизация с БД
            item['gender'] = db_item.gender
            item['category'] = db_item.category

            item['product_url'] = db_item.product_url  # ← точно есть?

            print(f"✅ DB found: {item['name']} | url={item.get('product_url', 'NO')[:50]}")

            # 🔥 НОРМАЛИЗАЦИЯ ПУТИ: убираем BASE_DIR, делаем относительным
            raw_path = db_item.image_path or ''
            if raw_path:
                base_dir_str = str(settings.BASE_DIR).replace('\\', '/')
                raw_path = raw_path.replace('\\', '/')
                if raw_path.startswith(base_dir_str):
                    raw_path = raw_path[len(base_dir_str):].lstrip('/')

            item['image_path'] = raw_path  # Теперь: data/raw/M/tops/mad_308590.jpg

            print(
                f"✅ DB found: {item['name']} | gender={item['gender']} | cat={item['category']} | path={item['image_path']}")
        else:
            print(f"❌ DB NOT found for: {clean_id} (file: {file_name})")


class ResultsView(View):
    def get(self, request):
        recommendations = request.session.get('recommendations', {})

        # ===== ОТЛАДКА =====
        print("\n" + "=" * 50)
        print("=== RECOMMENDATIONS DEBUG ===")
        print(f"Categories in recommendations: {list(recommendations.keys())}")
        print(f"Query category: {request.session.get('query_category', 'unknown')}")
        print(f"Number of categories: {len(recommendations)}")
        for cat, items in recommendations.items():
            print(f"  {cat}: {len(items)} items")
            for item in items[:3]:
                print(f"  - {item.get('name')} (category в item: {item.get('category')})")
        print("=" * 50 + "\n")
        # ===== КОНЕЦ ОТЛАДКИ =====

        context = {
            'photo_url': request.session.get('uploaded_photo', ''),
            'query_category': request.session.get('query_category', ''),
            'confidence': request.session.get('confidence', 0),
            'recommendations': recommendations,
            'error': request.session.get('error', None),
        }

        context['category_names'] = {
            'tops': 'ВЕРХ',
            'bottoms': 'НИЗ',
            'shoes': 'ОБУВЬ',
            'accessories': 'АКСЕССУАРЫ'
        }

        return render(request, 'recommendations/results.html', context)


class CategoryDetailView(View):
    def get(self, request, category_name):
        recommendations = request.session.get('recommendations', {})
        items = recommendations.get(category_name, [])
        # В recommendations/views.py
        print("=== RECOMMENDATIONS DEBUG ===")
        print(f"Categories in recommendations: {recommendations.keys()}")
        print(f"Full recommendations: {recommendations}")
        category_display_names = {
            'tops': 'ВЕРХ',
            'bottoms': 'НИЗ',
            'shoes': 'ОБУВЬ',
            'accessories': 'АКСЕССУАРЫ'
        }

        context = {
            'category_name': category_name,
            'category_name_ru': category_display_names.get(category_name, category_name.upper()),
            'items': items,
        }
        return render(request, 'recommendations/category.html', context)

