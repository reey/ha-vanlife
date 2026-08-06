DOMAIN = "vanlife"

CONF_BASE_URL = "base_url"
DEFAULT_BASE_URL = "https://app-api-eu.vanebike.life"

APP_INFO_HEADER = "os=android; client=app; version=1.0.0; version-code=1"

# Polling intervals in seconds
POLL_INTERVAL_MOVING = 30        # when the last GPS report is fresh
POLL_INTERVAL_STATIONARY = 120   # when the last GPS report is stale

# A GPS report younger than this is considered "the bike is moving"
MOVING_THRESHOLD_SECS = 600      # 10 minutes, mirrors the CLI's online check
