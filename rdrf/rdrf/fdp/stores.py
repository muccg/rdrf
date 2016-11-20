from rdflib.store import VALID_STORE
import rdflib_sqlalchemy.store

from sqlalchemy.engine import reflection


class OurSQLAlchemyStore(rdflib_sqlalchemy.store.SQLAlchemy):

    def close(self, commit_pending_transaction=False):
        # There is no close() method on SQLAlchemy Engine objects
        # if self.engine:
        #    self.engine.close()
        self.engine = None

    def open(self, configuration, create=True):
        # Problem 1:
        # According to the rdflib.Store.open docs if create=False
        # and the store doesn't exist an exceptions should be raised.
        # The SQLAlchemy store didn't raise an Exception so we do it here
        #
        # Problem 2:
        # The SQLAlchemy store returns None if everything goes ok
        # We return VALID_STORE instead
        ret = super().open(configuration, create) or VALID_STORE
        if not create:
            inspector = reflection.Inspector.from_engine(self.engine)
            existing_table_names = set(inspector.get_table_names())
            if len(set(self.table_names) & existing_table_names) == 0:
                raise Exception("Store doesn't exist")
        return ret
