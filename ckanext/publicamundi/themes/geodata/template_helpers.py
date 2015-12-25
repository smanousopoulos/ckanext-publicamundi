import copy
import sets
import datetime

from pylons import config

import ckan.plugins.toolkit as toolkit
from ckan.lib import helpers as h
from ckan import model
from ckan.lib.base import c

import ckanext.publicamundi.lib.template_helpers as ext_template_helpers
import ckan.lib.datapreview as datapreview

# Common helpers

def most_recent_datasets(limit=10):
    datasets = toolkit.get_action('package_search')(
        data_dict={'sort': 'metadata_modified desc', 'rows':limit})

    # Add terms for translation and call get_translation_terms
    #locale = helpers.lang()
    #translated = get_translated_dataset_groups(datasets.get('results'), locale)

    return datasets.get('results')

def list_menu_items (limit=21):
    groups = toolkit.get_action('group_list')(
        data_dict={'sort': 'name desc', 'all_fields':True})
    groups = groups[:limit]
    c.groups = groups

    return groups

def friendly_date(date_str):
    return h.render_datetime(date_str, '%d, %B, %Y')

def friendly_name(name):
    max_chars = 15
    if len(name) > max_chars:
        friendly_name = name.split(" ")[0]
        if len(friendly_name)+3 >= max_chars:
            friendly_name = friendly_name[:max_chars-4] + "..."
    else:
        friendly_name = name

    return friendly_name

def get_contact_point(pkg):
    
    # If there, INSPIRE metadata take precedence
    name = None
    email = None

    if pkg.get('dataset_type') == 'inspire':
        name = pkg.get('inspire.contact.0.organization', '').decode('unicode-escape')
        email = pkg.get('inspire.contact.0.email')
    
    # If not there, use maintainer or organization info
    
    if not name:
        name = pkg.get('maintainer') or pkg['organization']['title']
    
    if not email:
        email = pkg.get('maintainer_email') or config.get('email_to')
     
    return dict(name=name, email=email)

# Link helpers

def redirect_wp(page):
    locale = h.lang()
    if page:
        # check if page includes a subpage
        splitted = page.split('/')
        if not locale == 'el':
            splitted[0] = '{0}-{1}'.format(splitted[0], locale)
        return('/content/{0}/'.format('/'.join(splitted)))
    else:
        return('/content/')

def feedback_form():
    locale = h.lang()

    _feedback_form_en = config.get('ckanext.publicamundi.themes.geodata.feedback_form_en')
    _feedback_form_el = config.get('ckanext.publicamundi.themes.geodata.feedback_form_el')
    if _feedback_form_el and locale == 'el':
        return _feedback_form_el
    elif _feedback_form_en:
        return _feedback_form_en
    else:
        return ''

def get_maps_url(package_id=None, resource_id=None):
    locale = h.lang()

    _maps_url = config.get('ckanext.publicamundi.themes.geodata.maps_url')
    if _maps_url:
        if package_id and resource_id:
            return('{0}?package={1}&resource={2}&locale={3}'.format(_maps_url, package_id, resource_id, locale))
        else:
            return('{0}?locale={1}'.format(_maps_url, locale))
    else:
        return '/'

# Package rating
def package_rating_enabled():
    return config.get('ckanext.publicamundi.themes.geodata.package_rating', False)

# Resource preview helpers

# Returns the most suitable preview by checking whether ingested resources provide a better preview visualization
def preview_resource_or_ingested(pkg, res):
    snippet = h.resource_preview(res, pkg)
    data_dict = copy.copy(pkg)
    data_dict.update({'resource':res})

    if not _resource_preview(data_dict):
        raster_resources = ext_template_helpers.get_ingested_raster(pkg,res)
        vector_resources = ext_template_helpers.get_ingested_vector(pkg,res)

        for ing_res in raster_resources:
        #for ing_res in pkg.get('resources'):
            data_dict.update({'resource':ing_res})
            if _resource_preview(data_dict):
                snippet = h.resource_preview(ing_res, pkg)
                break
        for ing_res in vector_resources:
            data_dict.update({'resource':ing_res})
            if _resource_preview(data_dict):
                snippet = h.resource_preview(ing_res, pkg)
                break
    return snippet

def can_preview_resource_or_ingested(pkg, res):
    previewable = res.get('can_be_previewed')
    if not previewable:
        raster_resources = ext_template_helpers.get_ingested_raster(pkg,res)
        vector_resources = ext_template_helpers.get_ingested_vector(pkg,res)

        for ing_res in raster_resources:
        #for ing_res in pkg.get('resources'):
            if ing_res.get('can_be_previewed'):
                previewable = True
                break
        for ing_res in vector_resources:
            if ing_res.get('can_be_previewed'):
                previewable = True
                break
    return previewable

def _resource_preview(data_dict):
    return bool(datapreview.res_format(data_dict['resource'])
                    in datapreview.direct() + datapreview.loadable()
                    or datapreview.get_preview_plugin(
                        data_dict, return_first=True))

# Translation helpers

def get_translated_dataset_groups(datasets):
    desired_lang_code = h.lang()
    terms = sets.Set()
    for dataset in datasets:
        groups = dataset.get('groups')
        organization = dataset.get('organization')
        if groups:
            terms.add(groups[0].get('title'))
        if organization:
            terms.add(organization.get('title'))
    # Look up translations for all datasets in one db query.
    translations = toolkit.get_action('term_translation_show')(
        {'model': model},
        {'terms': terms,
            'lang_codes': (desired_lang_code)})

    for dataset in datasets:
        groups = dataset.get('groups')
        organization = dataset.get('organization')
        items = []
        if groups:
            items.append(groups[0])
        if organization:
            items.append(organization)
        for item in items:
            matching_translations = [translation for
                    translation in translations
                    if translation['term'] == item.get('title')
                    and translation['lang_code'] == desired_lang_code]
            if matching_translations:
                assert len(matching_translations) == 1
                item['title'] = (
                        matching_translations[0]['term_translation'])
    return datasets

# Helper function to ask for specific term to be translated
def get_term_translation(term):
    desired_lang_code = h.lang()
    translations = toolkit.get_action('term_translation_show')(
        {'model': model},
        {'terms': term,
            'lang_codes': (desired_lang_code)})
    matching_translations = [translation for
                    translation in translations
                    if translation['term'] == term
                    and translation['lang_code'] == desired_lang_code]
    if matching_translations:
        assert len(matching_translations) == 1
        term = (
                matching_translations[0]['term_translation'])
