# GeoIntel — промпты для бэкенда

Только бэкенд: данные, расчёты, база, API. Фронтенд и дизайн — отдельным этапом.

Блок 0 делаете вдвоём, это первый час: контракты и схема базы. Блоки A и B после этого идут параллельно и независимо.

Вставлять целиком, вместе с шапкой контекста.

---

# БЛОК 0 — совместный каркас и контракты

> Результат мержится в `main` до начала параллельной работы.

```
Ты помогаешь собрать бэкенд проекта GeoIntel — мониторинг засухи и прогноз
урожайности по Кыргызстану на спутниковых данных.

КОНТЕКСТ
Команда из двух разработчиков, работаем параллельно в одном репозитории на GitHub.
Дедлайн: 17 августа 2026, 22:00 по Бишкеку.

Цель этого шага — зафиксировать контракты и схему базы, чтобы дальше два
человека писали код параллельно. Бизнес-логика идёт следующим шагом.

Прочитай AGENTS.md и PROJECT.md перед началом.

СТЕК
Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, PostgreSQL 16 + PostGIS,
alembic, ruff, mypy, pytest. Пакетный менеджер uv.

Готовые сервисы вместо своего кода: Firebase Auth — авторизация,
Resend — почта, Google Earth Engine — расчёты по растрам, WeasyPrint — PDF.
Свои реализации этих задач не пишем.

СТРУКТУРА

geointel/
  contracts/        scope.py, metrics.py, plans.py     # замораживается
  providers/        base.py, gee.py
  domain/           decade.py
  batch/
  db/               session.py, models/, migrations/
  api/              main.py, errors.py
  services/
  i18n/             ru.json, ky.json, en.json
  scripts/
  tests/
docker-compose.yml, Makefile, pyproject.toml, .env.example, .gitignore

ЧТО НАПИСАТЬ

1) contracts/scope.py

class Scope(str, Enum):
    COUNTRY, OBLAST, DISTRICT, FIELD

Метод is_finer_than(other) -> bool. Порядок от крупной к мелкой:
COUNTRY, OBLAST, DISTRICT, FIELD.

2) contracts/metrics.py — замороженный реестр метрик.

frozen dataclass MetricDef:
    id, source, native_resolution_m, min_scope, unit,
    higher_is_better, decimals

METRICS: dict[str, MetricDef]:

  ndvi           Sentinel-2 SR Harmonized   10     FIELD      ratio   выше=лучше  3
  ndvi_hist      MODIS MOD13Q1              250    DISTRICT   ratio   выше=лучше  3
  lst            MODIS MOD11A2              1000   DISTRICT   °C      ниже=лучше  1
  vci            производная                250    DISTRICT   0-100   выше=лучше  1
  tci            производная                1000   DISTRICT   0-100   выше=лучше  1
  vhi            производная                1000   DISTRICT   0-100   выше=лучше  1
  spi_1          CHIRPS Daily               5000   DISTRICT   sigma   выше=лучше  2
  spi_3          CHIRPS Daily               5000   DISTRICT   sigma   выше=лучше  2
  soil_moisture  SMAP L4 SPL4SMGP           9000   DISTRICT   m3/m3   выше=лучше  3
  ndwi           Sentinel-2                 10     FIELD      ratio   выше=лучше  3
  yield_wheat    регрессия                  250    DISTRICT   c/ha    выше=лучше  1

soil_moisture имеет min_scope DISTRICT, а не FIELD: 9 км на пиксель это
8100 гектаров. Объясни это комментарием на английском в коде.

Функция assert_scope_allowed(metric_id, scope) -> None, кидает ScopeTooFineError.

3) contracts/plans.py — тарифы.

class Plan(str, Enum): TRIAL, FARMER, FARM, ORG

frozen dataclass PlanDef: id, max_fields, price_tiyin_month, features: frozenset

  TRIAL   1 участок    0            статус засухи, прогноз погоды 7 дней
  FARMER  5 участков   40000        + история сезона, письма при переходе порога
  FARM    50 участков  250000       + прогноз урожайности, выгрузка
  ORG     без лимита   2000000      + район или область целиком

Цены в тыйынах. Бесплатный тариф ограничен количеством участков, а не временем.

Функция can_use(plan, feature) -> bool и assert_field_limit(plan, current_count).

4) db/migrations/001_initial — вся схема одной миграцией.

admin_unit(id PK, parent_id FK, level, name_ru, name_ky, name_en,
           geom geometry(MultiPolygon,4326), cropland_ha, created_at)
customer(id PK, auth_uid UNIQUE, email UNIQUE, name, phone, org,
         plan, lang, created_at)
field(id PK, customer_id FK, name, crop, sowing_date, area_ha,
      cropland_ha, geom geometry(Polygon,4326), center geometry(Point,4326),
      radius_m, district_id FK, created_at)
metric_value(unit_id FK, metric_id, decade_start date, value, quality,
             computed_at, PK(unit_id, metric_id, decade_start))
field_metric(field_id FK, metric_id, decade_start date, value,
             PK(field_id, metric_id, decade_start))
yield_forecast(id PK, unit_id FK, crop, season_year, value, lo, hi,
               model_version, computed_at)
weather_forecast(id PK, field_id FK, issued_at, payload_json jsonb)
alert(id PK, unit_id FK NULL, field_id FK NULL, metric_id, decade_start,
      severity, state, notified_at, created_at)
agent_event(id PK, agent, action, subject, payload_json jsonb, status, created_at)
invoice(id PK, customer_id FK, plan, amount_tiyin bigint, status,
        issued_at, paid_at, confirmed_by)
report(id PK, customer_id FK, scope, subject_id, decade_start,
       storage_path, lang, created_at)

Индексы: metric_value(metric_id, decade_start), agent_event(created_at desc),
invoice(status), GIST по всем geometry.
Все timestamp timezone aware, хранение в UTC.

5) providers/base.py — только протоколы, без реализаций.

class RasterProvider(Protocol):
    metric_id: str
    def fetch(self, units: list[AdminUnitRef], start: date, end: date)
        -> dict[int, MeasuredValue]

MeasuredValue: frozen dataclass, value: float, quality: float в 0..1.

6) domain/decade.py — арифметика декад: 1-10, 11-20, 21-конец месяца.
Функции: decade_of(date), decade_start(date), previous_decade(d),
decade_range(start, end), same_decade_of_year(d, year). Полные тесты.

7) i18n/ — три каталога ru.json, ky.json, en.json и функция t(key, lang).
Отсутствующий перевод падает на русский, а не показывает голый ключ.
Заведи начальные ключи: errors.*, alerts.*, email.*, report.*

8) docker-compose.yml — postgis/postgis:16-3.4.
   Makefile — up, down, migrate, seed, dev, batch, check, fmt.
   pyproject.toml — ruff line-length 100, mypy strict для domain/ и contracts/.
   .env.example — DATABASE_URL, GEE_SERVICE_ACCOUNT_JSON, GEE_PROJECT,
   GEMINI_API_KEY, FIREBASE_PROJECT_ID, FIREBASE_CREDENTIALS_JSON,
   RESEND_API_KEY, MAIL_FROM, OPENMETEO_BASE_URL, APP_ENV, TZ_DISPLAY,
   PAYMENT_DETAILS_JSON

9) api/main.py — приложение FastAPI, только /health со статусом базы.

10) tests/test_contracts.py — assert_scope_allowed кидает для soil_moisture
    на Scope.FIELD и не кидает на Scope.DISTRICT. Плюс тесты на лимиты тарифов.

ЧЕГО НЕ ДЕЛАТЬ НА ЭТОМ ШАГЕ
Бизнес-логику, роутеры кроме /health, подключение Earth Engine, заглушечные данные.

ПОСЛЕ РАБОТЫ
make check зелёный. Запись в docs/log/a.md.
```

