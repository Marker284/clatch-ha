# Clatch Cycle Tracker for Home Assistant

[![Русский](https://img.shields.io/badge/lang-Русский-inactive.svg)](README.md)
[![English](https://img.shields.io/badge/lang-English-blue.svg)](README.en.md)

[![HACS Custom][hacs-shield]][hacs-url]
[![License][license-shield]][license-url]

An unofficial custom [Home Assistant](https://www.home-assistant.io/)
integration for the [Clatch](https://clatch.app/) app (a menstrual cycle
tracker, MTS ID). Cycle, phase and diary data land in HA as ordinary
sensors, ready for any automation, dashboard or notification.

Not affiliated with Clatch / MTS / Morizo Digital. The API is private and
not officially documented (reverse-engineered, see
[Marker284/clatch-api](https://github.com/Marker284/clatch-api)). Use it
only with your own token/account.

## Features

- Fully UI-configurable — the token and profile ID are entered in the
  integration's config flow, no `configuration.yaml`.
- The token is validated with a live API request during setup.
- Polls once an hour (configurable) — `/api/v1/period` and
  `/api/v1/symptoms`; cycle day, phase and forecasts are then computed
  locally (rolling average over the last 6 cycles).
- A "Clatch" device with sensors:

| Entity | What it shows |
|---|---|
| `sensor.<name>_cycle_day` | current cycle day |
| `sensor.<name>_phase` | cycle phase (menstruation / follicular / ovulation / luteal / PMS) |
| `sensor.<name>_days_until_period` | days until the period |
| `sensor.<name>_days_until_period_end` | days until the period ends (if ongoing) |
| `sensor.<name>_days_until_ovulation` | days until ovulation |
| `sensor.<name>_next_period_start` | next period start date |
| `sensor.<name>_ovulation_date` | ovulation date |
| `sensor.<name>_last_period_start` | last period start date |
| `sensor.<name>_avg_period_length` | average period length |
| `sensor.<name>_last_diary_entry` | date of the last diary entry (symptoms in attributes) |
| `binary_sensor.<name>_period_active` | `on` if the period is ongoing right now |

The profile being read (`profile_id`) can be your own or a partner's — if
you have access through Clatch's built-in sharing.

## Installation

### Via HACS (custom repository)

1. HACS → three-dot menu → **Custom repositories**.
2. URL: `https://github.com/Marker284/clatch-ha`, category **Integration**.
3. Find "Clatch Cycle Tracker" in the list → Install.
4. Restart Home Assistant.

### Manually

```bash
cd /config/custom_components
git clone https://github.com/Marker284/clatch-ha.git tmp-clatch-ha
mv tmp-clatch-ha/custom_components/clatch .
rm -rf tmp-clatch-ha
```

Restart Home Assistant.

## Setup

**Settings → Devices & Services → Add Integration → "Clatch Cycle
Tracker"**.

The form asks for:

- **Name** — free text, affects the entity_id (e.g. "Her" or "Cycle").
- **Clatch API token (JWT)** — the `Authorization: Bearer <jwt>` string
  the app sends.
- **Profile ID (`profile_id`)** — the UUID of the profile to read (your
  own, or a partner's if you have access through in-app sharing).

Clatch has no public API, so both values are extracted from the app's
**own** authenticated traffic. The full method is
[below](#how-to-obtain-the-token-and-profile-id).

The polling interval is changed separately under **Configure** (Options)
on the already-added integration — from 15 to 1440 minutes, 60 by default.

## How to obtain the token and profile ID

The procedure isn't quick (it needs physical access to the phone, Frida
and a reverse proxy), but it's a one-time job: the token's observed `exp`
is set ~10 years ahead, so you won't have to repeat it regularly.

> **Your own account only.** You intercept the traffic of your own device
> with your own login. The token is full access to the account: keep it
> like a password, never put it in git or hand it to anyone. Using the
> unofficial API likely violates the service's terms of use — at your own
> risk.

### Why ordinary traffic interception doesn't work

Two obstacles that make a plain Charles/mitmproxy "HTTP proxy in Wi-Fi
settings" insufficient:

1. **The app ignores the Android system proxy.** The login screen is a
   system WebView and does honor the proxy, but the main API traffic goes
   through the app's own Dart `HttpClient`, which does not consider
   Android's system proxy settings at all — the connection goes straight
   to the IP. A plain proxy would only see `login.mts.ru`, not
   `clatch3.mts.ru`.
2. **Flutter certificate pinning.** Flutter does its own certificate
   check at the BoringSSL level inside `libflutter.so`, so even swapping
   the trusted system CA (via `apk-mitm` etc.) doesn't help — the app
   simply won't send the request.

Both are bypassed: the pinning is removed with a Frida hook (step 2), and
the proxy-ignoring is solved by becoming the `clatch3.mts.ru` server
ourselves via DNS spoofing + a reverse proxy (step 3).

### What you'll need

- An Android phone with Clatch installed, physical access (USB), logged
  into the target account.
- A computer on the same Wi-Fi network.
- Tools on the computer: `adb`, `frida-tools` (`pip install frida-tools`),
  `objection` (`pip install objection`), Java (for `apktool` /
  `objection patchapk`), `mitmproxy`, `dnsmasq`.
- The app's APK. Pull it from the device
  (`adb shell pm path ru.morizo.clatch` → `adb pull <path>`) or download
  from APKMirror/APKPure — the **version must match** the one installed
  and logged in on the phone.

### Step 1. Embed the Frida gadget into the APK

```bash
objection patchapk -s clatch.apk
```

(needs `aapt` and `apktool` in `PATH`; on Arch — the AUR packages
`android-sdk-build-tools` and `android-apktool`).

Install the resulting `*-patched.apk` **instead of** the original (the
signatures differ — remove the original first:
`adb uninstall ru.morizo.clatch`). On launch the app hangs on the splash
screen — that's expected, the gadget is waiting for Frida to attach (it
listens on `127.0.0.1:27042` inside the process).

### Step 2. Remove the TLS pinning (Flutter/BoringSSL)

Script:
[NVISOsecurity/disable-flutter-tls-verification](https://github.com/NVISOsecurity/disable-flutter-tls-verification)
(the `disable-flutter-tls.js` file).

```bash
frida-ps -U | grep -i clatch           # find the process name/PID
frida -U -n Clatch -l disable-flutter-tls.js
```

The output `ssl_verify_peer_cert has been patched` means success — the
app unblocks from the splash screen.

**Important:** the hook lives only as long as the process does. On every
restart (crash, force-stop, reinstall) you must re-apply it. Handy to
automate:

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

### Step 3. Become the `clatch3.mts.ru` server (DNS + reverse proxy)

The key step: since the app connects straight to the IP and ignores the
proxy, we feed it our own IP via DNS and run a reverse proxy there that
forwards to the real backend.

**1. `dnsmasq`** — resolves `clatch3.mts.ru` to your computer's IP, and
everything else as usual. `dnsmasq-clatch.conf`:

```
no-resolv
server=8.8.8.8
address=/clatch3.mts.ru/<your computer's LAN IP>
listen-address=<your computer's IP>
bind-interfaces
port=53
```

```bash
sudo dnsmasq -C dnsmasq-clatch.conf --no-daemon
```

**2. On the phone:**

- Turn off **Private DNS** (Settings → Network & internet → Private DNS →
  Off) — otherwise Android goes over DNS-over-TLS straight to Google's
  resolver and ignores the local DNS.
- In the Wi-Fi network settings → IP → Static → **DNS 1 = the computer's
  IP**.

**3. `mitmproxy`** in reverse-proxy mode on port 443, forwarding to the
real backend:

```bash
sudo mitmdump --mode reverse:https://clatch3.mts.ru -p 443
```

Now that DNS points to the computer, the app connects "to
`clatch3.mts.ru`" and lands on mitmproxy. The TLS handshake succeeds
thanks to the patch from step 2 (the app no longer checks who the
certificate really belongs to).

**4.** Re-enter the app. It helps to clear the app's cache on the phone
first — then it's guaranteed to make fresh API requests instead of
serving data from the local cache.

### Step 4. Grab the token and profile ID

`mitmproxy` now shows the decrypted requests. Any request to
`clatch3.mts.ru` will do.

**Token** — the `Authorization` header on any request:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

Copy the whole value **after** `Bearer ` — that's the token for the
integration's form.

**Profile ID** — visible right in the path of the cycle-data requests.
When the calendar opens, the app calls:

```
GET /api/v1/period/<UUID>
GET /api/v1/symptoms/<UUID>
```

The `<UUID>` in the path is the `profile_id`. For your **own** profile,
just open your own calendar; for a **partner's** (if they shared access
with you in the app), open the partner's section in the app and the path
will carry their UUID. The list of profiles shared with you is also
returned by `GET /api/v1/sharing/in` (the UUID comes from the record
fields, and is not the `sub` from the JWT).

You can check the token + profile_id pair straight from the console —
this is exactly the request the integration makes during setup:

```bash
curl -H "Authorization: Bearer <jwt>" \
  https://clatch3.mts.ru/api/v1/period/<UUID>
```

It should return a JSON list of dates
(`{"data": ["2025-01-01T00:00:00Z", ...]}`), not a `401`/`403`.

### Step 5. Cleanup

- On the phone: DNS back to "Automatic", re-enable Private DNS if you
  like.
- Stop `dnsmasq` and `mitmdump` (started with `sudo` — Ctrl+C in their
  terminals).
- You can keep the patched APK or reinstall the original from the store —
  it doesn't affect the token you already have.

After that, fill in the **Token** and **Profile ID** in the integration —
none of the infrastructure above is needed any more, HA talks to the API
directly.

## Disclaimer

Using the unofficial API likely violates the service's terms of use. Use
it at your own risk, only with your own data or data you legitimately have
access to through in-app sharing. No tokens or personal data are published
in this repository.

[hacs-shield]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs-url]: https://github.com/hacs/integration
[license-shield]: https://img.shields.io/github/license/Marker284/clatch-ha.svg
[license-url]: LICENSE
