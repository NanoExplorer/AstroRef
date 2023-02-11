class InternalServerError(Exception):
    def __init__(self):
        super(InternalServerError,self).__init__()


class APILimitError(Exception):
    def __init__(self):
        super(APILimitError,self).__init__()


class ADSMalfunctionError(Exception):
    def __init__(self):
        super(ADSMalfunctionError,self).__init__()
        

class UnauthorizedError(Exception):
    def __init__(self):
        super(UnauthorizedError,self).__init__()
