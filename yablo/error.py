class ErrorFrontend(object):
    err_already_exists = {
        'code': 409,
        'msg': 'already exists'
    }


class YabloException(Exception):
    pass


class ConfigException(YabloException):
    """Error caused by missing configuration parameters."""
    pass
