import os
import uuid
import zope.interface
import zope.schema
from zope.schema.vocabulary import SimpleVocabulary
from lxml import etree
from owslib.iso import MD_Metadata

from ckanext.publicamundi import reference_data
from ckanext.publicamundi.lib.metadata.base import Object, object_null_adapter
from ckanext.publicamundi.lib.metadata.schemata.inspire_metadata import IInspireMetadata
from ckanext.publicamundi.lib.metadata import vocabularies
from ckanext.publicamundi.lib.metadata import xml_serializers
from ckanext.publicamundi.lib.metadata.xml_serializers import object_xml_serialize_adapter

from ckanext.publicamundi.lib.metadata.types import BaseMetadata
from ckanext.publicamundi.lib.metadata.types.thesaurus import Thesaurus, ThesaurusTerms
from ckanext.publicamundi.lib.metadata.types._common import *

class KeywordsFactory(object):
    
    __slots__ = ('_name',)

    def __init__(self, thesaurus_name='keywords-gemet-inspire-themes'):
        self._name = thesaurus_name
    
    def __call__(self):
        keywords = {}
        keywords[self._name] = ThesaurusTerms(
            terms=[], thesaurus=Thesaurus.make(self._name))
        return keywords

class TemporalExtentFactory(object):
    
    def __call__(self):
        return [TemporalExtent()]

class SpatialResolutionFactory(object):
    
    def __call__(self):
        return [SpatialResolution()]

class ConformityFactory(object):
    
    def __call__(self):
        return [Conformity(title=None, degree=None)]

@object_null_adapter()
class InspireMetadata(BaseMetadata):
    
    zope.interface.implements(IInspireMetadata)

    contact = list
    datestamp = None
    languagecode = None
    
    title = None
    identifier = None
    abstract = None
    locator = list
    resource_language = list
    
    topic_category = list

    keywords = KeywordsFactory()
    free_keywords = list

    bounding_box = list

    temporal_extent = TemporalExtentFactory()

    creation_date = None
    publication_date = None
    revision_date = None
    lineage = None
    
    spatial_resolution = SpatialResolutionFactory()
    
    conformity = list 
    
    access_constraints = list
    limitations = list
    
    responsible_party = list

    def deduce_basic_fields(self):
        data = super(InspireMetadata, self).deduce_basic_fields()
        
        data['notes'] = self.abstract
        
        identifier = None
        try:
            identifier = uuid.UUID(self.identifier)
        except:
            pass
        else:
            data['id'] = str(identifier)
        
        return data

# XML serialization

