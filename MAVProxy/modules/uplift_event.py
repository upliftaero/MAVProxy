__author__ = 'mjlubuntu'

UPLIFT_PLANENAME_CHANGE = 0

class UpliftEvent:
    def __init__(self, type, **kwargs):
        self.type = type
        self.arg_dict = kwargs
