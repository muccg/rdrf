from base import BaseRegistration


class AngelmanRegsitration(object, BaseRegistration):

    def __init__(self, user, request):
        super(AngelmanRegistration, self).__init__(user, request)

    def process(self,):
        pass
