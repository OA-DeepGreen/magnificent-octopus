from setuptools import setup, find_packages

setup(
    name='octopus',
    version='1.0.0-p3',
    packages=find_packages(),
    install_requires=[
        "werkzeug",
        "Flask",
        "Flask-Login",
        "requests",
        "esprit",
        "simplejson",
        "lxml",
        "Flask-WTF",
        "nose",
        "Flask-Mail",
        "python-dateutil",
    ],
    url='http://cottagelabs.com/',
    author='Cottage Labs',
    author_email='us@cottagelabs.com',
    description='Magnificent Octopus - Flask application helper library',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: Copyheart',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
