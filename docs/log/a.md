## 2026-08-15 14:20 — fix/a-seed-and-migrations
- Сделано: Успешно завершен Блок 0 для БД и задача A0. Исправлены конфликты миграций GeoAlchemy, исправлены ошибки транзакций SQLAlchemy, перемещены скрипты инициализации в правильную папку. Выполнен сидинг административных единиц и тестовых метрик (756 записей).
- Файлы: geointel/db/migrations/versions/001_initial.py, geointel/scripts/ingest_admin_units.py, geointel/scripts/seed_dev_metrics.py
- Решения: Удалил `op.create_index` для колонок `Geometry`, так как GeoAlchemy2 автоматически создает `gist` индексы. Добавил `db.commit()` перед `db.begin()` для совместимости с авто-транзакциями SQLAlchemy 2.0.
- Незакрытое: скрипт `ingest_cropland_mask.py` является заглушкой, требуется реализация `ee.Initialize()` и вычислений в Earth Engine (задачи A1 и A2).
## 2026-08-15 14:30 — feat/a-gee-providers
- Сделано: A1 (границы и маска пашни) и A2 (провайдеры GEE). Создан `geointel/providers/base.py` с контрактами. Добавлен синглтон инициализации GEE в `gee.py`. Написан `ingest_cropland_mask.py` с выгрузкой площади пашни по районам.
- Файлы:
  - `geointel/providers/base.py`
  - `geointel/providers/gee.py`
  - `geointel/providers/vegetation/sentinel2.py`
  - `geointel/providers/vegetation/modis.py`
  - `geointel/scripts/ingest_cropland_mask.py`
- Решения: Инициализация Earth Engine происходит лениво при вызове `initialize()`. Площадь вычисляется как сумма пикселей `ee.Image.pixelArea()`, умноженная на маску ESA WorldCover. Для Sentinel-2 NDVI считаем облачную маску по `SCL` и вычисляем fraction of valid pixels как `quality`. Все провайдеры используют общую функцию `reduce_regions` для агрегации метрик по районам.
- Незакрытое: `GEE_SERVICE_ACCOUNT_JSON` пуст в `.env`, требуется настройка окружения для запуска и проверки руками.

## 2026-08-15 14:52 — feat/a-indices-batch
- Сделано: A3 (реализация `domain/indices.py` для индексов VCI, TCI, VHI) и A4 (батч `batch/run_daily.py` для вычисления метрик по историческим данным и загрузки в базу). Исправлены все ошибки mypy и ruff, тесты проходят.
- Файлы:
  - `geointel/domain/indices.py`
  - `tests/test_indices.py`
  - `geointel/batch/run_daily.py`
- Решения: Использован `on_conflict_do_update` для `upsert_metrics`, чтобы обновлять уже посчитанные декады. Взяты исторические экстремумы (min, max) для расчета VCI и TCI, при отсутствии истории используются текущие значения.
- Незакрытое: Убедиться, что крон/scheduler корректно запускает `run_daily.py`.
