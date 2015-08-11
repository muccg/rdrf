from base import Base


class FhCalculationTest(Base):
    def test_registry_import_works(self):
        self.import_registry("fh.yaml")
