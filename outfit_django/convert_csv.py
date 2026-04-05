# convert_csv.py
import pandas as pd
from pathlib import Path

csv_path = Path('/outfit_django/data/metadata_enriched.csv')

# Читаем с автоопределением кодировки
with open(csv_path, 'rb') as f:
    raw = f.read(10000)

# Пробуем определить кодировку
import chardet

encoding = chardet.detect(raw)['encoding']
print(f"Detected encoding: {encoding}")

# Читаем и сохраняем в UTF-8
df = pd.read_csv(csv_path, encoding=encoding)
df.to_csv(csv_path, encoding='utf-8', index=False)
print("Converted to UTF-8!")