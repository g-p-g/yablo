from .config import parse_config

__version__ = "0.1"

# XXX Accept path from env var.
parse_config('yablo.cfg')
