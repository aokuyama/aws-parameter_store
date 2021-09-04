class LocalClient:
    def __init__(self, params={}):
        self.params = params

    def get_parameters(self, names):
        values = {}
        for name in names:
            values[name] = self.params[name]
        return values
