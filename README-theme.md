README Theme
============

 Includes the CKAN theme and a collection of tools used in geodata.gov.gr, such as the following:
 * `Email contact form in dataset page with captcha`
 * `5-star rating for datasets`
 * `Administration tools for the MapClient application (github.com/PublicaMundi/MapClient)`

Install
-------

Some external libraries are needed for captchas to work (image processing). We use the `wheezy.captcha` Python
which on its turn requires PIL or Pillow libraries to work with.

On a debian-based system, the following will be adequate:

    apt-get install libjpeg libjpeg-dev libfreetype6 libfreetype6-dev zlib1g-dev


Afterwards, install Pip requirements as usual:

    pip install -r theme-requirements.txt


Update CKAN configuration
-------------------------

Edit your CKAN .ini configuration file (e.g. your `development.ini`) and activate the following plugin to enable the geodata.gov.gr theme:

 * `publicamundi_geodata_theme`

Configure
---------

Some configuration options for the theme plugin:

    # MapClient Database url
    ckanext.publicamundi.themes.geodata.mapclient_db = postgres://tester:tester@localhost/mapclient
    
    # MapClient link for menu
    ckanext.publicamundi.themes.geodata.maps_url = maps
    
    # Feedback form link
    ckanext.publicamundi.themes.geodata.feedback_form_en = http://test.form
    # Feedback form link in greek
    ckanext.publicamundi.themes.geodata.feedback_form_el = http://test.form.gr
