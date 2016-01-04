import ckanext.publicamundi.themes.geodata.mapclient.model as model
from ckanext.publicamundi.themes.geodata.mapclient import mapclient

# RecordManager base class
# provides functions for basic db operations
# get, insert, update, upsert, delete records

class RecordManager(object):
    def __init__(self, record_type=None):
        self.record_type = record_type

    def get_record_by_id(self, id):
        db_entry = mapclient.Session.query(self.record_type).get(id)
        return _as_dict(db_entry)

    def get_all_records(self):
        db_entries = mapclient.Session.query(self.record_type).all()
        records = []
        for db_entry in db_entries:
            records.append(_as_dict(db_entry))
        return records

    def insert_records(self, records):
        try:
            for rec in records:
                new_entry = self.record_type()
                db_entry = _update_object_with_dict(new_entry, rec)
                mapclient.Session.add(db_entry)
            mapclient.Session.commit()
        except Exception as ex:
            log1.error(ex)
            mapclient.Session.rollback()

        return records

    def update_records(self, records):
        try:
            for rec in records:
                db_entry = mapclient.Session.query(self.record_type).get(rec.get("id"))
                db_entry = _update_object_with_dict(db_entry, rec)

            mapclient.Session.commit()
        except Exception as ex:
            log1.error(ex)
            mapclient.Session.rollback()

        return records

    def upsert_records(self, records):
        try:
            for rec in records:
                db_entry = mapclient.Session.query(self.record_type).get(rec.get("id"))
                if db_entry:
                    db_entry = _update_object_with_dict(db_entry, rec)
                else:
                    new_entry = self.record_type()
                    db_entry = _update_object_with_dict(new_entry, rec)
                    mapclient.Session.add(db_entry)
            mapclient.Session.commit()
        except Exception as ex:
            log1.error(ex)
            mapclient.Session.rollback()

        return records

    def delete_records(self, records):
        try:
            for rec in records:
                db_entry = mapclient.Session.query(self.record_type).get(rec.get("id"))
                if db_entry:
                    mapclient.Session.delete(db_entry)
            mapclient.Session.commit()
        except Exception as ex:
            log1.error(ex)
            mapclient.Session.rollback()

    def delete_all_records(self):
        try:
            db_entries = mapclient.Session.query(self.record_type).all()
            for db_entry in db_entries:
                mapclient.Session.delete(db_entry)
            mapclient.Session.commit()
        except Exception as ex:
            log1.error(ex)
            mapclient.Session.rollback()

# Specific Table Managers inherit RecordManager
# and override specific functions

class ResourceManager(RecordManager):
    def __init__(self):
        super(ResourceManager, self).__init__(model.Resource)

    def get_all_records(self):
        res = mapclient.Session.query(model.Resource).all()
        return _list_objects_to_dict(res)

    def get_resources_with_packages_organizations(self):
        res = mapclient.Session.query(model.Resource, model.Package, model.Organization).filter(model.Resource.package == model.Package.id).filter(model.Package.organization == model.Organization.id).order_by(model.Organization.title_el.asc()).order_by(model.Package.title_el.asc()).all()
        return _pkg_org_tuples_to_dict(res)

class FieldManager(RecordManager):
    def __init__(self):
        super(FieldManager, self).__init__(model.Field)

class QueryableManager(RecordManager):
    def __init__(self):
        super(QueryableManager, self).__init__(model.Queryable)

    def get_record_by_id(self, resource_id):
        res = mapclient.Session.query(self.record_type).filter(self.record_type.resource == resource_id).all()
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
    def __init__(self):
        super(TreeNodeManager, self).__init__(model.TreeNode)

    def get_all_records(self):
        db_entries = mapclient.Session.query(self.record_type).order_by(model.TreeNode.id.asc()).all()
        records = []
        for db_entry in db_entries:
            records.append(_as_dict(db_entry))
        return records

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
