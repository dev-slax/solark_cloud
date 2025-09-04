# Sol-Ark Cloud (MySolArk) – Home Assistant Integration

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Component-blue)  
![Version](https://img.shields.io/badge/version-0.2.5-success)  
![License](https://img.shields.io/badge/license-MIT-green)

Custom integration for [Home Assistant](https://www.home-assistant.io/) that connects to the **Sol-Ark Cloud / MySolArk portal** to expose live inverter and solar production data as sensors.

This integration was developed with the assistance of AI (OpenAI’s ChatGPT) alongside manual coding, testing, and verification.

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
1. Download the latest files.  
2. Extract to:  
   ```
   <config>/custom_components/solark_cloud/
   ```
   Verify structure:
   ```
   custom_components/solark_cloud/__init__.py
   custom_components/solark_cloud/api.py
   custom_components/solark_cloud/config_flow.py
   custom_components/solark_cloud/const.py
   custom_components/solark_cloud/manifest.json
   custom_components/solark_cloud/sensor.py
   ```
3. Restart Home Assistant.

---

## ⚙️ Configuration
1. In Home Assistant, go to **Settings → Devices & Services → Add Integration**.  
2. Search for **Sol-Ark (SolarkCloud)**.  
3. Enter:
   - Username (email)  
   - Password  
   - Plant ID  
   - Base URL (`https://api.solarkcloud.com` or `https://www.mysolark.com`)  
   - Auth mode (Auto, Strict, Legacy)  
   - Scan interval (default: 120s)  
4. Save → Restart HA if needed.

---

## 📜 License and Credits
This integration was developed independently, with reference to public Sol-Ark community projects:
- [Rick-EV/SolarkCloud](https://github.com/Rick-EV/SolarkCloud)  
- [judasgutenberg/SolArkMonitor](https://github.com/judasgutenberg/SolArkMonitor)  
- [pypi.org/project/solark-cloud](https://pypi.org/project/solark-cloud/)  

Thanks to their work documenting endpoints and field names.
MIT License.
