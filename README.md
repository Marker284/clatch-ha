# Clatch Cycle Tracker для Home Assistant

[![HACS Custom][hacs-shield]][hacs-url]
[![License][license-shield]][license-url]

Неофициальная кастомная интеграция [Home Assistant](https://www.home-assistant.io/)
для приложения [Clatch](https://clatch.app/) («Женский календарь», MTS ID).
Данные о цикле, фазах и дневнике попадают в HA как обычные сенсоры —
дальше с ними можно строить любые автоматизации, дашборды и уведомления.

Не аффилирована с Clatch / MTS / Morizo Digital. API — приватный,
официально не документированный (получен реверс-инжинирингом, см.
[Marker284/clatch-api](https://github.com/Marker284/clatch-api)).
Используйте только со своим токеном/аккаунтом.

## Возможности

- Настройка полностью через UI — токен и ID профиля вводятся в форме
  добавления интеграции, никакого `configuration.yaml`.
- Токен проверяется живым запросом к API прямо на этапе настройки.
- Один опрос в час (настраивается) — `/api/v1/period` и
  `/api/v1/symptoms`, дальше день цикла/фаза/прогнозы считаются локально
  (скользящее среднее по последним 6 циклам).
- Устройство "Clatch" с сенсорами:

| Сущность | Что показывает |
|---|---|
| `sensor.<name>_cycle_day` | текущий день цикла |
| `sensor.<name>_phase` | фаза цикла (менструация / фолликулярная / овуляция / лютеиновая / ПМС) |
| `sensor.<name>_days_until_period` | дней до месячных |
| `sensor.<name>_days_until_period_end` | дней до конца месячных (если идут сейчас) |
| `sensor.<name>_days_until_ovulation` | дней до овуляции |
| `sensor.<name>_next_period_start` | дата следующих месячных |
| `sensor.<name>_ovulation_date` | дата овуляции |
| `sensor.<name>_last_period_start` | дата начала последних месячных |
| `sensor.<name>_avg_period_length` | средняя длительность месячных |
| `sensor.<name>_last_diary_entry` | дата последней записи дневника (симптомы — в атрибутах) |
| `binary_sensor.<name>_period_active` | `on`, если месячные идут прямо сейчас |

Профиль для чтения (`profile_id`) может быть как своим, так и
партнёрским — если есть доступ через встроенный в Clatch sharing.

## Установка

### Через HACS (custom repository)

1. HACS → три точки в углу → **Custom repositories**.
2. URL: `https://github.com/Marker284/clatch-ha`, категория **Integration**.
3. Найти "Clatch Cycle Tracker" в списке → Установить.
4. Перезапустить Home Assistant.

### Вручную

```bash
cd /config/custom_components
git clone https://github.com/Marker284/clatch-ha.git tmp-clatch-ha
mv tmp-clatch-ha/custom_components/clatch .
rm -rf tmp-clatch-ha
```

Перезапустить Home Assistant.

## Настройка

**Настройки → Устройства и службы → Добавить интеграцию → "Clatch Cycle
Tracker"**.

Форма попросит:

- **Название** — свободное, влияет на entity_id (например "Она" или "Цикл").
- **Токен Clatch API (JWT)** — как получить свой токен, описано в
  [Marker284/clatch-api](https://github.com/Marker284/clatch-api) (публичная
  документация API; сама методология извлечения токена — в отдельном
  приватном репозитории автора, тут не публикуется).
- **ID профиля** — UUID профиля, чьи данные читать.

Интервал опроса меняется отдельно в **Настроить** (Options) уже
добавленной интеграции — от 15 до 1440 минут, по умолчанию 60.

## Дисклеймер

Использование неофициального API, скорее всего, нарушает
пользовательское соглашение сервиса. Используйте на свой риск, только со
своими данными/данными, к которым у вас есть легитимный доступ через
sharing в самом приложении. Токены и персональные данные в этом
репозитории не публикуются.

[hacs-shield]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs-url]: https://github.com/hacs/integration
[license-shield]: https://img.shields.io/github/license/Marker284/clatch-ha.svg
[license-url]: LICENSE
