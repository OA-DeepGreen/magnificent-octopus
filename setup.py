from setuptools import setup, find_packages

setup(
    name='octopus',
    version='1.1',
    packages=find_packages(),
    install_requires=[
        "werkzeug~=3.0",
        "Flask~=3.0",
        "Flask-Login~=0.6",
        "requests~=2.32",
        "esprit",
        "simplejson~=3.19",
        "lxml~=5.3",
        "Flask-WTF~=1.2",
        "nose~=1.3",
        "Flask-Mail~=0.10",
        "python-dateutil~=2.9",
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
