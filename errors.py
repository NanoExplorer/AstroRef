class InternalServerError(Exception):
    def __init__(self):
        super(InternalServerError,self).__init__()
class APILimitError(Exception):
    def __init__(self):
        super(APILimitError,self).__init__()