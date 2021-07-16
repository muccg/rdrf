class DummyCSPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = ''
        response = self.get_response(request)
        return response
