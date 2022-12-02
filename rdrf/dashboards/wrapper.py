from django_plotly_dash import DjangoDash


class CSPDjangoDash(DjangoDash):
    def __init__(self, *args, **kwargs):
        self.csp = kwargs.pop("csp")
        super().__init__(self, *args, **kwargs)

    def csp_wrap(self, csp_dict):

        content_security_policy = {
            "default-src": "'self'",
            "script-src": ["'self'"] + app.csp_hashes_inline_scripts(),
        }
