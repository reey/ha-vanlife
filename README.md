# ha-vanlife

> [!WARNING]
> **Unofficial & Cloud-Based**
> This integration uses Vanebike's cloud services (REST). It is unofficial and not affiliated with Vanebike. Because it relies on reverse-engineered cloud APIs (decompiled [Android app](https://play.google.com/store/apps/details?id=com.swei.aioteu)), any changes on the cloud side could break functionality.

---

## 🚀 Installation

### HACS (Recommended)

1. In HACS, open **Integrations**.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add `https://github.com/reey/ha-vanlife` as an **Integration** repository.
4. Install **VanLife (Vanebike)** and restart Home Assistant.

### Configuration

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=vanlife)

1. Open **Settings -> Devices & Services**.
2. Select **Add Integration**.
3. Search for **VanLife (Vanebike)**.
4. Sign in with the VanLife account used by the mobile app.

---

## 📊 Features & Entities

The integration fetches all available bikes connected to your account and 

- **Device tracker:** Tracks your bike via cloud polling. Current location is polled at least every two minutes. If the bike is currently moving (position changed in the last 10 minutes), the polling frequency is increased to every 30 seconds.

---
