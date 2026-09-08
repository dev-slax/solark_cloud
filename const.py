from homeassistant.const import Platform

DOMAIN = "solark_cloud"
PLATFORMS = [Platform.SENSOR]

# Current Sol-Ark portal/API hosts. Credentials are never sent outside this set.
PORTAL_URL = "https://www.solarkcloud.com"
DEFAULT_API_URL = "https://p2.api.solarkcloud.com"
LEGACY_API_URL = "https://api.solarkcloud.com"
KNOWN_API_URLS = (DEFAULT_API_URL, LEGACY_API_URL)

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PLANT_ID = "plant_id"
# Read only for backward compatibility with existing 0.2.x config entries.
CONF_BASE_URL = "base_url"

CONF_AUTH_MODE = "auth_mode"
AUTH_MODE_AUTO = "auto"
AUTH_MODE_STRICT = "strict"
AUTH_MODE_LEGACY = "legacy"
AUTH_MODES = (AUTH_MODE_AUTO, AUTH_MODE_STRICT, AUTH_MODE_LEGACY)

DEFAULT_SCAN_INTERVAL = 120
MIN_SCAN_INTERVAL = 60
MAX_SCAN_INTERVAL = 900

CONF_INVERT_GRID_SIGN = "invert_grid_sign"
