try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

config = {
	'name': 'Weatherer',
	'version': '0.1',
	'url': 'https://github.com/parnellj/weatherer',
	'download_url': 'https://github.com/parnellj/weatherer',
	'author': 'Justin Parnell',
	'author_email': 'parnell.justin@gmail.com',
	'maintainer': 'Justin Parnell',
	'maintainer_email': 'parnell.justin@gmail.com',
	'classifiers': [],
	'license': 'GNU GPL v3.0',
	'description': 'Accesses, downloads, and creatively visualizes weather pattern data from NOAA.',
	'long_description': 'Accesses, downloads, and creatively visualizes weather pattern data from NOAA.',
	'keywords': '',
	'install_requires': ['nose'],
	'packages': ['weatherer'],
	'scripts': []
}
	
setup(**config)
