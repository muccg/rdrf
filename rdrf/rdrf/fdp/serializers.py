from rdflib import BNode, Literal, URIRef
from rdflib.plugins.serializers.turtle import RecursiveSerializer, TurtleSerializer, VERB, _GEN_QNAME_FOR_DT
from rdflib.serializer import Serializer
from rdflib import plugin


# The default TurtleSerializer does auto generate prefixes like ns1, ns2, ..., nsN
# We don't want that functionality
class CustomTurtleSerializer(TurtleSerializer):
    def preprocessTriple(self, triple):
        RecursiveSerializer.preprocessTriple(self, triple)

        for i, node in enumerate(triple):
            if node in self.keywords:
                continue
            # Don't use generated prefixes for subjects and objects
            # self.getQName(node, gen_prefix=(i == VERB))
            self.getQName(node, gen_prefix=False)
            if isinstance(node, Literal) and node.datatype:
                self.getQName(node.datatype, gen_prefix=_GEN_QNAME_FOR_DT)
        p = triple[1]
        if isinstance(p, BNode): # hmm - when is P ever a bnode?
            self._references[p]+=1

    def getQName(self, uri, gen_prefix=True):
        if not isinstance(uri, URIRef):
            return None

        parts = None

        try:
            # parts = self.store.compute_qname(uri, generate=gen_prefix)
            parts = self.store.compute_qname(uri, generate=False)
        except:

            # is the uri a namespace in itself?
            pfx = self.store.store.prefix(uri)

            if pfx is not None:
                parts = (pfx, uri, '')
            else:
                # nothing worked
                return None

        prefix, namespace, local = parts

        # QName cannot end with .
        if local.endswith("."): return None

        prefix = self.addNamespace(prefix, namespace)

        return u'%s:%s' % (prefix, local)

