__version__ = "0.1"

# Load the config before other imports.
# XXX Accept path from env var.
from .config import parse_config
parse_config('yablo.cfg')
