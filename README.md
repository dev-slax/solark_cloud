# Sol-Ark Cloud (MySolArk) – Home Assistant Integration

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Component-blue)  
![Version](https://img.shields.io/badge/version-0.2.5-success)  
![License](https://img.shields.io/badge/license-MIT-green)

Custom integration for [Home Assistant](https://www.home-assistant.io/) that connects to the **Sol-Ark Cloud / MySolArk portal** to expose live inverter and solar production data as sensors.

---

## ✨ Features
-  **Authentication** with MySolArk credentials  
-  **Flexible auth modes**:
  - Auto (tries strict + legacy)  
  - Strict (with Origin/Referer headers)  
  - Legacy (minimal headers)  
-  **Cross-host fallback**: `api.solarkcloud.com` and `www.mysolark.com`  
-  **Sensors:**
  - PV Power (W)  
  - Load Power (W)  
  - Grid Import Power (W)  
  - Grid Export Power (W)  
  - Battery Power (W) *(+ discharge / − charge)*  
  - Battery SoC (%)  
  - Energy Today (kWh)  
  - Last Error (diagnostics)

---

## 📦 Installation

### Manual
1. Download the latest release ZIP.  
2. Extract to:  