---

# БЛОК A — разработчик «Данные»

```
Ты работаешь над бэкендом GeoIntel как разработчик A, зона ответственности «Данные».

ПЕРЕД НАЧАЛОМ
Прочитай AGENTS.md и PROJECT.md. Ты владеешь каталогами providers/,
domain/, batch/, scripts/ и файлами tests/test_indices.py, tests/test_decade.py,
tests/test_providers.py. Файлы разработчика B не редактируй ни при каких
обстоятельствах: нужна правка там — запиши в лог и продолжай без неё.
contracts/ заморожены.

Ветки feat/a-*. Перед пушем git pull --rebase origin main.
Веди docs/log/a.md в реальном времени.
Весь код, комментарии и коммиты — на английском.

ПРЕДМЕТНАЯ ОБЛАСТЬ
Кыргызстан: 7 областей плюс Бишкек и Ош, 40 районов. 90% территории — горы,
поэтому индексы считаются ТОЛЬКО по пикселям пашни.
Единица времени — декада, не неделя: под неё построены композиты MODIS.

КЛИЕНТЫ
Фермеры и агропредприятия. Продукт отвечает на вопросы полива, обработок,
сроков сева и уборки.

ЗАДАЧИ

--- A0. Разблокировать напарника. Делай это ПЕРВЫМ, 30 минут ---

scripts/seed_dev_metrics.py — наполняет metric_value правдоподобными
значениями по всем районам за последние 12 декад.
Юг (Баткен, Ош) — низкие VHI (18-35), север (Чуй, Иссык-Куль) — высокие (50-65).

Разработчик B строит на этих данных API и не ждёт твоего батча.

Скрипт обязан отказываться работать при APP_ENV != "local", явной проверкой
с понятным сообщением. В продакшене заглушек быть не должно.

--- A1. Границы и маска пашни ---

scripts/ingest_admin_units.py
  geoBoundaries или FAO GAUL, уровни ADM1 и ADM2, иерархия через parent_id.
  Заполни name_ru, name_ky, name_en. Кыргызские названия проверь глазами:
  автоматическая транслитерация даёт ошибки в топонимах.

scripts/ingest_cropland_mask.py
  ESA WorldCover 2021, класс 40 (cropland). Площадь пашни в гектарах
  по каждому району в cropland_ha. Маску сохрани как переиспользуемый
  ee.Image в providers/.

Проверка руками: в Чуйской области пашни в разы больше, чем в Нарынской.
Если наоборот — ошибка в маске, дальше не иди.

--- A2. Провайдеры ---

providers/gee.py — ЕДИНСТВЕННОЕ место вызова ee.Initialize(),
через сервисный аккаунт из переменной окружения. Нигде больше.

providers/vegetation/sentinel2.py — NDVI по Sentinel-2 SR Harmonized,
  облачная маска по SCL, медианный композит за декаду.
providers/vegetation/modis.py — NDVI по MOD13Q1, LST по MOD11A2.

Оба реализуют RasterProvider. Агрегация — среднее по пикселям пашни
внутри границы. quality = доля валидных пикселей после облачной маски.

--- A3. Индексы. Это ядро продукта ---

domain/indices.py

VCI = 100 * (NDVI - NDVI_min) / (NDVI_max - NDVI_min)
TCI = 100 * (LST_max - LST) / (LST_max - LST_min)
VHI = 0.5 * VCI + 0.5 * TCI

КРИТИЧНО: экстремумы берутся по ТОЙ ЖЕ ДЕКАДЕ ГОДА за 2000-2025 по MODIS,
а не за весь период. Иначе август сравнивается с маем.

Пороги VHI именованными константами:
  <30 экстремальная, 30-40 сильная, 40-45 умеренная, 45-60 норма, >60 благоприятно

domain/ не импортирует earthengine-api: получает массивы чисел, возвращает числа.

tests/test_indices.py — фиксированные числа, без GEE. Граничные случаи:
NDVI_max == NDVI_min (деление на ноль), значения за пределами исторических
экстремумов (клампить в 0..100), пропуски данных.

--- A4. Батч ---

batch/run_daily.py — Cloud Run Job, ежедневно в 04:00 по Бишкеку.

Шаги в batch/steps/:
  1. определить текущую декаду
  2. собрать сырые значения по всем районам через провайдеры
  3. посчитать индексы
  4. upsert в metric_value по первичному ключу
  5. сравнить VHI с порогом и с предыдущей декадой, создать alert
  6. агрегировать районы до областей и страны, взвешивая по cropland_ha

КАЖДЫЙ ШАГ ПИШЕТ В agent_event В МОМЕНТ ВЫПОЛНЕНИЯ, а не пачкой в конце.
agent="monitor", в payload_json вход и выход решения.

Батч идемпотентен: повторный запуск за ту же декаду перезаписывает,
а не дублирует.

--- A5. Осадки ---

providers/precipitation/chirps.py — суммы по декадам из CHIRPS Daily.
domain/indices.py — SPI за 1 и 3 месяца: стандартизация относительно
распределения за 1981-2025 по той же календарной позиции.

--- A6. Прогноз урожайности ---

domain/yield_model.py — линейная регрессия: интеграл NDVI за апрель-июль
→ урожайность ц/га. Обучение на статистике Нацстаткома по районам.

Не строй нейросеть. Регрессия даёт R² порядка 0.6-0.75 и считается за час.
ВСЕГДА возвращай доверительный интервал lo и hi, никогда одну точку.
Сохраняй версию модели вместе с прогнозом.

--- A7. Прогноз погоды ---

providers/weather/openmeteo.py — почасовой прогноз на 7 суток по координатам:
осадки, ветер, температура. Это отдельный источник от CHIRPS:
CHIRPS — история, Open-Meteo — прогноз.

Посчитай производные окна, в них и есть ценность для фермера:
  - ближайшее окно без дождя длиной от 6 часов
  - ближайшее окно с ветром до 4 м/с (опрыскивание)
  - риск заморозка в ближайшие 7 суток
Результат пиши в weather_forecast.

--- A8. Опционально, только если остаётся время ---

providers/soil/smap.py — SMAP L4 SPL4SMGP, влажность корнеобитаемого слоя, 9 км.
providers/soil/era5_land.py — тот же интерфейс, запасной источник.

Источник выбирается конфигом, не импортом в бизнес-логике: у SMAP плановый
конец миссии сентябрь 2026, подмена должна быть правкой одной строки.

ГОТОВНОСТЬ
make check зелёный, запись в docs/log/a.md, результат проверен глазами
на реальных данных.
```

