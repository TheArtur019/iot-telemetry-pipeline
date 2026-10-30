# Fault-Tolerant Distributed Telemetry Pipeline (Kafka + PostgreSQL + Django)

Распределенный конвейер потоковой обработки телеметрии промышленного оборудования на базе **Apache Kafka**, **PostgreSQL** и **Django**. Проект спроектирован с учетом требований к надежности распределенных систем: гарантия семантики доставки **at-least-once**, транзакционная идемпотентность сохранения, изоляция аномальных сообщений (DLQ) и разграничение прикладного и системного мониторинга.

---

## Архитектура системы

Комплекс построен по сервисной архитектуре со слабой связностью компонентов через шину сообщений Apache Kafka.

### Топология очередей Kafka
* `telemetry.raw` — поток сырых замеров температуры с технологических узлов (партиционирование по ключу `device_id`).
* `telemetry.processed` — результаты валидации и пороговой классификации (группа потребителей `processor-v1`).
* `telemetry.invalid` — Dead Letter Queue (DLQ) / карантин для сообщений, нарушающих контракт схемы данных.
* `systems.heartbeat` — служебный поток сигналов жизнеспособности запущенных воркеров (период отправки — 3 с).

---

## Ключевые инженерные решения

* **Семантика доставки At-Least-Once и ручной Commit:** 
  Автоматическая фиксация смещений отключена (`enable.auto.commit=False`). Смещение (`offset`) коммитится строго после успешной записи транзакции в PostgreSQL. При сбое БД или сети коммит блокируется, гарантируя повторную вычитку после восстановления.
* **Транзакционная идемпотентность:**
  Защита от дублей при ретраях и перечитывании топиков (`auto.offset.reset: earliest`) реализована на уровне реляционной схемы: уникальные индексы по полям `event_id` (таблица `EventLog`) и `original_event_id` (таблица `MeasurementResult`).
* **Изоляция сбоев (Dead Letter Queue):**
  Некорректно сформированные события не приводят к падению обработчиков (`processor`), а перенаправляются в карантинный топик `telemetry.invalid` с детерминированным UUID, рассчитанным на базе координат смещения (`partition:offset`).
* **Точность временных окон:**
  Аналитические агрегаты и метрики задержек рассчитываются относительно физического момента замера (`event_time` / `measured_at`), а не времени фиксации в СУБД (`received_at`), что исключает искажение статистики при ликвидации лагов.
* **Многоуровневая наблюдаемость:**
  Разграничены понятия доступности процесса и выполнения бизнес-логики: независимый поток `heartbeat` информирует о работе контейнера, в то время как отставание консьюмера (`consumer lag`) и сквозная задержка ($p95$) контролируют реальную производительность обработки.

---

## Стек технологий

* **Язык и среда:** Python 3.12, Docker, Docker Compose
* **Шина сообщений:** Apache Kafka 4.1 (режим KRaft, без ZooKeeper)
* **Клиент Kafka:** `confluent-kafka` (librdkafka)
* **Хранилище данных:** PostgreSQL 16
* **Бэкенд и веб-слой:** Django 5.2

---

## Инструкция по запуску

### 1. Клонирование и подготовка
```bash
git clone https://github.com/TheArtur019/iot-telemetry-pipeline
cd iot-telemetry-pipeline
```

### 2. Сборка и запуск контейнеров
Запуск всех компонентов (PostgreSQL, Kafka KRaft, миграции, топики, воркеры, web-сервер) выполняется одной командой:
```bash
docker compose up -d --build
```

### 3. Проверка доступности
* **Веб-панель мониторинга:** [http://localhost:8000](http://localhost:8000)
* **JSON API статуса систем:** [http://localhost:8000/api/state/](http://localhost:8000/api/state/)

---

## Тестирование и верификация

### Запуск модульных тестов
Проверка корректности дедупликации, фиксации транзакций и изоляции некорректных сообщений в тестовой БД:
```bash
docker compose run --rm --no-deps web python manage.py test monitoring
```

### Статический анализ проекта (AST)
```bash
docker compose run --rm --no-deps web python tools/check_project.py --require-migrations
```

### Мониторинг Consumer Lag
Проверка актуального отставания группы обработчика в брокере Kafka:
```bash
docker compose exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka:9092 \
  --describe --group processor-v1
```

### Анализ задержек конвейера в PostgreSQL
Расчет средней сквозной задержки и 95-го процентиля ($p95$) времени доставки телеметрии:
```bash
docker compose exec db psql -U student -d monitoring -c "
SELECT device_id,
       count(*) AS n,
       round(avg(extract(epoch FROM (received_at - measured_at)))::numeric, 2) AS mean_seconds,
       round(percentile_cont(0.95) WITHIN GROUP (
           ORDER BY extract(epoch FROM (received_at - measured_at))
       )::numeric, 2) AS p95_seconds
FROM monitoring_measurementresult
GROUP BY device_id
ORDER BY device_id;"
```
