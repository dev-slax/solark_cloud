from homeassistant.const import Platform

DOMAIN = "solark_cloud"
PLATFORMS = [Platform.SENSOR]

# Default (worked for you in 0.2.0)
DEFAULT_BASE_URL = "https://api.solarkcloud.com"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PLANT_ID = "plant_id"
CONF_BASE_URL = "base_url"

# Options
CONF_AUTH_MODE = "auth_mode"
AUTH_MODE_AUTO = "auto"
AUTH_MODE_STRICT = "strict"   # with Origin/Referer
AUTH_MODE_LEGACY = "legacy"   # minimal headers

DEFAULT_SCAN_INTERVAL = 120
