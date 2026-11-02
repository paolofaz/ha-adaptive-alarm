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
# Legacy 0.2 / 0.3 options are deliberately ignored: no silent re-pairing.
CONF_VIBRATION_SENSORS = "vibration_sensors"
CONF_VIBRATION_1 = "vibration_1"
CONF_VIBRATION_2 = "vibration_2"
CONF_VIBRATION_3 = "vibration_3"

# Physical mounting locations; target contact is NOT user-selectable.
CONF_VIBRATION_ENTRY = "vibration_entry"
CONF_VIBRATION_WINDOW_LIVING = "vibration_window_living"
CONF_VIBRATION_WINDOW_BATH = "vibration_window_bath"
VIBRATION_ASSIGNMENTS = (
    (CONF_VIBRATION_ENTRY, CONF_ENTRY_CONTACT),
    (CONF_VIBRATION_WINDOW_LIVING, CONF_WINDOW_LIVING),
    (CONF_VIBRATION_WINDOW_BATH, CONF_WINDOW_BATH),
)
CONF_STORM_SENSOR = "storm_sensor"
CONF_ARMING_DELAY = "arming_delay"
CONF_VIBRATION_PROFILE = "vibration_profile"
CONF_VIBRATION_WINDOW = "vibration_window"
CONF_VIBRATION_DEBOUNCE = "vibration_debounce"
CONF_RECOVERY_POLICY = "recovery_policy"

DEFAULT_ARMING_DELAY = 60
DEFAULT_VIBRATION_PROFILE = "balanced"
DEFAULT_VIBRATION_WINDOW = 20
DEFAULT_VIBRATION_DEBOUNCE = 3
DEFAULT_RECOVERY_POLICY = "notify"

EVENT_ADAPTIVE_ALARM = "adaptive_alarm_event"

# New per-device confirmation, independent of deprecated global profiles.
CONF_VIBRATION_THRESHOLD = "vibration_threshold"
DEFAULT_VIBRATION_THRESHOLD = 2

# Output opt-in: ONLY light-domain entities and ONLY on first valid prealert.
# Sirens, switches, locks and RF remain permanently inert.
CONF_DETERRENT_LIGHTS = "deterrent_lights"
CONF_DETERRENT_ENABLED = "deterrent_enabled"
DEFAULT_DETERRENT_ENABLED = False

# v0.6.0 — light timer is a SECOND opt-in. Existing users keep their
# v0.5.0 behavior until explicitly enabling automatic light-off.
CONF_DETERRENT_AUTO_OFF = "deterrent_auto_off"
CONF_DETERRENT_OFF_DELAY = "deterrent_off_delay"
DEFAULT_DETERRENT_OFF_DELAY = 120

# Phone/push routes must be explicitly configured. Modern Telegram Bot chat
# targets appear as notify entities; mobile apps generally use notify services.
CONF_NOTIFY_ENABLED = "notifications_enabled"
CONF_NOTIFY_ENTITIES = "notification_entities"
CONF_NOTIFY_SERVICES = "notification_services"
