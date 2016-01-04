import json
import os.path
from pylons import config

from ckan.lib.base import (
    c, BaseController, render, request, abort, redirect)
import ckan.plugins.toolkit as toolkit
import ckan.new_authz as new_authz

#from ckanext.publicamundi.themes.geodata.plugin import get_maps_db
from ckanext.publicamundi.themes.geodata import mapclient
from ckanext.publicamundi.themes.geodata.mapsdb import (
        ResourceManager, TreeNodeManager, QueryableManager, FieldManager )

_ = toolkit._
NotFound = toolkit.ObjectNotFound
MapNotFound = NotFound('Mapclient not enabled')
NotAuthorized = toolkit.NotAuthorized


class MapController(BaseController):
    def show_dashboard_maps(self):
        c.is_sysadmin = new_authz.is_sysadmin(c.user)

        if not c.is_sysadmin:
            return render('user/dashboard_maps.html')

        session = mapclient.session
        if session:
            c.enabled = True
            c.resources = ResourceManager(session).get_resources_with_packages_organizations()
        else:
            c.enabled = False

        return render('user/dashboard_maps.html')

    def get_maps_configuration(self):
        ''' Helper API call that returns saved map configuration from db'''

        def new_tree_node(tree_pos, node):
            if node.get("parentRef"):
                del node["parentRef"]
            node["node"] = True
            return {
                "children": [],
                "parent": tree_pos.get("key"),
                "key": node.get("id"),
                "title": node.get("caption_en"),
                "expanded" :True,
                "folder": True,
                "data": node
                }

        def new_tree_resource(tree_pos, res):
            if res.get("packageRef"):
                del res["packageRef"]
            if res.get("queryableRef"):
                del res["queryableRef"]
            if res.get("treeNodeRef"):
                del res["treeNodeRef"]

            res["node"] = False
            return {
                "children": [],
                "parent": tree_pos.get("key"),
                "key": res.get("id"),
                "title": res.get("tree_node_caption_en"),
                "folder": False,
                "data": res
                }

        def find_tree_node_by_key(tree, key):
            if tree.get("key") == key:
                return tree
            elif not tree.get("children"):
                return None
            else:
                for child in tree.get("children"):
                    if find_tree_node_by_key(child, key):
                        return find_tree_node_by_key(child, key)

        def get_index(item):
            if item.get("data"):
                if item.get("data").get("index"):
                    return item.get("data").get("index")
                elif item.get("data").get("tree_node_index"):
                    return item.get("data").get("tree_node_index")

        source = {
                "children": [],
                "expanded": True,
                "key": "root",
                "title": "root"
                }

        session = mapclient.session
        if not session:
            raise MapNotFound

        tree_nodes = TreeNodeManager(session).get_all_records()
        for node in tree_nodes:
            if node.get("parent") == None:
                source.get("children").append(new_tree_node(source, node))
                #source.update({"children": sorted(source.get("children"), key=get_index)})
            else:
                xnode = find_tree_node_by_key(source, node.get("parent"))
                if xnode:
                    xnode.get("children").append(new_tree_node(xnode, node))
                    #xnode.update({"children": sorted(xnode.get("children"), key=get_index)})
                else:
                    #TODO: fix raise no text
                    raise 'oops something went wrong, tree node not found for visible node'
        
        #resources = self.mapsdb.get_resources_with_packages_organizations()
        resources = ResourceManager(session).get_resources_with_packages_organizations()
        for res in resources:
            if res.get("visible") == True:
                xnode = find_tree_node_by_key(source, res.get("tree_node_id"))
                if xnode:
                    xnode.get("children").append(new_tree_resource(xnode, res))
                    # sort to display correct index order
                    xnode.update({"children": sorted(xnode.get("children"), key=get_index)})

                else:
                    #TODO: fix raise no text
                    raise 'oops something went wrong, tree node not found for visible layer'

        if tree_nodes:
            next_tree_node_id = tree_nodes[-1].get("id")+1
        else:
            next_tree_node_id = 0

        return json.dumps({'source': source, 'tree_node_id': next_tree_node_id})

    def save_maps_configuration(self):
        ''' Helper API POST call that saves the map configuration
            to DB tables

            parameters: resources,
                        tree_nodes,
                        resources_fields,
                        resources_queryable
        '''
        sysadmin = new_authz.is_sysadmin(c.user)
        if not sysadmin:
            raise NotAuthorized('Not authorized for this action')

        session = mapclient.session
        if not session:
            raise MapNotFound

        if not request.params:
            raise NotFound('No parameters provided')

        # read request POST parameters
        resources = request.params.get("resources")
        if not resources:
            resources = '{}'
        resources = json.loads(resources)

        tree_nodes = request.params.get("tree_nodes")
        if not tree_nodes:
            tree_nodes = '{}'
        tree_nodes = json.loads(tree_nodes)

        resources_fields = request.params.get("resources_fields")
        if not resources_fields:
            resources_fields = '{}'
        resources_fields = json.loads(resources_fields)

        resources_queryable = request.params.get("resources_queryable")
        if not resources_queryable:
            resources_queryable = '{}'
        resources_queryable = json.loads(resources_queryable)

        # transform dicts to lists
        res_list = []
        for resk, resv in resources.iteritems():
            resv.update({"id":resk})
            if resv.get("node"):
                del resv["node"]
            res_list.append(resv)

        node_list = []
        del_node_list = []
        for item in sorted(tree_nodes.items(), key=lambda x: x[1]):
            nodek = item[0]
            nodev = item[1]
            nodev.update({"id":nodek})
            if nodev.get("node"):
                del nodev["node"]
            if nodev.get("visible") == False:
                del_node_list.append({"id":nodek})
            else:
                node_list.append(nodev)

        res_fields_list = []
        for resfk, resfv in resources_fields.iteritems():
            res_fields_list += resfv

        res_quer_list = []
        for resqk, resqv in resources_queryable.iteritems():
            resqv.update({"id":resqk})
            res_quer_list.append(resqv)

        # perform db deletes/updates/inserts
        TreeNodeManager(session).delete_records(del_node_list)
        TreeNodeManager(session).upsert_records(node_list)
        ResourceManager(session).update_records(res_list)
        FieldManager(session).update_records(res_fields_list)
        QueryableManager(session).upsert_records(res_quer_list)

        return

    def get_resource_queryable(self):
        ''' Helper API call that returns queryable resource and its fields
            parameters: id
        '''
        session = mapclient.session
        if not session:
            raise MapNotFound

        resource_id = request.params.get("id")
        if not resource_id:
            return

        queryable = QueryableManager(session).get_record_by_id(resource_id)
        if not queryable:
            return

        fields = queryable.get('fields')
        return json.dumps({'fields':fields, 'queryable':queryable})
