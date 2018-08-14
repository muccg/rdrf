
class RulesParser:
    def __init__(self):
        self.rules = []

    def load(self, registry_model):
        self.rules = registry_model.metadata["rules"]

    def run(self, stage):
        pass
        
