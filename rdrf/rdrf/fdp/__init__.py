from rdflib import plugin, serializer, store
import rdflib_sqlalchemy

# Fair Data Point

# Returns FDP root, Catalogue, Dataset, Distributions and Patient endpoints
# Samples of how they should look are at the end of the file.


plugin.register('text/turtle', serializer.Serializer, 'rdrf.fdp.serializers', 'CustomTurtleSerializer')
plugin.register('turtle', serializer.Serializer, 'rdrf.fdp.serializers', 'CustomTurtleSerializer')


# rdflib_sqlalchemy.registerplugins()
plugin.register('SQLAlchemy', store.Store, 'rdrf.fdp.stores', 'OurSQLAlchemyStore')


_FDP = '''\
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix fdp-o: <http://rdf.biosemantics.org/ontologies/fdp-o#> .
@prefix ldp: <http://www.w3.org/ns/ldp#> .
@prefix lang: <http://id.loc.gov/vocabulary/iso639-1/> .

<http://localhost:8084/fdp> dcterms:title "FDP of localhost:8084" ;
  rdfs:label "FDP of localhost:8084" ;
  dcterms:identifier "e6d510fc6a73c32d66b9360f14174f1e" ;
  dcterms:hasVersion "1.0" ;
  dcterms:issued "2016-10-27T14:06:05.699+02:00"^^xsd:dateTime ;
  dcterms:modified "2016-10-27T14:07:53.242+02:00"^^xsd:dateTime ;
  dcterms:language lang:en ;
  dcterms:description "FDP of localhost:8084" ;
  dcterms:license <http://rdflicense.appspot.com/rdflicense/cc-by-nc-nd3.0> ;
  a ldp:Container ;
  rdfs:seeAlso <http://localhost:8084/fdp/swagger-ui.html> ;
  ldp:contains <http://localhost:8084/fdp/mtmcatalog> .
'''

_CATALOG = '''\
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix fdp-o: <http://rdf.biosemantics.org/ontologies/fdp-o#> .
@prefix ldp: <http://www.w3.org/ns/ldp#> .
@prefix lang: <http://id.loc.gov/vocabulary/iso639-1/> .

<http://localhost:8084/fdp/mtmcatalog> dcterms:title "Catalog for MTM" ;
  rdfs:label "Catalog for MTM" ;
  dcterms:identifier "mtmcatalog" ;
  dcterms:hasVersion "1.0" ;
  dcterms:issued "2016-10-27T14:07:53.240+02:00"^^xsd:dateTime ;
  dcterms:modified "2016-10-27T14:08:49.260+02:00"^^xsd:dateTime ;
  dcterms:language lang:en ;
  a dcat:Catalog ;
  dcat:themeTaxonomy <http://purl.bioontology.org/ontology/MESH/D003625> ;
  dcat:dataset <http://localhost:8084/fdp/mtmcatalog/mtmdataset> .
'''


_DATASET = '''\
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix fdp-o: <http://rdf.biosemantics.org/ontologies/fdp-o#> .
@prefix ldp: <http://www.w3.org/ns/ldp#> .
@prefix lang: <http://id.loc.gov/vocabulary/iso639-1/> .

<http://localhost:8084/fdp/mtmcatalog/mtmdataset> dcterms:title "Dataset for MTM" ;
  rdfs:label "Dataset for MTM" ;
  dcterms:identifier "mtmdataset" ;
  dcterms:hasVersion "1.0" ;
  dcterms:issued "2016-10-27T14:08:49.257+02:00"^^xsd:dateTime ;
  dcterms:modified "2016-10-27T14:22:39.981+02:00"^^xsd:dateTime ;
  dcterms:language lang:en ;
  dcterms:publisher <http://orcid.org/0000-0002-6816-4445> ;
  dcterms:description "mtm" ;
  a dcat:Dataset ;
  dcat:landingPage <http://mtmcnmregistry.org> ;
  dcat:theme <http://purl.bioontology.org/ontology/MESH/D003625> ;
  dcat:keyword "centronuclear" , "mtm" , "myotubular" , "patient" , "registry" ;
  dcat:distribution <http://localhost:8084/fdp/mtmcatalog/mtmdataset/RDF> , <http://localhost:8084/fdp/mtmcatalog/mtmdataset/RDF-1> , <http://localhost:8084/fdp/mtmcatalog/mtmdataset/RDF-3> , <http://localhost:8084/fdp/mtmcatalog/mtmdataset/RDF-sftp> .
'''


