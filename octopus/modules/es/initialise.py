import esprit
from octopus.lib import plugin
from octopus.core import app

def get_mappings(app):
    """Get the full set of mappings required for the app"""

    # LEGACY DEFAULT MAPPINGS
    mappings = app.config.get("ELASTIC_SEARCH_DEFAULT_MAPPING", {})

    # TYPE SPECIFIC MAPPINGS
    # get the list of classes which carry the type-specific mappings to be loaded
    mapping_daos = app.config.get("ELASTIC_SEARCH_MAPPINGS", [])

    # load each class and execute the "mappings" function to get the mappings that need to be imported
    for cname in mapping_daos:
        klazz = plugin.load_class_raw(cname)
        mappings[klazz.__type__] = klazz().mappings()

    return mappings


def mutate_mapping(conn, type, mapping):
    """ When we are using an index-per-type connection change the mappings to be keyed 'doc' rather than the type """
    if conn.index_per_type:
        try:
            mapping[esprit.raw.INDEX_PER_TYPE_SUBSTITUTE] = mapping.pop(type)
        except KeyError:
            # Allow this mapping through unaltered if it isn't keyed by type
            pass
    return


def put_mappings(conn, mappings):
    # get the ES version that we're working with
    es_version = app.config.get("ELASTIC_SEARCH_VERSION", "1.7.5")

    # for each mapping (a class may supply multiple), create a mapping, or mapping and index
    for key, mapping in iter(mappings.items()):
        mutate_mapping(conn, key, mapping)
        ix = conn.index
        if not esprit.raw.type_exists(conn, key, es_version=es_version):
            r = esprit.raw.put_mapping(conn, key, mapping[esprit.raw.INDEX_PER_TYPE_SUBSTITUTE], make_index=True, es_version=es_version)
            print("Creating ES Type + Mapping in index {0} for {1}; status: {2}".format(ix, key, r.status_code))
        else:
            print("ES Type + Mapping already exists in index {0} for {1}".format(ix, key))


def put_example(type, example):
    # make a connection to the index
    conn = esprit.raw.Connection(app.config['ELASTIC_SEARCH_HOST'], app.config['ELASTIC_SEARCH_INDEX'], index_per_type=app.config['ELASTIC_INDEX_PER_TYPE'])

    # get the ES version that we're working with
    es_version = app.config.get("ELASTIC_SEARCH_VERSION", "0.90.13")

    if not esprit.raw.type_exists(conn, type, es_version=es_version):
        example.save()
        example.delete()
        print("Initialising ES Type+Mapping from document for", type)
    else:
        print("Not Initialising from document - ES Type+Mapping already exists for", type)


def initialise():
    if not app.config.get("INITIALISE_INDEX", False):
        app.logger.warn('INITIALISE_INDEX config var is not True, initialise index command cannot run')
        return

    # get the app mappings
    conn = esprit.raw.Connection(app.config['ELASTIC_SEARCH_HOST'], app.config['ELASTIC_SEARCH_INDEX'], index_per_type=app.config['ELASTIC_INDEX_PER_TYPE'])
    mappings = get_mappings(app)
    # Send the mappings to ES
    put_mappings(conn, mappings)

    example_daos = app.config.get("ELASTIC_SEARCH_EXAMPLE_DOCS", [])
    for cname in example_daos:
        klazz = plugin.load_class_raw(cname)
        example = klazz.example()
        type = klazz.get_write_type()
        put_example(type, example)

    self_inits = app.config.get("ELASTIC_SEARCH_SELF_INIT", [])
    for cname in self_inits:
        klazz = plugin.load_class_raw(cname)
        klazz.self_init()
