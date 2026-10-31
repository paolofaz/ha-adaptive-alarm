"""Constants for Adaptive Alarm."""

DOMAIN = "adaptive_alarm"
DEFAULT_NAME = "Adaptive Alarm"

CONF_ENTRY_CONTACT = "entry_contact"
CONF_ENTRY_LOCK = "entry_lock"
CONF_WINDOW_LIVING = "window_living"
CONF_WINDOW_BATH = "window_bath"
CONF_SHUTTER_LIVING = "shutter_living"
CONF_SHUTTER_BATH = "shutter_bath"
CONF_EXTRA_CONTACTS = "extra_contacts"
# The legacy unpaired vibration_sensors option is intentionally not acted upon.
CONF_VIBRATION_SENSORS = "vibration_sensors"
CONF_VIBRATION_1 = "vibration_1"
CONF_VIBRATION_1_ZONE = "vibration_1_zone"
CONF_VIBRATION_2 = "vibration_2"
CONF_VIBRATION_2_ZONE = "vibration_2_zone"
CONF_VIBRATION_3 = "vibration_3"
CONF_VIBRATION_3_ZONE = "vibration_3_zone"

VIBRATION_PAIRS = (
    (CONF_VIBRATION_1, CONF_VIBRATION_1_ZONE),
    (CONF_VIBRATION_2, CONF_VIBRATION_2_ZONE),
    (CONF_VIBRATION_3, CONF_VIBRATION_3_ZONE),
)
CONF_STORM_SENSOR = "storm_sensor"
CONF_ARMING_DELAY = "arming_delay"
CONF_VIBRATION_PROFILE = "vibration_profile"
CONF_VIBRATION_WINDOW = "vibration_window"
CONF_VIBRATION_DEBOUNCE = "vibration_debounce"
CONF_RECOVERY_POLICY = "recovery_policy"

DEFAULT_ARMING_DELAY = 60
DEFAULT_VIBRATION_PROFILE = "balanced"
DEFAULT_VIBRATION_WINDOW = 60
DEFAULT_VIBRATION_DEBOUNCE = 3
DEFAULT_RECOVERY_POLICY = "notify"

EVENT_ADAPTIVE_ALARM = "adaptive_alarm_event"
