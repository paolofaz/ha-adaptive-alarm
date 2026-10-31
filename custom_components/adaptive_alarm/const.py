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
CONF_VIBRATION_SENSORS = "vibration_sensors"
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