---

# БЛОК B — разработчик «Сервис»

```
Ты работаешь над бэкендом GeoIntel как разработчик B, зона ответственности «Сервис».

ПЕРЕД НАЧАЛОМ
Прочитай AGENTS.md и PROJECT.md. Ты владеешь каталогами db/, api/,
services/, i18n/, deploy/ и файлами tests/test_api.py, tests/test_scope_rules.py,
tests/test_billing.py. Каталоги providers/, domain/, batch/, scripts/
принадлежат разработчику A — не редактируй. contracts/ заморожены.

Ветки feat/b-*. Перед пушем git pull --rebase origin main.
Веди docs/log/b.md в реальном времени.
Весь код, комментарии и коммиты — на английском. Пользовательские тексты —
через каталоги i18n, а не строками в коде.

КЛИЕНТЫ
Фермеры и агропредприятия.

НЕЗАВИСИМОСТЬ
Ты не ждёшь разработчика A. Единственная точка стыка — таблица metric_value.
A даст scripts/seed_dev_metrics.py в первые полчаса, работай на этих данных.

ЗАДАЧИ

--- B1. Слой данных ---

db/models/ — SQLAlchemy-модели по схеме из 001_initial, разнесённые
по файлам metrics.py, customer.py, billing.py, ops.py.
НЕ делай один models.py: он станет точкой конфликтов.

db/repositories/ — типизированные методы. Сырого SQL в роутерах нет.

Пространственные запросы через PostGIS. Для точки с радиусом — ST_DWithin
по ГЕОГРАФИЧЕСКОМУ типу, не по планарному: иначе радиус в Кыргызстане врёт.

--- B2. Основные эндпоинты ---

GET /api/units?level=oblast|district&decade=2026-08-01
GET /api/units/{id}?decade=...        карточка: метрики, прогноз, соседние декады
GET /api/units/{id}/series?metric=vhi&from=2026-05-01
GET /api/alerts?since=...

Каждый ответ содержит decade_start и quality.
Никаких вычислений в API — только чтение того, что посчитал батч.
Язык ответа: из профиля клиента, иначе из Accept-Language, по умолчанию ru.

--- B3. Геометрия ---

GET /api/geo/units.geojson?level=oblast

Предрассчитанный GeoJSON, упрощённый по Дугласу-Пекеру. Геометрия не меняется,
поэтому ETag и Cache-Control на сутки. Не отдавай полную геометрию
из PostGIS на каждый запрос.

--- B4. Правило min_scope. Блокирующее требование ---

api/errors.py + tests/test_scope_rules.py

Запрос метрики на географии мельче её min_scope → 422:

{"error": "scope_too_fine", "metric": "soil_moisture",
 "min_scope": "district", "requested": "field",
 "reason": "Native resolution 9000 m is too coarse for field-level display"}

Не null, не значение с оговоркой. Именно отказ.
Причина: SMAP даёт 9 км на пиксель — 8100 гектаров, туда попадут поля,
склоны и камни. Тесты обязательны.

--- B5. Регистрация и участки ---

services/registration.py + api/routers/fields.py

Авторизация — Firebase Auth (Google Identity Platform). Свою систему паролей
НЕ пишем: ни хеширования, ни подтверждения почты, ни восстановления доступа.

Бэкенд проверяет ID-токен Firebase в api/deps.py и по auth_uid находит или
создаёт запись в customer. Вход через Google-аккаунт и через email-ссылку.
При первом входе спрашивается язык интерфейса.

Создание участка: точка на карте, радиус, КУЛЬТУРА и ДАТА СЕВА.
Культура спрашивается ДО анализа, а не после: от неё зависят фазы развития,
пороги температур и водопотребление.

При создании:
  - пересеки круг с маской пашни, посчитай реальную площадь пашни внутри
  - сохрани обе площади: площадь круга и площадь пашни в нём
  - определи район по центру
  - проверь лимит участков по тарифу через contracts/plans.py

В ответе честно верни обе площади. Если пашни в круге меньше 20% — подсказка
обвести участок точнее.

--- B6. Gemini ---

services/gemini.py + POST /api/explain

Вход: scope, subject_id, decade, lang (ru, ky, en).
Модель получает значения метрик, динамику за последние декады, пороги
и прогноз урожайности. Возвращает связный текст для фермера.

Требования:
  - низкая температура: нужна фактическая точность, а не красота
  - в системной инструкции ЗАПРЕТ называть любые числа, которых нет во входе
  - результат кэшируется по ключу (scope, subject_id, decade, lang):
    не дёргай API на каждый заход в карточку
  - каждый вызов пишет agent_event с agent="narrator"

--- B7. Почта ---

services/email.py — отправка через Resend по API. Свой SMTP не поднимаем:
настройка домена, SPF и DKIM съедает полдня.
HTML-письма по шаблонам, на языке клиента.

Письма: подтверждение регистрации, переход показателя через порог по участку,
декадная сводка, счёт на оплату, подтверждение оплаты.

Агент notifier: после батча сам рассылает уведомления по сработавшим alert,
проставляет notified_at, пишет agent_event. Дубли не отправляет.

--- B8. Деньги ---

services/billing.py + api/routers/billing.py + api/routers/admin.py

Оплата — счёт на перевод, подтверждение вручную.
Онлайн-эквайринг не подключаем: агропредприятия платят по счёту,
а подключение эквайринга занимает дни.

  POST /api/billing/invoice     клиент выбирает тариф, в ответе номер счёта
                                и реквизиты, они же уходят письмом
  GET  /api/billing/invoices    свои счета
  POST /api/admin/invoices/{id}/confirm   проставляет paid_at и confirmed_by

Доступ к платным функциям проверяется по наличию оплаченного счёта,
а не по факту регистрации. Проверка через contracts/plans.py.
Суммы хранятся в тыйынах целым числом.

--- B9. PDF-отчёты ---

services/pdf.py + POST /api/reports

Генерация из HTML-шаблона через WeasyPrint. Шрифт с полным покрытием
кириллицы, включая кыргызские буквы ң, ө, ү — проверь рендер всех трёх
языков до деплоя.

Отчёт по району или участку: текущий статус, динамика за сезон, прогноз
урожайности с интервалом, объяснение от модели. Путь к файлу в таблице report.
Это платный продукт: агропредприятию нужен документ для агронома и отчётности.

--- B10. Экран операций ---

GET /api/ops/events?limit=100

Последние записи agent_event, публично, без авторизации.

--- B11. Деплой ---

deploy/ — Dockerfile для API и отдельный для батча, Cloud Run для API,
Cloud Run Job + Cloud Scheduler для батча (04:00 +06), Postgres с PostGIS.

После деплоя проверь эндпоинты курлом с внешней машины.

ВРЕМЯ
В базе UTC, пользователю Asia/Bishkek. Конвертация в ОДНОЙ функции
на границе API. Внутри домена локального времени не существует.

ГОТОВНОСТЬ
make check зелёный, запись в docs/log/b.md, эндпоинт проверен курлом
на реальных данных.
```

---

## Порядок и зависимости

```
Блок 0 — вдвоём, ~1 час
        │
        ├────────────────┬────────────────
        ▼                ▼
   A0  seed          (B ждёт A0, 30 мин)
   A1  границы            ▼
   A2  провайдеры    B1  модели
   A3  индексы       B2  эндпоинты
   A4  батч          B3  geojson
   A5  осадки        B4  min_scope
   A6  урожайность   B5  регистрация
   A7  погода        B6  Gemini
   A8  SMAP*         B7  почта
                     B8  счета
                     B9  PDF
                     B10 /ops
                     B11 деплой
```

## Что резать при отставании

По порядку: `*` SMAP и NDWI → SPI по осадкам → PDF-отчёты → прогноз урожайности.

Не режется никогда: батч считает VHI → API отдаёт → Gemini объясняет → регистрация работает → всё в проде на трёх языках.

Фронтенд начинается после того, как API отвечает на публичном адресе.
