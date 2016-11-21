from datetime import datetime

from django.conf import settings
from django.shortcuts import reverse
from django.utils.encoding import iri_to_uri

import logging

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, plugin
from rdflib.compare import graph_diff, to_isomorphic
from rdflib.namespace import DCTERMS, FOAF, XSD
from rdflib.store import Store, CORRUPTED_STORE, VALID_STORE

import uuid
from urllib.parse import urljoin

from ..models import Registry
from registry.patients import models as m


logger = logging.getLogger(__name__)


DCAT = Namespace('http://www.w3.org/ns/dcat#')
LDP = Namespace('http://www.w3.org/ns/ldp#')
LANG = Namespace('http://id.loc.gov/vocabulary/iso639-1/')


class Base():
    def __init__(self, uri, build_absolute_uri=None):
        self.uri = uri
        self.build_absolute_uri = self.build_uri if build_absolute_uri is None else build_absolute_uri

        self.persister = GraphPersister(self.ident)

    @property
    def ident(self):
        if hasattr(self, 'registry_code'):
            return URIRef('%s-%s' % (self.IDENT, self.registry_code))
        return URIRef(self.IDENT)

    @property
    def node(self):
        return URIRef(self.uri)

    def build_uri(self, path):
        return iri_to_uri(urljoin(self.uri, path))

    def defaults(self, g):
        g.bind('ldp', LDP)
        g.bind('dcat', DCAT)
        g.bind('dcterms', DCTERMS)
        g.bind('lang', LANG)

    def load_graph(self):
        g = self.persister.load()

        if g is None:
            logger.info('Creating graph for "%s"', self.ident)
            g = Graph()
            self.defaults(g)
            self.persister.create(self.node, g)
            g = self.persister.load()

        return g

    def save(self, g):
        self.persister.overwrite(self.node, g)

    def delete(self):
        self.persister.delete()


class FDP(Base):
    IDENT = 'fdp-root'
    DYNAMIC = (LDP.Contains,)

    def defaults(self, g):
        super().defaults(g)
        label = Literal('RDRF Fair Data Point')

        g.set((self.node, RDF.type, LDP.Container))

        g.set((self.node, DCTERMS.identifier, Literal(uuid.uuid1())))
        g.set((self.node, DCTERMS.title, label))
        g.set((self.node, RDFS.label, label))
        g.set((self.node, DCTERMS.hasVersion, Literal('1.0')))
        g.set((self.node, DCTERMS.language, LANG.en))
        g.set((self.node, DCTERMS.description, label))
        g.set((self.node, DCTERMS.license, URIRef('http://rdflicense.appspot.com/rdflicense/cc-by-nc-nd3.0')))
        self.load_dynamic(g)

    def load_dynamic(self, g):
        for t in filter(lambda t: t[1] in self.DYNAMIC, g):
            g.remove(t)
        for registry in Registry.objects.all():
            g.add((self.node, LDP.Contains, URIRef(self.build_absolute_uri(reverse('catalog', kwargs={'registry_code': registry.code})))))

    def did_dynamic_data_change(self, g):
        current_dynamic = Graph()
        for t in filter(lambda t: t[1] in self.DYNAMIC, g):
            current_dynamic.add(t)

        new_dynamic = Graph()
        self.load_dynamic(new_dynamic)

        if (len(current_dynamic) != len(new_dynamic)):
            return True

        both, first, second = graph_diff(to_isomorphic(current_dynamic), to_isomorphic(new_dynamic))

        return not (len(both) == len(new_dynamic) and len(first) == len(second) == 0)

    def load_graph(self):
        g = super().load_graph()

        if self.did_dynamic_data_change(g):
            self.load_dynamic(g)
            self.save(g)
            g = self.load_graph()

        return g


class Catalog(Base):
    IDENT = 'fdp-catalog'

    def __init__(self, uri, registry_code, *args, **kwargs):
        self.registry_code = registry_code
        super().__init__(uri, *args, **kwargs)

    def defaults(self, g):
        super().defaults(g)
        label = 'Catalog for %s' % self.registry_code.upper()

        g.set((self.node, RDF.type, DCAT.Catalog))

        g.add((self.node, DCTERMS.identifier, Literal('%scatalog' % self.registry_code)))
        g.add((self.node, DCTERMS.title, Literal(label)))
        g.add((self.node, RDFS.label, Literal(label)))
        g.add((self.node, DCTERMS.hasVersion, Literal('1.0')))
        g.add((self.node, DCTERMS.language, LANG.en))
        g.add((self.node, DCAT.themeTaxonomy, URIRef('http://purl.bioontology.org/ontology/MESH/D003625')))
        g.add((self.node, DCAT.dataset, URIRef(self.build_absolute_uri(reverse('dataset', kwargs={'registry_code': self.registry_code})))))


