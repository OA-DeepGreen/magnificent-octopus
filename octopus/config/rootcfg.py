# absolute paths, or relative paths from root application directory (ie. above the magnificent-octopus directory),
# to the desired config files (in the order you want them loaded)
CONFIG_FILES = [
    # octopus.lib config files
    "octopus/config/cli.py",
    "octopus/config/dates.py",
    "octopus/config/http.py",
    "octopus/config/mail.py",
    "octopus/config/webapp.py",

    # octopus.module config files
    "octopus/modules/account/settings.py",
    "octopus/modules/clientjs/settings.py",
    "octopus/modules/es/settings.py",
    "octopus/modules/jper/settings.py",
    "octopus/modules/store/settings.py",
    "octopus/modules/swordv2/settings.py",

    # local service configuration
    "config/service.py",
    "local.cfg"
]

# absolute paths, or relative paths from root directory, to the template directories (in the order you want them looked at)
TEMPLATE_PATHS = [
    # local service templates
    "service/templates",

    # octopus standard bootstrap layout templates
    "octopus/templates",

    # octopus modules templates
    "octopus/modules/account/templates",
    "octopus/modules/clientjs/templates"
]

# absolute paths, or relative paths from the root directory, to the static file directories (in the order you want them looked at)
STATIC_PATHS = [
    # local service static directory
    "service/static",

    # octopus standard static directory - contains all vendor JS, plus the core Octopus JS
    "octopus/static",

    # octopus modules static directories
    "octopus/modules/account/static",
    "octopus/modules/clientjs/static",
    "octopus/modules/es/static"
]

# module import paths for the app initialisation modules that need to run at flask app creation
# (e.g. to do things like add login management support)
SETUP_MODULES = [
    "octopus.modules.account.setup_app",     # NOTE that you will also need to set ACCOUNT_ENABLE=True for this to run
    "service.setup_app"
]

# module import paths for the startup modules that need to run at application startup (in the order you want them run)
# (e.g. to do things like create/pre-populate the database)
INITIALISE_MODULES = [
    "octopus.modules.es.initialise",
    "service.initialise"
]
