import os
import uuid
from django.shortcuts import render, redirect
from django.views import View
from django.conf import settings
from .services.matcher_service import OutfitMatcherService


class MainView(View):
    def get(self, request):
        # Очищаем старые данные при заходе на главную
        request.session.pop('recommendations', None)
        request.session.pop('uploaded_photo', None)
        request.session.pop('query_category', None)
        request.session.pop('confidence', None)
        request.session.pop('error', None)

        return render(request, 'recommendations/main.html')

    def post(self, request):
        if 'photo' not in request.FILES:
            return redirect('main')

        photo = request.FILES['photo']

        # Создаём уникальное имя файла
        ext = photo.name.split('.')[-1]
        filename = f"{uuid.uuid4()}.{ext}"

        # Путь для сохранения
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, filename)

        # Сохраняем файл
        with open(temp_path, 'wb+') as destination:
            for chunk in photo.chunks():
                destination.write(chunk)

        # Получаем рекомендации
        try:
            matcher = OutfitMatcherService()
            result = matcher.get_recommendations(temp_path, top_k=6)

            # Сохраняем в сессию ВСЕ данные
            request.session['recommendations'] = result['recommendations']
            request.session['uploaded_photo'] = f"temp/{filename}"  # Относительный путь
            request.session['query_category'] = result['query_category']
            request.session['confidence'] = float(result['confidence'])
            request.session['error'] = None

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            request.session['error'] = str(e)
            request.session['recommendations'] = {}
            request.session['uploaded_photo'] = f"temp/{filename}"
            request.session['query_category'] = 'unknown'
            request.session['confidence'] = 0

        # Редирект на страницу результатов
        return redirect('results')


class ResultsView(View):
    def get(self, request):
        # Получаем данные из сессии
        context = {
            'photo_url': request.session.get('uploaded_photo', ''),
            'query_category': request.session.get('query_category', ''),
            'confidence': request.session.get('confidence', 0),
            'recommendations': request.session.get('recommendations', {}),
            'error': request.session.get('error', None),
        }

        # Перевод категорий
        category_names = {
            'tops': 'ВЕРХ',
            'bottoms': 'НИЗ',
            'shoes': 'ОБУВЬ',
            'accessories': 'АКСЕССУАРЫ'
        }
        context['category_names'] = category_names

        return render(request, 'recommendations/results.html', context)


class CategoryDetailView(View):
    def get(self, request, category_name):
        recommendations = request.session.get('recommendations', {})
        items = recommendations.get(category_name, [])

        category_names = {
            'tops': 'ВЕРХ',
            'bottoms': 'НИЗ',
            'shoes': 'ОБУВЬ',
            'accessories': 'АКСЕССУАРЫ'
        }

        context = {
            'category_name': category_name,
            'category_name_ru': category_names.get(category_name, category_name),
            'items': items,
        }
        return render(request, 'recommendations/category.html', context)