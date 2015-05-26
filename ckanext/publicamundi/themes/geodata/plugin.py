import datetime

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib import helpers
from ckan.lib.base import c
from ckan.lib.helpers import render_datetime, resource_preview
import ckanext.publicamundi.lib.template_helpers as ext_template_helpers

def most_recent_datasets(limit=10):
    datasets = toolkit.get_action('package_search')(
        data_dict={'sort': 'metadata_modified desc', 'rows':8})
    return datasets

def list_menu_items (limit=21):
    groups = toolkit.get_action('group_list')(
        data_dict={'sort': 'name desc', 'all_fields':True})
    groups = groups[:limit]
    c.groups = groups

    return groups

def friendly_date(date_str):
    return render_datetime(date_str, '%d, %B, %Y')


_feedback_form = None
_maps_url = None
_wp_url = None
_non_previewable_formats = ['geotiff', 'gml', 'shapefile', 'shp' ]
_previewable_formats = ['wms', 'wfs']

def feedback_form():
    return _feedback_form

def get_non_previewable_formats():
    return _non_previewable_formats

def get_previewable_formats():
    return _previewable_formats

def get_maps_suffix():
    if _maps_url:
        return _maps_url
    else:
        return '/'

def get_wp_suffix():
    locale = helpers.lang()
    if _wp_url:
        return(_wp_url+'?lang={0}'.format(locale))
    else:
        return '/'

# Returns the most suitable preview by checking whether ingested resources provide a better preview visualization
def preview_resource_or_ingested(res, pkg):
    snippet = resource_preview(res, pkg)
    non_previewable = get_non_previewable_formats()
    previewable = get_previewable_formats()

    if res.get('format') in non_previewable:
        raster_resources = ext_template_helpers.get_ingested_raster_from_resource(pkg,res)
        vector_resources = ext_template_helpers.get_ingested_vector_from_resource(pkg,res)

        for ing_res in raster_resources:
            if ing_res.get('format') in previewable:
                snippet = resource_preview(ing_res, pkg)
        for ing_res in vector_resources:
            if ing_res.get('format') in previewable:
                snippet = resource_preview(ing_res, pkg)

        #for ing_res in pkg.get('resources'):
        #    if (ing_res.get('vectorstorer_resource') or ing_res.get('rasterstorer_resource')) and ing_res.get('parent_resource_id') == res.get('id') and ing_res.get('format') in previewable:
        #        snippet = resource_preview(ing_res, pkg)
    return snippet

class GeodataThemePlugin(plugins.SingletonPlugin):
    '''Theme plugin for geodata.gov.gr.
    '''

    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IPackageController, inherit=True)
    
    # ITemplateHelpers
    

    def get_helpers(self):
        return {
            'newest_datasets': most_recent_datasets,
            'list_menu_items': list_menu_items,
            'friendly_date': friendly_date,
            'feedback_form': feedback_form,
            'preview_resource_or_ingested': preview_resource_or_ingested,
            'get_wp_suffix': get_wp_suffix,
            'get_maps_suffix': get_maps_suffix,
        }
    
    # IConfigurer
    
    def update_config(self, config):

        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')
        toolkit.add_resource('public', 'ckanext-publicamundi-geodata-theme')

    # IConfigurable

    def configure(self, config):
        '''Pass configuration to plugins and extensions'''

        global _feedback_form
        global _wp_url
        global _maps_url

        _feedback_form = config.get('ckanext.publicamundi.themes.geodata.feedback_form')
        _maps_url = config.get('ckanext.publicamundi.themes.geodata.maps_suffix')
        _wp_url = config.get('ckanext.publicamundi.themes.geodata.wp_suffix')

        return

    # IRoutes

    def before_map(self, mapper):
        mapper.connect('developers', '/developers', controller= 'ckanext.publicamundi.themes.geodata.controllers.static:Controller', action='developers')
        #mapper.connect('maps', '/maps', controller= 'ckanext.publicamundi.themes.geodata.controllers.static:Controller', action='redirect_maps' )
        #mapper.redirect('maps', 'http://http://83.212.118.10:5000/maps')
        #mapper.connect('maps', '/maps')
        #mapper.connect('news', '/news', controller= 'ckanext.publicamundi.themes.geodata.controllers.static:Controller', action='redirect_news' )

        return mapper

    # IPackageController
    def before_view(self, pkg_dict):
        list_menu_items()
        return pkg_dict

