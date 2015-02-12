class ErrorFrontend(object):
    err_already_exists = {
        'code': 409,
        'msg': 'already exists'
    }

    err_not_found = {
        'code': 404,
        'msg': 'resource not found'
    }


class YabloException(Exception):
    pass


class ConfigException(YabloException):
    """Error caused by missing configuration parameters."""
    pass
