import logging

from pylons import config

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean
from sqlalchemy.types import Text, BigInteger
from sqlalchemy.schema import ForeignKey
from sqlalchemy.sql import delete
from sqlalchemy.orm import sessionmaker, mapper, relation

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

# RecordManager base class
# provides functions for basic db operations
# get, insert, update, upsert, delete records

class RecordManager(object):
    def __init__(self, session, record_type):
        self.session = session
        self.record_type = record_type

    def get_record_by_id(self, id):
        db_entry = self.session.query(self.record_type).get(id)
        return _as_dict(db_entry)

    def get_all_records(self):
        db_entries = self.session.query(self.record_type).all()
        records = []
        for db_entry in db_entries:
            records.append(_as_dict(db_entry))
        return records

    def insert_records(self, records):
        try:
            for rec in records:
                new_entry = self.record_type()
                db_entry = _update_object_with_dict(new_entry, rec)
                self.session.add(db_entry)
            self.session.commit()
        except Exception as ex:
            log1.error(ex)
            self.session.rollback()

        return records

    def update_records(self, records):
        try:
            for rec in records:
                db_entry = self.session.query(self.record_type).get(rec.get("id"))
                db_entry = _update_object_with_dict(db_entry, rec)

            self.session.commit()
        except Exception as ex:
            log1.error(ex)
            self.session.rollback()

        return records

    def upsert_records(self, records):
        try:
            for rec in records:
                db_entry = self.session.query(self.record_type).get(rec.get("id"))
                if db_entry:
                    db_entry = _update_object_with_dict(db_entry, rec)
                else:
                    new_entry = self.record_type()
                    db_entry = _update_object_with_dict(new_entry, rec)
                    self.session.add(db_entry)
            self.session.commit()
        except Exception as ex:
            log1.error(ex)
            self.session.rollback()

        return records

    def delete_records(self, records):
        try:
            for rec in records:
                db_entry = self.session.query(self.record_type).get(rec.get("id"))
                if db_entry:
                    self.session.delete(db_entry)
            self.session.commit()
        except Exception as ex:
            log1.error(ex)
            self.session.rollback()

    def delete_all_records(self):
        try:
            db_entries = self.session.query(self.record_type).all()
            for db_entry in db_entries:
                self.session.delete(db_entry)
            self.session.commit()
        except Exception as ex:
            log1.error(ex)
            self.session.rollback()

# Specific Table Managers inherit RecordManager
# and override specific functions

class ResourceManager(RecordManager):
    def __init__(self, session):
        super(ResourceManager, self).__init__(session, Resource)

    def get_all_records(self):
        res = self.session.query(self.record_type).all()
        return _list_objects_to_dict(res)

    def get_resources_with_packages_organizations(self):
        res = self.session.query(Resource, Package, Organization).filter(Resource.package == Package.id).filter(Package.organization == Organization.id).order_by(Organization.title_el.asc()).order_by(Package.title_el.asc()).all()
        return _pkg_org_tuples_to_dict(res)

class FieldManager(RecordManager):
    def __init__(self, session):
        super(FieldManager, self).__init__(session, Field)

class QueryableManager(RecordManager):
    def __init__(self, session):
        super(QueryableManager, self).__init__(session, Queryable)

    def get_record_by_id(self, resource_id):
        res = self.session.query(self.record_type).filter(self.record_type.resource == resource_id).all()
        queryable = _list_objects_to_dict(res)
        for q in queryable:
            q.update({'fields':\
                    sorted(_list_objects_to_dict(q.get('fields')), \
                    key=lambda k: k['id'])\
                    })
        if queryable:
            return queryable[0]
        else:
            return None

class TreeNodeManager(RecordManager):
    def __init__(self, session):
        super(TreeNodeManager, self).__init__(session, TreeNode)

    def get_all_records(self):
        db_entries = self.session.query(self.record_type).order_by(self.record_type.id.asc()).all()
        records = []
        for db_entry in db_entries:
            records.append(_as_dict(db_entry))
        return records

# MapsRecords class initializes mapclient database
class MapsRecords(object):
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
        self.session = session_factory()
        self.metadata = MetaData()

    def _initialize_model(self):
        if self.session:
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

# Helpers 

def _as_dict(row):
    return _filter_dict(row.__dict__)

def _update_object_with_dict(obj, dct):
    for key, value in dct.iteritems():
        setattr(obj, key, value)
    return obj

def _filter_dict(dict):
    d = {}
    for k, v in dict.iteritems():
        if not k == '_sa_instance_state':
            d[k] = v
    return d

def _list_objects_to_dict(obj_list):
    res_list = []
    for obj in obj_list:
        res_list.append(_as_dict(obj))
    return res_list

def _pkg_org_tuples_to_dict(obj_list):
    res_list = []
    for obj in obj_list:
        res = obj[0]
        pkg = obj[1]
        org = obj[2]

        out_dict = _as_dict(res)
        out_dict.update({"package_name": pkg.name,
                    "organization_name": org.name,
                    "package_title_el": pkg.title_el,
                    "package_title_en": pkg.title_en,
                    "organization_title_el": org.title_el,
                    "organization_title_en": org.title_en,
                    })
        res_list.append(out_dict)
    return res_list
