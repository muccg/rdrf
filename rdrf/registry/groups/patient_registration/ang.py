from base import BaseRegistration


class AngelmanRegistration(BaseRegistration, object):

    def __init__(self, user, request):
        super(AngelmanRegistration, self).__init__(user, request)

    def process(self,):
        pass
