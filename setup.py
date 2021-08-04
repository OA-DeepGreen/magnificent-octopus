from setuptools import setup, find_packages

setup(
    name='octopus',
    version='1.0.0-p3',
    packages=find_packages(),
    install_requires=[
        "werkzeug==1.0.1",
        "Flask==1.1.2",
        "Flask-Login==0.5.0",
        "requests==2.25.1",
        "esprit",
        "simplejson==3.17.2",
        "lxml==4.6.2",
        "Flask-WTF==0.14.3",
        "nose==1.3.7",
        "Flask-Mail==0.9.1",
        "python-dateutil==2.8.1",
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