@object_xml_serialize_adapter(IInspireMetadata)
class InspireMetadataXmlSerializer(xml_serializers.BaseObjectSerializer):

    def to_xsd(self, wrap_into_schema=False, type_prefix='', annotate=False):
        '''Return the XSD document as an etree Element.
        '''

        # Note We do not support providing parts of it 
        assert wrap_into_schema

        xsd_file = reference_data.get_path('xsd/isotc211.org-2005/gmd/metadataEntity.xsd')

        xsd = None
        with open(xsd_file, 'r') as fp:
            xsd = etree.parse(fp)
        return xsd.getroot()

    def dumps(self, o=None):
        '''Dump object (instance of InspireMetadata) o as an INSPIRE-complant XML 
        document.
        '''

        import ckan.plugins as p

        if o is None:
            o = self.obj

        s = p.toolkit.render('package/inspire_iso.xml', extra_vars={ 'data': o })
        # Convert: render() always returns unicode
        return s.encode('utf-8') 

    def to_xml(self, o=None, nsmap=None):
        '''Build and return an etree Element to serialize an object (instance of
        InspireMetadata) o.

        Here, in contrast to what base XML serializer does, we build the etree by
        parsing the XML string (generated by a Jinja2 template).
        '''

        s = self.dumps(o)
        e = etree.fromstring(s)
        return e

    def from_xml(self, e):
        '''Build and return an InspireMetadata object serialized as an etree
        Element e.
        '''

        def to_date(string):
            if isinstance(string, str):
                return datetime.datetime.strptime(string,'%Y-%m-%d').date()
            else:
                return None

        def to_resp_party(alist):
            result = []
            for it in alist:
                result.append(ResponsibleParty(
                    organization = unicode(it.organization),
                    email = unicode(it.email),
                    role = it.role))
            return result

        md = MD_Metadata(e)

        datestamp = to_date(md.datestamp)
        id_list = md.identification.uricode

        url_list = []
        if md.distribution:
            for it in md.distribution.online:
                url_list.append(it.url)

        topic_list = []
        for topic in md.identification.topiccategory:
            topic_list.append(topic)
        
        keywords_dict = {}
        free_keywords = []
        print 'start here'
        for it in md.identification.keywords:
            print it
            thes_title = it['thesaurus']['title']
            if thes_title is None:
                date = to_date(it['thesaurus']['date'])
                datetype= it['thesaurus']['datetype']
                title = it['thesaurus']['title']
                for t in it['keywords']:
                    free_keywords.append(FreeKeyword(value=t, reference_date=date, date_type=datetype, originating_vocabulary=title ))
            else:
                thes_split = thes_title.split(',')
                # TODO thes_split[1] (=version) can be used in a get_by_title_and_version() 
                # to enforce a specific thesaurus version.
                thes_title = thes_split[0]
                try:
                    thes_name = vocabularies.munge('Keywords-' + thes_title)
                    term_list = []
                    for t in it['keywords']:
                        term_list.append(t)
                    thes = Thesaurus.make(thes_name)
                    if thes:
                        kw = ThesaurusTerms(thesaurus=thes, terms=term_list)
                        keywords_dict.update({thes_name:kw})

                except ValueError:
                    print 'free keywords with name'
                    date = to_date(it['thesaurus']['date'])
                    datetype= it['thesaurus']['datetype']
                    title = it['thesaurus']['title']
                    for t in it['keywords']:
                        free_keywords.append(FreeKeyword(value=t, reference_date=date, date_type=datetype, originating_vocabulary=title ))

        temporal_extent = []
        if md.identification.temporalextent_start or md.identification.temporalextent_end:
            temporal_extent = [TemporalExtent(
                start = to_date(md.identification.temporalextent_start),
                end = to_date(md.identification.temporalextent_end))]

        bbox = []
        if md.identification.extent:
            if md.identification.extent.boundingBox:
                bbox = [GeographicBoundingBox(
                    nblat = float(md.identification.extent.boundingBox.maxy),
                    sblat = float(md.identification.extent.boundingBox.miny),
                    eblng = float(md.identification.extent.boundingBox.maxx),
                    wblng = float(md.identification.extent.boundingBox.minx))]

        creation_date = None
        publication_date = None
        revision_date = None

        for it in md.identification.date:
            if it.type == 'creation':
                creation_date = to_date(it.date)
            elif it.type == 'publication':
                publication_date = to_date(it.date)
            elif it.type == 'revision':
                revision_date = to_date(it.date)

        #if not creation_date:
        #    raise Exception('creation date not present','')
        #elif not publication_date:
        #    raise Exception('publication date not present','')
        #elif not revision_date:
        #    raise Exception('revision date not present','')

        spatial_list = []

        if len(md.identification.distance) != len(md.identification.uom):
            raise Exception(
                'Found unequal list lengths distance,uom (%s, %s)' % (
                    md.identification.distance,md.identification.uom))
        else:
                for i in range(0,len(md.identification.distance)):
                    spatial_list.append(SpatialResolution(
                        distance = int(md.identification.distance[i]),
                        uom = unicode(md.identification.uom[i])))

                for i in range(0, len(md.identification.denominators)):
                    spatial_list.append(SpatialResolution(
                        denominator = int(md.identification.denominators[i])))
        conf_list = []
        invalid_degree = False

        if len(md.dataquality.conformancedate) != len(md.dataquality.conformancedatetype):
            # Date list is unequal to datetype list, this means wrong XML so exception is thrown
            raise Exception('Found unequal list lengths: conformance date, conformancedatetype')
        if len(md.dataquality.conformancedegree) != len(md.dataquality.conformancedate):
            # Degree list is unequal to date/datetype lists, so we are unable to conclude
            # to which conformity item each degree value corresponds, so all are set to 
            # not-evaluated (Todo: MD_Metadata bug #63)
            invalid_degree = True

        if md.dataquality.conformancedate:
        #and len(md.dataquality.conformancedate) == len(md.dataquality.degree):
            for i in range(0,len(md.dataquality.conformancedate)):

                date = to_date(md.dataquality.conformancedate[i])

                date_type = md.dataquality.conformancedatetype[i]
                # TODO md.dataquality.conformancedatetype returns empty
                if invalid_degree:
                    degree = 'not-evaluated'
                else:
                    try:
                        if md.dataquality.conformancedegree[i] == 'true':
                            degree = 'conformant'
                        elif md.dataquality.conformancedegree[i] == 'false':
                            degree = 'not-conformant'
                    except:
                        degree = "not-evaluated"
                title = unicode(md.dataquality.conformancetitle[i])
                if title != 'None': 
                    conf_list.append(Conformity(title=title, date=date, date_type=date_type, degree=degree))

                # TODO: is title required fields? If so the following is unnecessary
                else:
                    conf_list.append(Conformity(date=date, date_type=date_type, degree=degree))

        limit_list = []
        for it in md.identification.uselimitation:
                limit_list.append(unicode(it))
        constr_list = []
        for it in md.identification.otherconstraints:
                constr_list.append(unicode(it))

        obj = InspireMetadata()

        obj.contact = to_resp_party(md.contact)
        obj.datestamp = datestamp
        obj.languagecode = md.languagecode
        obj.title = unicode(md.identification.title)
        obj.abstract = unicode(md.identification.abstract)
        obj.identifier = id_list[0]
        obj.locator = url_list
        #obj.resource_language = md.identification.resourcelanguage
        obj.topic_category = topic_list
        obj.keywords = keywords_dict
        print free_keywords
        obj.free_keywords = free_keywords
        obj.bounding_box = bbox
        obj.temporal_extent = temporal_extent
        obj.creation_date = creation_date
        obj.publication_date = publication_date
        obj.revision_date = revision_date
        obj.lineage = unicode(md.dataquality.lineage)
        obj.spatial_resolution = spatial_list
        obj.conformity = conf_list
        obj.access_constraints = limit_list
        obj.limitations = constr_list
        obj.responsible_party = to_resp_party(md.identification.contact)

        return obj

