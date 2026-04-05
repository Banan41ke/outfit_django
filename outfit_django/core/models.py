from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    name_ru = models.CharField(max_length=50)
    emoji = models.CharField(max_length=10, default='👕')

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name_ru


class Item(models.Model):
    filename = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    color_r = models.IntegerField()
    color_g = models.IntegerField()
    color_b = models.IntegerField()
    embedding = models.JSONField(null=True, blank=True)
    image = models.ImageField(upload_to='items/', null=True, blank=True)

    def __str__(self):
        return f"{self.category.name_ru} - {self.filename}"

    @property
    def color_hex(self):
        return f'#{self.color_r:02x}{self.color_g:02x}{self.color_b:02x}'


class CartItem(models.Model):
    session_key = models.CharField(max_length=40)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['session_key', 'item']


class FavoriteItem(models.Model):
    session_key = models.CharField(max_length=40)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['session_key', 'item']