class Dataset(Base):
    IDENT = 'fdp-dataset'

    def __init__(self, uri, registry_code, *args, **kwargs):
        self.registry_code = registry_code
        super().__init__(uri, *args, **kwargs)

    def defaults(self, g):
        super().defaults(g)
        label = 'Dataset for %s' % self.registry_code.upper()

        g.add((self.node, RDF.type, DCAT.Dataset))

        g.add((self.node, DCTERMS.title, Literal(label)))
        g.add((self.node, RDFS.label, Literal(label)))
        g.add((self.node, DCTERMS.identifier, Literal('%sdataset' % self.registry_code)))
        g.add((self.node, DCTERMS.hasVersion, Literal('1.0')))
        g.add((self.node, DCTERMS.language, LANG.en))
        # TODO this orcid id isn't ours
        g.add((self.node, DCTERMS.publisher, URIRef('http://orcid.org/0000-0002-6816-4445')))
        g.add((self.node, DCTERMS.description, Literal(self.registry_code.upper())))
        # TODO make this configurable
        g.add((self.node, DCAT.landingPage, URIRef('http://mtmcnmregistry.org')))
        g.add((self.node, DCAT.theme, URIRef('http://purl.bioontology.org/ontology/MESH/D003625')))

        # TODO add ability for registry to define keywords?
        # For example for MTM: 'centronuclear', 'myotubular', etc.
        keywords = ('registry', 'patient', self.registry_code)
        addAll(g, self.node, DCAT.keyword, [Literal(o) for o in keywords])

        g.add((self.node, DCAT.distribution, URIRef(self.build_absolute_uri(reverse('distribution', kwargs={'registry_code': self.registry_code})))))


class Distribution(Base):
    IDENT = 'fdp-distribution'

    def __init__(self, uri, registry_code, *args, **kwargs):
        self.registry_code = registry_code
        super().__init__(uri, *args, **kwargs)

    def defaults(self, g):
        super().defaults(g)
        label = '%s RDF' % self.registry_code.upper()

        g.add((self.node, RDF.type, DCAT.Distribution))

        g.add((self.node, DCTERMS.identifier, Literal('%s-rdf-distribution' % self.registry_code)))
        g.add((self.node, DCTERMS.title, Literal(label)))
        g.add((self.node, RDFS.label, Literal(label)))
        g.add((self.node, DCTERMS.hasVersion, Literal('1.0')))
        g.add((self.node, DCTERMS.license, URIRef('http://rdflicense.appspot.com/rdflicense/cc-by-nc-nd3.0')))
        g.add((self.node, DCAT.accesURL, URIRef(self.build_absolute_uri(reverse('patient', kwargs={'registry_code': self.registry_code})))))
        g.add((self.node, DCAT.mediaType, Literal('text/turtle')))


