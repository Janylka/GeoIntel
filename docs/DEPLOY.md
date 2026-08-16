# GeoIntel — деплой в Google Cloud

Пошаговая инструкция для проекта `fortunecookie-snihsn`. Стек: Cloud Run (API +
батч) + Cloud SQL (Postgres 16 + PostGIS) + Cloud Scheduler. Живая версия с
интерактивной навигацией: см. ссылку на артефакт в истории чата — этот файл
её текстовый двойник, чтобы инструкция жила в репозитории.

## Текущий статус

**Уже готово:**
- GCP-проект `fortunecookie-snihsn` существует, биллинг активен
- Firebase Auth (Google + email-ссылка) настроен и проверен локально
- `frontend/assets/firebase-config.js` содержит реальный web-конфиг, закоммичен
- Resend-ключ рабочий
- Gemini-ключ валиден, деградирует вежливо при сбое

**Блокирует прямо сейчас:**
- Earth Engine: у сервис-аккаунта нет прав использовать проект (см. Фазу 1)
- Gemini: закончились предоплаченные кредиты — пополнить на ai.studio/projects

**Не начато:**
- Инстанс Cloud SQL
- Сборка и пуш Docker-образов
- Деплой Cloud Run (API + батч-job)
- Триггер Cloud Scheduler

---

## Фаза 0 — аккаунты и CLI (~10 мин)

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project fortunecookie-snihsn
```

Нужны: gcloud CLI ([cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)), Docker Desktop.

## Фаза 1 — починить доступ Earth Engine (~10 мин, БЛОКИРУЕТ)

Точная ошибка при тесте локально:
```
EEException: Caller does not have required permission to use project
fortunecookie-snihsn. Grant the caller the roles/serviceusage.serviceUsageConsumer
role...
```

Включение API в библиотеке и разрешение конкретному аккаунту *использовать*
его в проекте — разные вещи. API уже включён, но сервис-аккаунту не хватает
IAM-роли:

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  cloudscheduler.googleapis.com \
  artifactregistry.googleapis.com \
  earthengine.googleapis.com \
  secretmanager.googleapis.com

gcloud projects add-iam-policy-binding fortunecookie-snihsn \
  --member="serviceAccount:geointel-gee@fortunecookie-snihsn.iam.gserviceaccount.com" \
  --role="roles/serviceusage.serviceUsageConsumer"
```

