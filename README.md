
# Sol-Ark (Cloud) — Home Assistant Custom Integration

This custom integration logs into **MySolArk** and exposes sensors for your **PV production**:
- **PV Power (W)**
- **PV Energy Today (kWh)**

> Notes
> - MySolArk (Sol-Ark Cloud) updates roughly every **5 minutes**.
> - As of June 2024, Sol-Ark moved their backend to **api.solarkcloud.com** (from PV Pro/PowerView), but the API is substantially similar.
> - This integration depends on the PyPI package **`solark-cloud`** which wraps the undocumented cloud API.

## Install

1. Download the ZIP attached to this message and extract the folder to:
   ```
   <home-assistant-config>/custom_components/solark_cloud
   ```
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**, search for **Sol-Ark (Cloud)**.
4. Enter your **MySolArk** username and password. Optionally add a **Plant ID** (leave empty to use the first plant on your account).

### Add to Energy Dashboard (optional)
- You can use **PV Energy Today** as your solar production source (kWh) in the Energy dashboard.
- If units or sign need tweaking, create a template sensor accordingly.

## Troubleshooting
- If you previously used `api.solark.com` and saw DNS errors, update to the new domain: **api.solarkcloud.com**.
- Check logs for `solark_cloud` if values are missing; the integration searches common fields in the API response for PV power/energy.
- If you have multiple plants, set **Plant ID** in the integration **Options**.

## Credits
- [`solark-cloud` PyPI package](https://pypi.org/project/solark-cloud/) by Mark Smith (MIT).
- Community research on Sol-Ark's cloud API (e.g., Judas Gutenberg's SolArkMonitor).

## Disclaimer
This uses an **undocumented** cloud API, which may change without notice.
