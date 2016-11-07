if __name__ == "__main__":
    import unittest
    from .tests import suite

    unittest.TextTestRunner(verbosity=2).run(suite)