Если после этого всё ещё не работает — сервис-аккаунт нужно отдельно
зарегистрировать в самом Earth Engine (это отдельный шаг от IAM), от имени
владельца проекта: [code.earthengine.google.com/register](https://code.earthengine.google.com/register),
выбрав `fortunecookie-snihsn` как Cloud-проект.

Проверка:
```bash
uv run python -c "from geointel.providers.gee import initialize; initialize(); print('OK')"
```

## Фаза 2 — Cloud SQL + PostGIS (~25 мин)

```bash
gcloud sql instances create geointel-db \
  --database-version=POSTGRES_16 \
  --tier=db-g1-small \
  --region=us-central1 \
  --root-password=ВЫБЕРИТЕ_ПАРОЛЬ

gcloud sql instances describe geointel-db --format="value(state)"  # ждать RUNNABLE
gcloud sql databases create geointel --instance=geointel-db
```

Если `db-g1-small` не найден — `gcloud sql tiers list` и выбрать наименьший
доступный для Postgres (названия тарифов у GCP иногда меняются).

```bash
gcloud sql connect geointel-db --user=postgres
```
```sql
\c geointel
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE USER geointel_app WITH PASSWORD 'ВЫБЕРИТЕ_ПАРОЛЬ_2';
GRANT ALL PRIVILEGES ON DATABASE geointel TO geointel_app;
GRANT ALL ON SCHEMA public TO geointel_app;
\q
```

## Фаза 3 — миграции и реальные данные (~20 мин)

Через Cloud SQL Auth Proxy — тот же Alembic, что и `make migrate` локально,
просто указывает на облачный инстанс.

```bash
# терминал 1, оставить работать
./cloud-sql-proxy fortunecookie-snihsn:us-central1:geointel-db --port 5433
```
```bash
# терминал 2
source .env   # GEE_SERVICE_ACCOUNT_JSON и остальное уже там
export DATABASE_URL="postgresql+psycopg://geointel_app:ПАРОЛЬ_2@127.0.0.1:5433/geointel"

uv run alembic upgrade head
uv run python -m geointel.scripts.ingest_admin_units
uv run python -m geointel.scripts.ingest_cropland_mask
```

**Не запускайте** `seed_dev_metrics.py` на проде — это заведомо тестовые
данные, и он сам откажется работать вне `APP_ENV=local`. Оставьте
`metric_value` батчу (Фаза 6).

## Фаза 4 — ключи → Secret Manager (~10 мин)

Все ключи уже есть в вашем локальном `.env` — просто копируем их в
Secret Manager, ничего не нужно добывать заново.

```bash
source .env
printf '%s' "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
printf '%s' "$RESEND_API_KEY" | gcloud secrets create resend-api-key --data-file=-
printf '%s' "$GEE_SERVICE_ACCOUNT_JSON" | gcloud secrets create gee-service-account-json --data-file=-
printf '%s' "$FIREBASE_CREDENTIALS_JSON" | gcloud secrets create firebase-credentials-json --data-file=-
```

Под давлением времени можно пропустить Secret Manager и передать всё через
`--set-env-vars` прямо при деплое — быстрее, но менее безопасно.

## Фаза 5 — сборка и пуш образов (~15 мин)

`deploy/Dockerfile.api` уже включает `frontend/`.

```bash
gcloud artifacts repositories create geointel \
  --repository-format=docker --location=us-central1

gcloud auth configure-docker us-central1-docker.pkg.dev

docker build -f deploy/Dockerfile.api \
  -t us-central1-docker.pkg.dev/fortunecookie-snihsn/geointel/api:latest .
docker push us-central1-docker.pkg.dev/fortunecookie-snihsn/geointel/api:latest

docker build -f deploy/Dockerfile.batch \
  -t us-central1-docker.pkg.dev/fortunecookie-snihsn/geointel/batch:latest .
docker push us-central1-docker.pkg.dev/fortunecookie-snihsn/geointel/batch:latest
```

## Фаза 6 — деплой API на Cloud Run (~15 мин)

Подключение к Cloud SQL из Cloud Run идёт через Unix-сокет, а не TCP.

```bash
gcloud run deploy geointel-api \
  --image=us-central1-docker.pkg.dev/fortunecookie-snihsn/geointel/api:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8000 \
  --add-cloudsql-instances=fortunecookie-snihsn:us-central1:geointel-db \
  --set-env-vars="APP_ENV=production,TZ_DISPLAY=Asia/Bishkek,GEE_PROJECT=fortunecookie-snihsn,ADMIN_EMAILS=aliya1998n@gmail.com" \
  --set-env-vars="DATABASE_URL=postgresql+psycopg://geointel_app:ПАРОЛЬ_2@/geointel?host=/cloudsql/fortunecookie-snihsn:us-central1:geointel-db" \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,RESEND_API_KEY=resend-api-key:latest,GEE_SERVICE_ACCOUNT_JSON=gee-service-account-json:latest,FIREBASE_CREDENTIALS_JSON=firebase-credentials-json:latest"
```

⚠️ Порт в Dockerfile (`uvicorn --port 8000`) и флаг `--port=8000` здесь должны
совпадать — иначе health-check тихо провалится.

Команда выведет `*.run.app` URL — это и API, и фронтенд, с одного origin.

## Фаза 7 — батч-джоба + ежедневный Scheduler (~20 мин)

Это то, что судьи ищут первым делом: доказательство, что AI работает сам, а
не по кнопке.

```bash
gcloud run jobs create geointel-batch \
  --image=us-central1-docker.pkg.dev/fortunecookie-snihsn/geointel/batch:latest \
  --region=us-central1 \
  --add-cloudsql-instances=fortunecookie-snihsn:us-central1:geointel-db \
  --set-env-vars="APP_ENV=production,GEE_PROJECT=fortunecookie-snihsn" \
  --set-env-vars="DATABASE_URL=postgresql+psycopg://geointel_app:ПАРОЛЬ_2@/geointel?host=/cloudsql/fortunecookie-snihsn:us-central1:geointel-db" \
  --set-secrets="GEE_SERVICE_ACCOUNT_JSON=gee-service-account-json:latest,RESEND_API_KEY=resend-api-key:latest"

gcloud iam service-accounts create geointel-scheduler
gcloud run jobs add-iam-policy-binding geointel-batch \
  --region=us-central1 \
  --member="serviceAccount:geointel-scheduler@fortunecookie-snihsn.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

gcloud scheduler jobs create http geointel-daily-batch \
  --location=us-central1 \
  --schedule="0 4 * * *" \
  --time-zone="Asia/Bishkek" \
  --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/fortunecookie-snihsn/jobs/geointel-batch:run" \
  --http-method=POST \
  --oauth-service-account-email=geointel-scheduler@fortunecookie-snihsn.iam.gserviceaccount.com
```

Если синтаксис триггера через REST капризничает — в консоли Cloud Run у
job'а есть вкладка *Triggers* → *Add Cloud Scheduler Trigger*, там проще.

Прогнать один раз вручную:
```bash
gcloud run jobs execute geointel-batch --region=us-central1
```

## Фаза 8 — домен для Firebase (~5 мин)

Конфиг уже в коде и закоммичен, вход уже проверен на `localhost`. Осталось
только добавить публичный домен:

Firebase Console → Authentication → Settings → *Authorized domains* →
добавить `*.run.app` URL из Фазы 6. Это настройка в консоли, не код —
пересобирать образ не нужно.

## Фаза 9 — проверка и передача судьям (~15 мин)

```bash
curl https://ВАШ-СЕРВИС-uc.a.run.app/health
curl https://ВАШ-СЕРВИС-uc.a.run.app/api/units/
curl https://ВАШ-СЕРВИС-uc.a.run.app/api/ops/events
```

Чек-лист:
- [ ] `/health` возвращает `{"status":"ok","database":"ok"}`
- [ ] Карта на дашборде показывает настоящие границы районов
- [ ] Вход через Google и через email-ссылку работает на публичном домене
- [ ] Доступ к репозиторию открыт для `testing@devpost.com` и `judging@hacker.fund`
- [ ] Scheduler показывает успешный запуск в Cloud Console → Cloud Scheduler → Logs

---

## Известные пробелы (не блокируют деплой)

- `batch/run_daily.py` пока не создаёт записи `alert` — сравнение с порогом
  есть в `domain/indices.py`, но сам шаг создания алерта не реализован
- Нет эндпоинта скачивания сгенерированного PDF-отчёта
- Прогноз урожайности (`yield_forecast`) не считается: `domain/yield_model.py`
  существует, но не подключён ни к батчу, ни к реальным данным Нацстаткома
- Кыргызские названия районов сгенерированы по общим знаниям, не сверены
  носителем языка

## Частые ошибки

| Симптом | Причина |
|---|---|
| `connection to server ... failed` | Cloud Run не видит Cloud SQL — проверить `--add-cloudsql-instances` и точное совпадение `PROJECT:REGION:INSTANCE` в `DATABASE_URL` |
| `403` от Earth Engine | Сервис-аккаунт не зарегистрирован на code.earthengine.google.com/register — это отдельный шаг от IAM |
| Вход не работает | Домен Cloud Run не добавлен в Authorized domains (Фаза 8) |
| Health-check не проходит, контейнер не стартует | Несовпадение порта между Dockerfile и флагом `--port` у Cloud Run |
| `/api/alerts` всегда пусто | Ожидаемо — батч ещё не создаёт алерты (см. «Известные пробелы») |
