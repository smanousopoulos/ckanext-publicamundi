import logging

from pylons import config

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean
from sqlalchemy.types import Text, BigInteger
from sqlalchemy.schema import ForeignKey
from sqlalchemy.sql import delete
from sqlalchemy.orm import sessionmaker, mapper, relation, scoped_session

from geoalchemy import Geometry


log1 = logging.getLogger(__name__)


# Declare data model

class Organization(object):
    pass

class Group(object):
    pass

class Package(object):
    pass

class PackageGroup(object):
    pass

class Resource(object):
    pass

class Field(object):
    pass

class Queryable(object):
    pass

class TreeNode(object):
    pass

# MapClient class initializes mapclient database
class MapClient(object):
    def __init__(self):
        self.maps_db =  config.get('ckanext.publicamundi.themes.geodata.mapclient_db')

        self.engine = None
        self.metadata = None
        self.session = None

        if self.maps_db:
            try:
                self._initialize_session()
                self._initialize_model()
            except:
                self.engine = None
                log1.debug('Mapclient not set up correctly. Check database configuration')
        else:
            log1.info('Mapclient database option not found. Skipping')

    def _initialize_session(self):
        self.engine = create_engine(self.maps_db)
        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)

        #self.session = Session()
        #Session.configure(bind=self.engine)
        #self.session = session_factory()
        #self.session = self.Session()
        
        self.metadata = MetaData()

    def _initialize_model(self):
        self.organizations = Table('organization',
                                self.metadata,
                                autoload=True,
                                autoload_with=self.engine)


        self.groups = Table('group',
                        self.metadata,  
                        autoload=True,
                        autoload_with=self.engine)


        self.packages = Table('package',
                            self.metadata,
                            Column('the_geom', Geometry(4326)),
                            Column('organization', Text, ForeignKey('organization.id')),
                            autoload=True,
                            autoload_with=self.engine)

        self.package_groups = Table('package_group',
                                self.metadata,
                                Column('package_id', Text, ForeignKey('package.id')),
                                Column('group_id', Text, ForeignKey('group.id')),
                                autoload=True, 
                                autoload_with=self.engine)
        
        self.tree_nodes = Table('resource_tree_node',
                            self.metadata,
                            Column('parent', BigInteger, ForeignKey('resource_tree_node.id')),
                            autoload = True,
                            autoload_with = self.engine)
                    
        self.resources = Table('resource',
                            self.metadata,
                            Column('package', Text, ForeignKey('package.id')),
                            Column('tree_node_id', Text, ForeignKey('resource_tree_node.id')),
                            autoload=True,
                            autoload_with=self.engine)
        
        self.queryables = Table('resource_queryable',
                            self.metadata,
                            Column('resource', Text, ForeignKey('resource.id')),
                            autoload=True,
                            autoload_with=self.engine)
                            
        self.fields = Table('resource_field',
                        self.metadata,
                        Column('queryable', Text, ForeignKey('resource_queryable.id')),
                        autoload=True,
                        autoload_with=self.engine)
        
        # Do the mappings only once
        try:
            mapper(Organization, self.organizations)
            mapper(Group, self.groups)
            mapper(PackageGroup, self.package_groups, properties={
                # M:1 relations. No lazy loading is used.
                'packageRef':relation(Package, lazy=False),
                'groupRef':relation(Group, lazy=False)
                })

            mapper(Package, self.packages, properties = {
                # M:1 relation
                'organizationRef': relation(Organization, uselist=False, remote_side=[self.organizations.c.id], lazy=False),
                # M:N relation. No lazy loading is used.
                'groups': relation(PackageGroup, lazy=False),
                })

            mapper(TreeNode, self.tree_nodes, properties={
                # Add a reference to the parent group. It is important to set remote_side parameter since the relation is a many-to-one
                # relation. Moreover, since this is a self-referencing relation, join_depth parameter must be also set in order to avoid
                # querying the database for the parent of each group.
                'parentRef': relation(TreeNode, uselist=False, remote_side=[self.tree_nodes.c.id], lazy=False, join_depth=1)
            })
            
            mapper(Resource, self.resources, properties = {
                # M:1 relation
                'packageRef': relation(Package, uselist=False, remote_side=[self.packages.c.id], lazy=False),
                # M:1 relation
                'treeNodeRef': relation(TreeNode, uselist=False, remote_side=[self.tree_nodes.c.id], lazy=False),
                # 1:1 relation. No lazy loading is used. Allow cascading deletes
                'queryableRef': relation(Queryable, lazy=False, backref='resourceRef', cascade="all, delete, delete-orphan")
                })

            mapper(Field, self.fields)
            mapper(Queryable, self.queryables, properties = {
                # 1:M relation. No lazy loading is used. Allow cascading deletes
                'fields': relation(Field, lazy=False, backref='queryableRef', cascade="all, delete, delete-orphan")
                })
        except Exception as ex:
            log1.debug('Failure mapping tables to classes ')

    # TODO: when should _cleanup be called?
    def _cleanup(self):
        try:
            if self.session:
                self.session.close()
        except:
            pass

