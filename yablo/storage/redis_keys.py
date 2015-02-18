# Note: redis keys will be prefixed by the first three letters in
# the chain name defined in the config file.
from ..config import app_config


PREFIX = app_config['key_prefix']

# Keys for cached query. Remember to set a ttl for them
# as redis is expected to be configured to evict those
# based on memory usage.
# These keys are expected to store a single string.
QUERY_CACHE = PREFIX + ":q:%s"

# Keys used for handling events.
# Always use RPUSH.
HANDLE_EVENT = PREFIX + ":evt"
HANDLE_EVENT_TEMP = PREFIX + ":evt:t"
SEND_EVENT = PREFIX + ":send"
SEND_EVENT_TEMP = PREFIX + ":send:t"

# Types to use when storing events to be processed.
EVENT_NEW_BLOCK = 0
EVENT_BLOCKDISC = 1
EVENT_NEW_TRANS = 2

# Types to use when publishing events.
EVENT_METHOD_WEBHOOK = 0
EVENT_WATCH_BLOCK = 0
EVENT_WATCH_ADDR = 1
EVENT_WATCH_BLOCKDISC = 2
