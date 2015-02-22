class ErrorFrontend(object):
    err_already_exists = {
        'code': 409,
        'msg': 'already exists'
    }

    err_not_found = {
        'code': 404,
        'msg': 'resource not found'
    }

    mapping = {
        409: 'err_already_exists',
        404: 'err_not_found'
    }

    @staticmethod
    def get_msg(code):
        if code in ErrorFrontend.mapping:
            res = getattr(ErrorFrontend, ErrorFrontend.mapping[code])
            return res['msg']


class YabloException(Exception):
    pass


class ConfigException(YabloException):
    """Error caused by missing configuration parameters."""
    pass
