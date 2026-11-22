"""Constants for the unofficial Duracell Energy Cloud integration."""

DOMAIN = "duracell_energy_cloud"
NAME = "Duracell Energy Cloud"

API_ROOT = (
    "https://monitoring.duracellenergy.com/dist/server/api/CodeIgniter/"
    "index.php/Senergytec/web/v2/Inverterapi/"
)
LOGIN_URL = API_ROOT + "UserLogin_v1"
FLOW_URL = API_ROOT + "getGroupHybridFlowgraph_v1"

CONF_INVERTER_ID = "inverter_id"
CONF_GROUP_ID = "group_id"
CONF_FLOW_SIGN = "flow_sign"
CONF_LOGIN_SIGN = "login_sign"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_TOKEN = "token"
CONF_AUTH_MODE = "auth_mode"
CONF_POLL_SECONDS = "poll_seconds"

AUTH_PASSWORD = "password"
AUTH_TOKEN = "token"
DEFAULT_POLL_SECONDS = 120
MIN_POLL_SECONDS = 60

PLATFORMS = ["sensor", "binary_sensor"]

AUTH_AUTO = "automatic"
GROUPS_URL = API_ROOT + "GroupList"
DEVICES_URL = API_ROOT + "GroupDetailList"

DETAIL_URL = API_ROOT + "InverterDetailInfoNewone"