_DISTRIBUTION = '''\
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix fdp-o: <http://rdf.biosemantics.org/ontologies/fdp-o#> .
@prefix ldp: <http://www.w3.org/ns/ldp#> .
@prefix lang: <http://id.loc.gov/vocabulary/iso639-1/> .

<http://localhost:8084/fdp/mtmcatalog/mtmdataset/RDF-3> dcterms:title "mtm RDF" ;
  rdfs:label "mtm RDF" ;
  dcterms:identifier "mtmdataset" ;
  dcterms:hasVersion "1.0" ;
  dcterms:issued "2016-10-27T14:21:37.898+02:00"^^xsd:dateTime ;
  dcterms:modified "2016-10-27T14:21:37.898+02:00"^^xsd:dateTime ;
  dcterms:license <http://rdflicense.appspot.com/rdflicense/cc-by-nc-nd3.0> ;
  a dcat:Distribution ;
  dcat:accessURL <http://example.com/home/citroen/mtm.2.ttl> ;
  dcat:mediaType "text/turtle" .
'''


_PATIENTS = '''\
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .


<http://132.229.130.125:8000/api/v1/registries/mtm/patients/3/> a <http://rdf.biosemantics.org/ontologies/rd-connect/d212d920_6507_45fc_9751_830485f89425> ;
  foaf:firstName "Betty" ;
  foaf:lastName "BOOP" ;
  <http://dbpedia.org/ontology/gender> <http://dbpedia.org/resource/Female> ;
  <http://rdf.biosemantics.org/ontologies/byod-leiden-2016-onto#67e95ecc-9b69-11e6-9f33-a24fc0d9649c> <http://www.orpha.net/ORDO/Orphanet_456328> ;
  <http://rdf.biosemantics.org/ontologies/byod-leiden-2016-onto#67e9614c-9b69-11e6-9f33-a24fc0d9649c> <http://purl.obolibrary.org/obo/CHEBI_353417> .

<http://localhost:3333/wheelchair/0> a <http://purl.bioontology.org/ontology/SNOMEDCT/58938008> .

<http://localhost:3333/question/0> a <http://purl.bioontology.org/ontology/LNC/52640-0> .

<http://localhost:3333/deviceuse/0> <http://rdf.biosemantics.org/ontologies/byod-leiden-2016-onto#96131e22-9c2d-11e6-80f5-76304dec7eb7> <http://localhost:3333/question/0> .

<http://localhost:3333/wheelchair/0> <http://rdf.biosemantics.org/ontologies/byod-leiden-2016-onto#961318b4-9c2d-11e6-80f5-76304dec7eb7> <http://localhost:3333/deviceuse/0> .

<http://132.229.130.125:8000/api/v1/registries/mtm/patients/3/> <http://purl.bioontology.org/ontology/SNOMEDCT/uses_device> <http://localhost:3333/wheelchair/0> .

<http://localhost:3333/phenotype/0> a <http://purl.obolibrary.org/obo/HP_00069577> ;
  <http://purl.obolibrary.org/obo/RO_0000086> "11"^^xsd:int .

<http://132.229.130.125:8000/api/v1/registries/mtm/patients/3/> <http://rdf.biosemantics.org/ontologies/rd-connect/59e1324d_567b_42e1_bc88_203004e660da> <http://localhost:3333/phenotype/0> .

<http://132.229.130.125:8000/api/v1/registries/mtm/patients/6/> a <http://rdf.biosemantics.org/ontologies/rd-connect/d212d920_6507_45fc_9751_830485f89425> ;
  foaf:firstName "Eileen" ;
  foaf:lastName "HARRIS" ;
  <http://dbpedia.org/ontology/gender> <http://dbpedia.org/resource/Female> ;

  <http://rdf.biosemantics.org/ontologies/byod-leiden-2016-onto#67e9614c-9b69-11e6-9f33-a24fc0d9649c> <http://purl.obolibrary.org/obo/CHEBI_353417> .

<http://localhost:3333/wheelchair/1> a <http://purl.bioontology.org/ontology/SNOMEDCT/58938008> .

<http://localhost:3333/question/1> a <http://purl.bioontology.org/ontology/LNC/52640-0> .

<http://localhost:3333/deviceuse/1> <http://rdf.biosemantics.org/ontologies/byod-leiden-2016-onto#96131e22-9c2d-11e6-80f5-76304dec7eb7> <http://localhost:3333/question/1> .

<http://localhost:3333/wheelchair/1> <http://rdf.biosemantics.org/ontologies/byod-leiden-2016-onto#961318b4-9c2d-11e6-80f5-76304dec7eb7> <http://localhost:3333/deviceuse/1> .

<http://132.229.130.125:8000/api/v1/registries/mtm/patients/6/> <http://purl.bioontology.org/ontology/SNOMEDCT/uses_device> <http://localhost:3333/wheelchair/1> .

<http://localhost:3333/phenotype/1> a <http://purl.obolibrary.org/obo/HP_00069577>  .

<http://132.229.130.125:8000/api/v1/registries/mtm/patients/6/> <http://rdf.biosemantics.org/ontologies/rd-connect/59e1324d_567b_42e1_bc88_203004e660da> <http://localhost:3333/phenotype/1> .

'''


