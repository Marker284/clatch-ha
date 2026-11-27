# Clatch Cycle Tracker для Home Assistant

[![Русский](https://img.shields.io/badge/lang-Русский-blue.svg)](README.md)
[![English](https://img.shields.io/badge/lang-English-inactive.svg)](README.en.md)

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
- **Токен Clatch API (JWT)** — строка `Authorization: Bearer <jwt>`, которую
  шлёт приложение.
- **ID профиля (`profile_id`)** — UUID профиля, чьи данные читать (свой или
  партнёрский, если есть доступ через sharing в самом приложении).

У Clatch нет публичного API, поэтому оба значения добываются из
**собственного** авторизованного трафика приложения. Полная методология —
[ниже](#как-получить-токен-и-id-профиля).

Интервал опроса меняется отдельно в **Настроить** (Options) уже
добавленной интеграции — от 15 до 1440 минут, по умолчанию 60.

## Как получить токен и ID профиля

Процедура не быстрая (нужен физический доступ к телефону, Frida и
reverse-proxy), но делается один раз: наблюдаемый `exp` токена выставлен
на ~10 лет вперёд, повторять регулярно не придётся.

> **Только для своего аккаунта.** Перехватывается трафик вашего же
> устройства с вашим же логином. Токен — это полноценный доступ к
> аккаунту: храните его как пароль, в git и в чужие руки не отдавайте.
> Использование неофициального API, скорее всего, нарушает
> пользовательское соглашение сервиса — на свой риск.

### Почему обычный перехват трафика не работает

Два препятствия, из-за которых недостаточно просто поднять
Charles/mitmproxy «HTTP-прокси в настройках Wi-Fi»:

1. **Приложение игнорирует системный прокси Android.** Экран логина —
   системный WebView и прокси слушает, а вот основной API-трафик идёт
   через собственный Dart `HttpClient`, который системные прокси-настройки
   Android не учитывает вообще — соединение идёт напрямую по IP. Обычный
   прокси увидит только `login.mts.ru`, но не `clatch3.mts.ru`.
2. **Сертификатный пиннинг Flutter.** Flutter делает свою проверку
   сертификата на уровне BoringSSL внутри `libflutter.so`, поэтому даже
   подмена доверенного системного CA (через `apk-mitm` и т.п.) не
   помогает — приложение просто не отправит запрос.

Обходятся оба: пиннинг снимается хуком Frida (шаг 2), а игнорирование
прокси — тем, что мы сами становимся сервером `clatch3.mts.ru` через
подмену DNS + reverse-proxy (шаг 3).

### Что понадобится

- Android-телефон с установленным Clatch, физический доступ (USB),
  залогиненный в целевой аккаунт.
- Компьютер в той же Wi-Fi-сети.
- Инструменты на компе: `adb`, `frida-tools` (`pip install frida-tools`),
  `objection` (`pip install objection`), Java (для `apktool` /
  `objection patchapk`), `mitmproxy`, `dnsmasq`.
- APK приложения. Снять с устройства (`adb shell pm path ru.morizo.clatch`
  → `adb pull <путь>`) или скачать с APKMirror/APKPure — **версия должна
  совпадать** с установленной и залогиненной на телефоне.

### Шаг 1. Встроить Frida gadget в APK

```bash
objection patchapk -s clatch.apk
```

(нужны `aapt` и `apktool` в `PATH`; на Arch — AUR-пакеты
`android-sdk-build-tools` и `android-apktool`).

Установите получившийся `*-patched.apk` **вместо** оригинала (подписи
разные — оригинал сначала удалить: `adb uninstall ru.morizo.clatch`).
При запуске приложение зависнет на сплэш-экране — это нормально, gadget
ждёт подключения Frida (слушает `127.0.0.1:27042` внутри процесса).

### Шаг 2. Снять TLS-пиннинг (Flutter/BoringSSL)

Скрипт:
[NVISOsecurity/disable-flutter-tls-verification](https://github.com/NVISOsecurity/disable-flutter-tls-verification)
(файл `disable-flutter-tls.js`).

```bash
frida-ps -U | grep -i clatch           # найти имя/PID процесса
frida -U -n Clatch -l disable-flutter-tls.js
```

Вывод `ssl_verify_peer_cert has been patched` означает успех — приложение
разблокируется со сплэша.

**Важно:** хук живёт, пока жив процесс. При каждом перезапуске (краш,
force-stop, переустановка) патч нужно накатывать заново. Удобно
автоматизировать:

```bash
last=
while true; do
  pid=$(frida-ps -U 2>/dev/null | awk '$2=="Clatch"{print $1}')
  if [ -n "$pid" ] && [ "$pid" != "$last" ]; then
    frida -U -n Clatch -l disable-flutter-tls.js <<< $'\n'
    last=$pid
  fi
  sleep 2
done
```

### Шаг 3. Стать сервером `clatch3.mts.ru` (DNS + reverse-proxy)

Ключевой шаг: раз приложение лезет напрямую по IP и игнорирует прокси,
подсовываем ему свой IP через DNS, а на нём держим reverse-proxy,
форвардящий на настоящий бэкенд.

**1. `dnsmasq`** — резолвит `clatch3.mts.ru` на IP вашего компа, всё
остальное как обычно. `dnsmasq-clatch.conf`:

```
no-resolv
server=8.8.8.8
address=/clatch3.mts.ru/<IP компа в локальной сети>
listen-address=<IP компа>
bind-interfaces
port=53
```

```bash
sudo dnsmasq -C dnsmasq-clatch.conf --no-daemon
```

**2. На телефоне:**

- Выключить **Приватный DNS** (Настройки → Сеть и интернет → Приватный
  DNS → Выключено) — иначе Android ходит по DNS-over-TLS напрямую к
  гугловскому резолверу и локальный DNS игнорирует.
- В настройках Wi-Fi-сети → IP → Статический → **DNS 1 = IP компа**.

**3. `mitmproxy`** в режиме reverse-proxy на 443, форвардит на настоящий
бэкенд:

```bash
sudo mitmdump --mode reverse:https://clatch3.mts.ru -p 443
```

Теперь DNS указывает на комп, приложение лезет «на `clatch3.mts.ru`» и
попадает на mitmproxy. TLS-хендшейк проходит благодаря патчу из шага 2
(приложение больше не проверяет, кому реально принадлежит сертификат).

**4.** Перезайдите в приложение. Полезно сначала очистить кэш приложения
на телефоне — тогда оно гарантированно сделает свежие запросы к API, а не
отдаст данные из локального кэша.

### Шаг 4. Забрать токен и ID профиля

`mitmproxy` теперь показывает расшифрованные запросы. Нужны любые запросы
к `clatch3.mts.ru`.

**Токен** — заголовок `Authorization` в любом запросе:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

Скопируйте значение целиком, **после** `Bearer ` — это и есть токен для
формы интеграции.

**ID профиля** — виден прямо в пути запросов за данными цикла. Приложение
при открытии календаря дёргает:

```
GET /api/v1/period/<UUID>
GET /api/v1/symptoms/<UUID>
```

`<UUID>` в пути и есть `profile_id`. Для **своего** профиля достаточно
открыть свой календарь; для **партнёрского** (если вам расшарили доступ в
самом приложении) — открыть в приложении раздел партнёра, тогда в пути
будет его UUID. Список доступных вам расшаренных профилей также отдаёт
`GET /api/v1/sharing/in` (UUID берётся из полей записей, это не `sub` из
JWT).

Проверить пару токен + profile_id можно прямо из консоли — ровно этот
запрос делает интеграция при настройке:

```bash
curl -H "Authorization: Bearer <jwt>" \
  https://clatch3.mts.ru/api/v1/period/<UUID>
```

Должен вернуться JSON со списком дат (`{"data": ["2025-01-01T00:00:00Z", ...]}`),
а не `401`/`403`.

### Шаг 5. Уборка

- На телефоне: DNS обратно на «Автоматически», Приватный DNS — по вкусу
  вернуть.
- Остановить `dnsmasq` и `mitmdump` (были через `sudo` — Ctrl+C в их
  терминалах).
- Патченый APK можно оставить или переустановить оригинал из стора — на
  уже полученный токен это не влияет.

После этого в интеграции заполняете **Токен** и **ID профиля** — вся
инфраструктура выше больше не нужна, HA обращается к API напрямую.

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
