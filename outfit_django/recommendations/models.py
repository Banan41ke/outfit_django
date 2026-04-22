from django.db import models


class ClothingItem(models.Model):
    """Идеальная модель для хранения одежды, обуви и их признаков (CLIP)"""

    GENDER_CHOICES = [
        ('M', 'Мужское'),
        ('F', 'Женское'),
        ('U', 'Унисекс'),
    ]

    CATEGORY_CHOICES = [
        ('tops', 'Верхняя одежда'),
        ('bottoms', 'Брюки и шорты'),
        ('shoes', 'Обувь'),
        ('accessories', 'Аксессуары'),
    ]

    # ❗ id НЕ ТРОГАЕМ — Django сам создаёт AutoField
    # id = models.AutoField(primary_key=True)  ← УДАЛИТЬ ЭТУ СТРОКУ

    # 🔥 ВАЖНОЕ ПОЛЕ (твой mad_307940)
    external_id = models.CharField(max_length=100, unique=True, verbose_name="Внешний ID")

    name = models.CharField(max_length=500, verbose_name="Название товара")

    # Категория и пол
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Категория")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U', verbose_name="Пол")

    # Стиль
    style_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Стиль")

    # Изображения
    image_path = models.CharField(max_length=500, verbose_name="Путь к локальному файлу")
    image_url = models.URLField(max_length=1000, blank=True, verbose_name="Ссылка на фото")

    # Цвет
    color_name = models.CharField(max_length=100, blank=True, verbose_name="Цвет")
    color_rgb = models.JSONField(default=list, blank=True)

    # Магазин
    store = models.CharField(max_length=100, blank=True, verbose_name="Магазин")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Цена")
    currency = models.CharField(max_length=10, default='BYN', verbose_name="Валюта")
    product_url = models.URLField(max_length=1000, blank=True, verbose_name="Ссылка на товар")

    # CLIP
    embedding = models.BinaryField(null=True, blank=True, verbose_name="Вектор CLIP")

    # Технические
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Предмет одежды"
        verbose_name_plural = "Предметы одежды"
        indexes = [
            models.Index(fields=['category', 'gender', 'is_active']),
            models.Index(fields=['store', 'category']),
        ]

    def __str__(self):
        return f"{self.name} | {self.get_gender_display()} | {self.store}"


class UserQuery(models.Model):
    """Модель для хранения запросов пользователей и выданных рекомендаций"""

    user_id = models.CharField(max_length=100, verbose_name="ID пользователя")
    chat_id = models.CharField(max_length=100, verbose_name="ID чата")

    query_image = models.ImageField(upload_to='queries/%Y/%m/', verbose_name="Запрос (фото)")

    detected_category = models.CharField(
        max_length=20,
        choices=ClothingItem.CATEGORY_CHOICES,
        blank=True
    )
    detected_gender = models.CharField(
        max_length=1,
        choices=ClothingItem.GENDER_CHOICES,
        blank=True
    )

    recommendations = models.ManyToManyField(
        ClothingItem,
        related_name='queries',
        verbose_name="Результаты"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Запрос пользователя"
        verbose_name_plural = "Запросы пользователей"
        ordering = ['-created_at']

    def __str__(self):
        return f"Запрос {self.user_id} от {self.created_at.strftime('%d.%m %H:%M')}"