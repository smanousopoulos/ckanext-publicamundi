import datetime
import logging
import copy
import sets

from pylons import request, config

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan import model
from ckan.lib import helpers as h
from ckan.lib.base import c

from ckanext.publicamundi.themes.geodata.mapsdb import MapsRecords

import ckanext.publicamundi.themes.geodata.template_helpers as template_helpers

log1 = logging.getLogger(__name__)

_maps_db = None

def get_maps_db():
    return _maps_db

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
            'newest_datasets': template_helpers.most_recent_datasets,
            'list_menu_items': template_helpers.list_menu_items,
            'friendly_date': template_helpers.friendly_date,
            'friendly_name': template_helpers.friendly_name,
            'feedback_form': template_helpers.feedback_form,
            'redirect_wp': template_helpers.redirect_wp,
            'get_maps_url': template_helpers.get_maps_url,
            'preview_resource_or_ingested': template_helpers.preview_resource_or_ingested,
            'can_preview_resource_or_ingested': template_helpers.can_preview_resource_or_ingested,
            'get_translated_dataset_groups' : template_helpers.get_translated_dataset_groups,
            'get_term_translation': template_helpers.get_term_translation,
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

        # Initialize maps db
        global _maps_db
        _maps_db = MapsRecords()

        return

    # IRoutes

    def before_map(self, mapper):
        # Dataset pages controllers
        mapper.connect('dataset_apis', '/dataset/developers/{id}', controller= 'ckanext.publicamundi.themes.geodata.controllers.package:PackageController', action='package_apis')
        mapper.connect('dataset_contact_form', '/dataset/contact/{id}', controller= 'ckanext.publicamundi.themes.geodata.controllers.contact:Controller', action='contact_form')
        # Send email controller
        mapper.connect('send_email', '/publicamundi/util/send_email', controller= 'ckanext.publicamundi.themes.geodata.controllers.contact:Controller', action='send_email')
        # Generate captcha controller
        mapper.connect('generate_captcha', '/publicamundi/util/generate_captcha', controller= 'ckanext.publicamundi.themes.geodata.controllers.contact:Controller', action='generate_captcha')
        # MapDB controller
        mapper.connect('user_dashboard_maps', '/dashboard/maps', controller= 'ckanext.publicamundi.themes.geodata.controllers.maps:MapController', action='show_dashboard_maps')
        # MapDB client api calls
        mapper.connect('get-maps-configuration', '/publicamundi/util/get_maps_configuration', controller= 'ckanext.publicamundi.themes.geodata.controllers.maps:MapController', action='get_maps_configuration')
        mapper.connect('save-maps-configuration', '/publicamundi/util/save_maps_configuration', controller= 'ckanext.publicamundi.themes.geodata.controllers.maps:MapController', action='save_maps_configuration')
        mapper.connect('get-resource-queryable', '/publicamundi/util/get_resource_queryable', controller= 'ckanext.publicamundi.themes.geodata.controllers.maps:MapController', action='get_resource_queryable')

        return mapper

    # IPackageController 
    # has been copied from ckanext/multilingual MultilingualDataset
    def after_search(self, search_results, search_params):

        # Translte the unselected search facets.
        facets = search_results.get('search_facets')
        if not facets:
            return search_results

        desired_lang_code = request.environ['CKAN_LANG']
        fallback_lang_code = config.get('ckan.locale_default', 'en')

        # Look up translations for all of the facets in one db query.
        terms = sets.Set()
        for facet in facets.values():
            for item in facet['items']:
                terms.add(item['display_name'])
        translations = toolkit.get_action('term_translation_show')(
                {'model': model},
                {'terms': terms,
                    #'lang_codes': (desired_lang_code, fallback_lang_code)})
                    'lang_codes': (desired_lang_code)})

        # Replace facet display names with translated ones.
        for facet in facets.values():
            for item in facet['items']:
                matching_translations = [translation for
                        translation in translations
                        if translation['term'] == item['display_name']
                        and translation['lang_code'] == desired_lang_code]
                if not matching_translations:
                    matching_translations = [translation for
                            translation in translations
                            if translation['term'] == item['display_name']
                            and translation['lang_code'] == fallback_lang_code]
                if matching_translations:
                    assert len(matching_translations) == 1
                    item['display_name'] = (
                        matching_translations[0]['term_translation'])

        return search_results