class Patient():
    def __init__(self, uri, registry_code, build_absolute_uri=None):
        self.uri = uri
        self.build_absolute_uri = self.build_uri if build_absolute_uri is None else build_absolute_uri
        self.registry_code = registry_code

    @property
    def ident(self):
        if hasattr(self, 'registry_code'):
            return URIRef('%s-%s' % (self.IDENT, self.registry_code))
        return URIRef(self.IDENT)

    @property
    def node(self):
        return URIRef(self.uri)

    def build_uri(self, path):
        return iri_to_uri(urljoin(self.uri, path))

    def load_graph(self):
        g = Graph()

        DBPEDIA = Namespace('http://dbpedia.org/ontology/')
        OBO = Namespace('http://purl.obolibrary.org/obo/')
        LEIDEN = Namespace('http://rdf.biosemantics.org/ontologies/byod-leiden-2016-onto#')

        PATIENT_TYPE = URIRef('http://purl.obolibrary.org/obo/NCBITaxon_9606')

        g.bind('dbpedia', DBPEDIA)
        g.bind('foaf', FOAF)
        g.bind('obo', OBO)
        g.bind('byod-leiden', LEIDEN)


        # registry = get_object_or_404(Registry, code=self.registry_code)
        registry = Registry.objects.get(code=self.registry_code)
        for p in m.Patient.objects.get_by_registry(registry):
            # TODO think about how to do this.
            # Requesting the patient URIs won't return anything
            # However, we don't want to include the real pk in the URI, we don't want
            # to link to the real data
            # We can keep it like this, or maybe make the patient a Literal('patient-' + UUID) instead
            patient_uri = self.build_absolute_uri(str(uuid.uuid1()))
            patient = URIRef(patient_uri)
            g.add((patient, RDF.type, PATIENT_TYPE))


            # TODO I could work more on making these mappings real, but we will have to do them
            # in a more general way, for example with RML instead.
            #
            # Ask the DTL guys what they recommend for it, before putting in more work.

            g.add((patient, FOAF.firstName, Literal(p.given_names)))
            g.add((patient, FOAF.lastName, Literal(p.family_name)))
            if p.sex:
                g.add((patient, DBPEDIA.gender,
                    URIRef('http://dbpedia.org/resource/%s' % ('Female' if p.sex == '2' else 'Male'))))

            HAS_DISEASE = LEIDEN['67e95ecc-9b69-11e6-9f33-a24fc0d9649c']

            MYOTUBULAR = URIRef('http://www.orpha.net/ORDO/Orphanet_456328')
            CENTRONUCLEAR = URIRef('http://www.orpha.net/ORDO/Orphanet_596')
            # TODO get the CDE value for diagnosis and set it
            g.add((patient, HAS_DISEASE, MYOTUBULAR if p.sex == '2' else CENTRONUCLEAR))

            # TODO get the steroid usage flag from dyamic data
            USES_SUBSTANCE = LEIDEN['67e9614c-9b69-11e6-9f33-a24fc0d9649c']
            STEROID = URIRef('http://purl.obolibrary.org/obo/CHEBI_353417')
            g.add((patient, USES_SUBSTANCE, STEROID))

            phenotype = URIRef(patient_uri + 'phenotype/0')
            LOSS_OF_ABILITY_TO_WALK = OBO.HP_0006957
            HAS_QUALITY = OBO.RO_0000086

            g.add((phenotype, RDF.type, LOSS_OF_ABILITY_TO_WALK))
            g.add((phenotype, HAS_QUALITY, Literal('6', datatype=XSD.integer)))

            HAS_PHENOTYPE = LEIDEN['59e1324d_567b_42e1_bc88_203004e660da']
            g.add((patient, HAS_PHENOTYPE, phenotype))

            # TODO maybe add wheelchair usage, but it isn't complete anyways
        return g


class GraphPersister():
    def __init__(self, ident, store_impl='SQLAlchemy'):
        self.ident = ident
        self.store_impl = store_impl

        self.store = plugin.get(self.store_impl, Store)(identifier=self.ident)

        self.DBURI = settings.FDP_DATABASE_URI

    def p_no_meta(self, triple):
        s, p, o = triple
        return not (p == DCTERMS.issued or p == DCTERMS.modified)

    def _open(self):
        g = Graph(self.store, identifier=self.ident)
        g.open(self.DBURI, create=True)
        return g

    def _copy_graph(self, src, dest, pfilter=None):
        for pref, ns in src.namespaces():
            dest.bind(pref, ns)
        to_copy = src if pfilter is None else filter(pfilter, src)
        for t in to_copy:
            dest.add(t)
        return dest

    def exists(self):
        return self.load() is not None

    def load(self):
        g = Graph(self.store, identifier=self.ident)
        try:
            ret = g.open(self.DBURI, create=False)
        except:
            return None

        if ret == CORRUPTED_STORE:
            raise Exception('%s store %s is corrupted' % (self.store_impl, self.ident))

        if ret != VALID_STORE:
            return None

        gc = self._copy_graph(g, Graph(identifier=self.ident))

        return gc

    def create(self, node, gin):
        g = self._open()
        self._copy_graph(gin, g, self.p_no_meta)

        now = datetime.now()
        # TODO move these into base or detect nodes
        g.set((node, DCTERMS.issued, Literal(now, datatype=XSD.dateTime)))
        g.set((node, DCTERMS.modified, Literal(now, datatype=XSD.dateTime)))

        g.commit()

    def delete(self):
        g = self._open()
        g.destroy(self.DBURI)

    def overwrite(self, node, gin):
        g = self._open()

        for t in filter(self.p_no_meta, g):
            g.remove(t)
        self._copy_graph(gin, g, self.p_no_meta)

        # TODO move these into base or detect nodes
        g.set((node, DCTERMS.modified, Literal(datetime.now(), datatype=XSD.dateTime)))

        g.commit()



def addAll(g, s, p, os):
    for o in os:
        g.add((s, p, o))


def turtle(g):
    return g.serialize(format='turtle').decode('utf8')
