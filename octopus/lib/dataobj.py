from octopus.lib import dates
from copy import deepcopy
import locale, json, urllib.parse

#########################################################
## Data coerce functions

def to_unicode():
    def to_utf8_unicode(val):
        if isinstance(val, str):
            return val
        elif isinstance(val, str):
            try:
                return val.decode("utf8", "strict")
            except UnicodeDecodeError:
                raise ValueError("Could not decode string")
        else:
            return str(val)

    return to_utf8_unicode

def to_int():
    def intify(val):
        # strip any characters that are outside the ascii range - they won't make up the int anyway
        # and this will get rid of things like strange currency marks
        if isinstance(val, str):
            val = val.encode("ascii", errors="ignore")

        # try the straight cast
        try:
            return int(val)
        except ValueError:
            pass

        # could have commas in it, so try stripping them
        try:
            return int(val.replace(",", ""))
        except ValueError:
            pass

        # try the locale-specific approach
        try:
            return locale.atoi(val)
        except ValueError:
            pass

        raise ValueError("Could not convert string to int: {x}".format(x=val))

    return intify

def to_float():
    def floatify(val):
        # strip any characters that are outside the ascii range - they won't make up the float anyway
        # and this will get rid of things like strange currency marks
        if isinstance(val, str):
            val = val.encode("ascii", errors="ignore")

        # try the straight cast
        try:
            return float(val)
        except ValueError:
            pass

        # could have commas in it, so try stripping them
        try:
            return float(val.replace(",", ""))
        except ValueError:
            pass

        # try the locale-specific approach
        try:
            return locale.atof(val)
        except ValueError:
            pass

        raise ValueError("Could not convert string to float: {x}".format(x=val))

    return floatify

def date_str(in_format=None, out_format=None):
    def datify(val):
        return dates.reformat(val, in_format=in_format, out_format=out_format)

    return datify

def to_datestamp(in_format=None):
    def stampify(val):
        return dates.parse(val, format=in_format)

    return stampify

def to_isolang(output_format=None):
    """
    :param output_format: format from input source to putput.  Must be one of:
        * alpha3
        * alt3
        * alpha2
        * name
        * fr
    Can be a list in order of preference, too
    :return:
    """
    # delayed import, since we may not always want to load the whole dataset for a dataobj
    from octopus.lib import isolang as dataset

    # sort out the output format list
    if output_format is None:
        output_format = ["alpha3"]
    if not isinstance(output_format, list):
        output_format = [output_format]

    def isolang(val):
        if val is None:
            return None
        l = dataset.find(val)
        for f in output_format:
            v = l.get(f)
            if v is None or v == "":
                continue
            return v

    return isolang

def to_url(val):
    if val is None:
        return None

    # parse with urlparse
    url = urllib.parse.urlparse(val)

    # now check the url has the minimum properties that we require
    if url.scheme and url.scheme.startswith("http"):
        uc = to_unicode()
        return uc(val)
    else:
        raise ValueError("Could not convert string {val} to viable URL".format(val=val))

def to_bool(val):
    """Conservative boolean cast - don't cast lists and objects to True, just existing booleans and strings."""
    if val is None:
        return None
    if val is True or val is False:
        return val

    if isinstance(val, str):
        if val.lower() == 'true':
            return True
        elif val.lower() == 'false':
            return False
        raise ValueError("Could not convert string {val} to boolean. Expecting string to either say 'true' or 'false' (not case-sensitive).".format(val=val))

    raise ValueError("Could not convert {val} to boolean. Expect either boolean or string.".format(val=val))



############################################################

############################################################
## The core data object which manages all the interactions
## with the underlying data member variable

class DataSchemaException(Exception):
    pass

class DataObj(object):
    """
    Class which provides services to other classes which store their internal data
    as a python data structure in the self.data field.
    """

    SCHEMA = None

    DEFAULT_COERCE = {
        "unicode": to_unicode(),
        "utcdatetime": date_str(),
        "integer": to_int(),
        "float": to_float(),
        "isolang": to_isolang(),
        "url": to_url,
        "bool": to_bool,
        "isolang_2letter": to_isolang(output_format="alpha2"),
        "bigenddate" : date_str(out_format="%Y-%m-%d")
    }

    def __init__(self, raw=None, struct=None, construct_raw=True, expose_data=False, properties=None, coerce_map=None, construct_silent_prune=False):
        # make a shortcut to the object.__getattribute__ function
        og = object.__getattribute__

        # if no subclass has set the coerce, then set it from default
        try:
            og(self, "_coerce_map")
        except:
            self._coerce_map = coerce_map if coerce_map is not None else deepcopy(self.DEFAULT_COERCE)

        # if no subclass has set the struct, initialise it
        try:
            og(self, "_struct")
        except:
            self._struct = struct

        # assign the data if not already assigned by subclass
        # NOTE: data is not _data deliberately
        try:
            og(self, "data")
        except:
            self.data = {} if raw is None else raw

        # properties to allow automatic object API construction
        # of the form
        #
        # {"<public property name>" : ("<path.to.property>", "<data object wrapper>")
        # e.g
        # {"identifier" : ("bibjson.identifier", DataObj))}
        try:
            og(self, "_properties")
        except:
            self._properties = properties if properties is not None else {}

        # if no subclass has set expose_data, set it
        try:
            og(self, "_expose_data")
        except:
            self._expose_data = expose_data

        # restructure the object based on the struct if requried
        if self._struct is not None and raw is not None and construct_raw:
            self.data = construct(self.data, self._struct, self._coerce_map, silent_prune=construct_silent_prune)

        # run against the old validation routine
        # (now deprecated)
        self.validate()

        # run the object's native validation routine
        self.custom_validate()

        # SE: fix for multiple inheritance bug in Octopus
        super(DataObj, self).__init__()

    def __getattr__(self, name):
        if hasattr(self.__class__, name):
            return object.__getattribute__(self, name)

        props, data_attrs = self._list_dynamic_properties()

        # if the name is not in the dynamic properties, raise an attribute error
        if name not in props and name not in data_attrs:
            raise AttributeError('{name} is not set'.format(name=name))

        # otherwise, extract the path from the properties list or the internal data
        if name in props:
            path, wrapper = self._properties.get(name)
        else:
            path = name
            wrapper = DataObj

        # request the internal property directly (which will in-turn raise the AttributeError if necessary)
        try:
            return self._get_internal_property(path, wrapper)
        except AttributeError:
            # re-wrap the attribute error with the name, rather than the path
            raise AttributeError('{name} is not set'.format(name=name))

    def __setattr__(self, key, value):
        # first set the attribute on any explicitly defined property
        try:
            if hasattr(self.__class__, key):
                # att = object.__getattribute__(self, key)
                return object.__setattr__(self, key, value)
        except AttributeError:
            pass

        # this could be an internal attribute from the constructor, so we need to make
        # a special case
        if key in ["_coerce_map", "_struct", "data", "_properties", "_expose_data"]:
            return object.__setattr__(self, key, value)

        props, data_attrs = self._list_dynamic_properties()

        # extract the path from the properties list or the internal data
        path = None
        wrapper = None
        if key in props:
            path, wrapper = self._properties.get(key)
        elif key in data_attrs:
            path = key
            wrapper = DataObj

        # try to set the property on othe internal object
        if path is not None:
            wasset = self._set_internal_property(path, value, wrapper)
            if wasset:
                return

        # fall back to the default approach of allowing any attribute to be set on the object
        return object.__setattr__(self, key, value)

    def validate(self):
        if self.SCHEMA is not None:
            validate(self.data, self.SCHEMA)
        return True

    def custom_validate(self):
        pass

    def populate(self, fields_and_values):
        for k, v in fields_and_values.items():
            setattr(self, k, v)

    def clone(self):
        return self.__class__(deepcopy(self.data))

    def json(self):
        return json.dumps(self.data)

    def get_struct(self):
        return self._struct

    def _get_internal_property(self, path, wrapper=None):
        # pull the object from the structure, to find out what kind of retrieve it needs
        # (if there is a struct)
        type, substruct, instructions = None, None, None
        if self._struct:
            type, substruct, instructions = construct_lookup(path, self._struct)

        if type is None:
            # if there is no struct, or no object mapping was found, try to pull the path
            # as a single node (may be a field, list or dict, we'll find out in a mo)
            val = self._get_single(path)

            # if this is a dict or a list and a wrapper is supplied, wrap it
            if wrapper is not None:
                if isinstance(val, dict):
                    return wrapper(val, expose_data=self._expose_data)
                elif isinstance(val, list):
                    return [wrapper(v, expose_data=self._expose_data) for v in val]

            # otherwise, return the raw value if it is not None, or raise an AttributeError
            if val is None:
                raise AttributeError('{name} is not set'.format(name=path))

            return val

        # if the struct contains a reference to the path, always return something, even if it is None - don't raise an AttributeError
        kwargs = construct_kwargs(type, "get", instructions)
        coerce_fn = self._coerce_map.get(instructions.get("coerce"))
        if coerce_fn is not None:
            kwargs["coerce"] = coerce_fn

        if type == "field":
            return self._get_single(path, **kwargs)
        elif type == "object":
            d = self._get_single(path, **kwargs)
            if wrapper:
                return wrapper(d, substruct, construct_raw=False, expose_data=self._expose_data)    # FIXME: this means all substructures are forced to use this classes expose_data policy, whatever it is
            else:
                return d
        elif type == "list":
            if instructions.get("contains") == "field":
                return self._get_list(path, **kwargs)
            elif instructions.get("contains") == "object":
                l = self._get_list(path, **kwargs)
                if wrapper:
                    return [wrapper(o, substruct, construct_raw=False, expose_data=self._expose_data) for o in l]    # FIXME: this means all substructures are forced to use this classes expose_data policy, whatever it is
                else:
                    return l

        # if for whatever reason we get here, raise the AttributeError
        raise AttributeError('{name} is not set'.format(name=path))

    def _set_internal_property(self, path, value, wrapper=None):

        def _wrap_validate(val, wrap, substruct):
            if wrap is None:
                if isinstance(val, DataObj):
                    return val.data
                else:
                    return val

            else:
                if isinstance(val, DataObj):
                    if isinstance(val, wrap):
                        return val.data
                    else:
                        raise AttributeError("Attempt to set {x} failed; is not of an allowed type.".format(x=path))
                else:
                    try:
                        d = wrap(val, substruct)
                        return d.data
                    except DataStructureException as e:
                        raise AttributeError(str(e))

        # pull the object from the structure, to find out what kind of retrieve it needs
        # (if there is a struct)
        type, substruct, instructions = None, None, None
        if self._struct:
            type, substruct, instructions = construct_lookup(path, self._struct)

        # if no type is found, then this means that either the struct was undefined, or the
        # path did not point to a valid point in the struct.  In the case that the struct was
        # defined, this means the property is trying to set something outside the struct, which
        # isn't allowed.  So, only set types which are None against objects which don't define
        # the struct.
        if type is None:
            if self._struct is None:
                if isinstance(value, list):
                    value = [_wrap_validate(v, wrapper, None) for v in value]
                    self._set_list(path, value)
                else:
                    value = _wrap_validate(value, wrapper, None)
                    self._set_single(path, value)

                return True
            else:
                return False

        kwargs = construct_kwargs(type, "set", instructions)
        coerce_fn = self._coerce_map.get(instructions.get("coerce"))
        if coerce_fn is not None:
            kwargs["coerce"] = coerce_fn

        if type == "field":
            self._set_single(path, value, **kwargs)
            return True
        elif type == "object":
            v = _wrap_validate(value, wrapper, substruct)
            self._set_single(path, v, **kwargs)
            return True
        elif type == "list":
            if instructions.get("contains") == "field":
                self._set_list(path, value, **kwargs)
                return True
            elif instructions.get("contains") == "object":
                if not isinstance(value, list):
                    value = [value]
                vals = [_wrap_validate(v, wrapper, substruct) for v in value]
                self._set_list(path, vals, **kwargs)
                return True

        return False

    def _list_dynamic_properties(self):
        # list the dynamic properties the object could have
        props = []
        try:
            # props = og(self, 'properties').keys()
            props = list(self._properties.keys())
        except AttributeError:
            pass

        data_attrs = []
        try:
            if self._expose_data:
                if self._struct:
                    data_attrs = construct_data_keys(self._struct)
                else:
                    data_attrs = list(self.data.keys())
        except AttributeError:
            pass

        return props, data_attrs

    def _add_struct(self, struct):
        # if the struct is not yet set, set it
        try:
            object.__getattribute__(self, "_struct")
            self._struct = construct_merge(self._struct, struct)
        except:
            self._struct = struct

    def _get_path(self, path, default):
        parts = path.split(".")
        context = self.data

        for i in range(len(parts)):
            p = parts[i]
            d = {} if i < len(parts) - 1 else default
            context = context.get(p, d)
        return context

    def _set_path(self, path, val):
        parts = path.split(".")
        context = self.data

        for i in range(len(parts)):
            p = parts[i]

            if p not in context and i < len(parts) - 1:
                context[p] = {}
                context = context[p]
            elif p in context and i < len(parts) - 1:
                context = context[p]
            else:
                context[p] = val

    def _delete_from_list(self, path, val=None, matchsub=None, prune=True):
        l = self._get_list(path)

        removes = []
        i = 0
        for entry in l:
            if val is not None:
                if entry == val:
                    removes.append(i)
            elif matchsub is not None:
                matches = 0
                for k, v in matchsub.items():
                    if entry.get(k) == v:
                        matches += 1
                if matches == len(list(matchsub.keys())):
                    removes.append(i)
            i += 1

        removes.sort(reverse=True)
        for r in removes:
            del l[r]

        if len(l) == 0 and prune:
            self._delete(path, prune)

    def _delete(self, path, prune=True):
        parts = path.split(".")
        context = self.data

        stack = []
        for i in range(len(parts)):
            p = parts[i]
            if p in context:
                if i < len(parts) - 1:
                    stack.append(context[p])
                    context = context[p]
                else:
                    del context[p]
                    if prune and len(stack) > 0:
                        stack.pop() # the last element was just deleted
                        self._prune_stack(stack)

    def _prune_stack(self, stack):
        while len(stack) > 0:
            context = stack.pop()
            todelete = []
            for k, v in context.items():
                if isinstance(v, dict) and len(list(v.keys())) == 0:
                    todelete.append(k)
            for d in todelete:
                del context[d]

    def _coerce(self, val, cast, accept_failure=False):
        if cast is None:
            return val
        try:
            return cast(val)
        except (ValueError, TypeError):
            if accept_failure:
                return val
            raise DataSchemaException("Cast with {x} failed on {y}".format(x=cast, y=val))

    def _get_single(self, path, coerce=None, default=None, allow_coerce_failure=True):
        # get the value at the point in the object
        val = self._get_path(path, default)

        if coerce is not None and val is not None:
            # if you want to coerce and there is something to coerce do it
            return self._coerce(val, coerce, accept_failure=allow_coerce_failure)
        else:
            # otherwise return the value
            return val

    def _get_list(self, path, coerce=None, by_reference=True, allow_coerce_failure=True):
        # get the value at the point in the object
        val = self._get_path(path, None)

        # if there is no value and we want to do by reference, then create it, bind it and return it
        if val is None and by_reference:
            mylist = []
            self._set_single(path, mylist)
            return mylist

        # otherwise, default is an empty list
        elif val is None and not by_reference:
            return []

        # check that the val is actually a list
        if not isinstance(val, list):
            raise DataSchemaException("Expecting a list at {x} but found {y}".format(x=path, y=val))

        # if there is a value, do we want to coerce each of them
        if coerce is not None:
            coerced = [self._coerce(v, coerce, accept_failure=allow_coerce_failure) for v in val]
            if by_reference:
                self._set_single(path, coerced)
            return coerced
        else:
            if by_reference:
                return val
            else:
                return deepcopy(val)

    def _set_single(self, path, val, coerce=None, allow_coerce_failure=False, allowed_values=None, allowed_range=None,
                    allow_none=True, ignore_none=False):

        if val is None and ignore_none:
            return

        if val is None and not allow_none:
            raise DataSchemaException("NoneType is not allowed at {x}".format(x=path))

        # first see if we need to coerce the value (and don't coerce None)
        if coerce is not None and val is not None:
            val = self._coerce(val, coerce, accept_failure=allow_coerce_failure)

        if allowed_values is not None and val not in allowed_values:
            raise DataSchemaException("Value {x} is not permitted at {y}".format(x=val, y=path))

        if allowed_range is not None:
            lower, upper = allowed_range
            if (lower is not None and val < lower) or (upper is not None and val > upper):
                raise DataSchemaException("Value {x} is outside the allowed range: {l} - {u}".format(x=val, l=lower, u=upper))

        # now set it at the path point in the object
        self._set_path(path, val)

    def _set_list(self, path, val, coerce=None, allow_coerce_failure=False, allow_none=True, ignore_none=False):
        # first ensure that the value is a list
        if not isinstance(val, list):
            val = [val]

        # now carry out the None check
        # for each supplied value, if it is none, and none is not allowed, raise an error if we do not
        # plan to ignore the nones.
        for v in val:
            if v is None and not allow_none:
                if not ignore_none:
                    raise DataSchemaException("NoneType is not allowed at {x}".format(x=path))

        # now coerce each of the values, stripping out Nones if necessary
        val = [self._coerce(v, coerce, accept_failure=allow_coerce_failure) for v in val if v is not None or not ignore_none]

        # check that the cleaned array isn't empty, and if it is behave appropriately
        if len(val) == 0:
            # this is equivalent to a None, so we need to decide what to do
            if ignore_none:
                # if we are ignoring nones, just do nothing
                return
            elif not allow_none:
                # if we are not ignoring nones, and not allowing them, raise an error
                raise DataSchemaException("Empty array not permitted at {x}".format(x=path))

        # now set it on the path
        self._set_path(path, val)

    def _add_to_list(self, path, val, coerce=None, allow_coerce_failure=False, allow_none=False, ignore_none=True, unique=False):
        if val is None and ignore_none:
            return

        if val is None and not allow_none:
            raise DataSchemaException("NoneType is not allowed in list at {x}".format(x=path))

        # first coerce the value
        if coerce is not None:
            val = self._coerce(val, coerce, accept_failure=allow_coerce_failure)
        current = self._get_list(path, by_reference=True)

        # if we require the list to be unique, check for the value first
        if unique:
            if val in current:
                return

        # otherwise, append
        current.append(val)

    def _utf8_unicode(self):
        """
        DEPRECATED - use dataobj.to_unicode() instead
        """
        return to_unicode()

    def _int(self):
        """
        DEPRECATED - use dataobj.to_int() instead
        """
        return to_int()

    def _float(self):
        """
        DEPRECATED - use dataobj.to_float() instead
        """
        return to_float()

    def _date_str(self, in_format=None, out_format=None):
        """
        DEPRECATED - use dataobj.date_str instead
        """
        return date_str(in_format=in_format, out_format=out_format)



############################################################
## Primitive object schema validation

class ObjectSchemaValidationError(Exception):
    pass


def validate(obj, schema):
    """
    DEPRECATED - use "construct" instead

    :param obj:
    :param schema:
    :return:
    """
    # all fields
    allowed = schema.get("bools", []) + schema.get("fields", []) + schema.get("lists", []) + schema.get("objects", [])

    for k, v in obj.items():
        # is k allowed at all
        if k not in allowed:
            raise ObjectSchemaValidationError("object contains key " + k + " which is not permitted by schema")

        # check the bools are bools
        if k in schema.get("bools", []):
            if type(v) != bool:
                raise ObjectSchemaValidationError("object contains " + k + " = " + str(v) + " but expected boolean")

        # check that the fields are plain old strings
        if k in schema.get("fields", []):
            if type(v) != str and type(v) != str and type(v) != int and type(v) != float:
                raise ObjectSchemaValidationError("object contains " + k + " = " + str(v) + " but expected string, unicode or a number")

        # check that the lists are really lists
        if k in schema.get("lists", []):
            if type(v) != list:
                raise ObjectSchemaValidationError("object contains " + k + " = " + str(v) + " but expected list")
            # if it is a list, then for each member validate
            entry_schema = schema.get("list_entries", {}).get(k)
            if entry_schema is None:
                # validate the entries as fields
                for e in v:
                    if type(e) != str and type(e) != str and type(e) != int and type(e) != float:
                        raise ObjectSchemaValidationError("list in object contains " + str(type(e)) + " but expected string, unicode or a number in " + k)
            else:
                # validate each entry against the schema
                for e in v:
                    validate(e, entry_schema)

        # check that the objects are objects
        if k in schema.get("objects", []):
            if type(v) != dict:
                raise ObjectSchemaValidationError("object contains " + k + " = " + str(v) + " but expected object/dict")
            # if it is an object, then validate
            object_schema = schema.get("object_entries", {}).get(k)
            if object_schema is None:
                #raise ObjectSchemaValidationError("no object entry for object " + k)
                pass # we are not imposing a schema on this object
            else:
                validate(v, object_schema)

############################################################
## Data structure coercion

class DataStructureException(Exception):
    pass

def construct(obj, struct, coerce, context="", silent_prune=False):
    """
    {
        "fields" : {
            "field_name" : {"coerce" :"coerce_function", **kwargs}

        },
        "objects" : [
            "field_name"
        ],
        "lists" : {
            "field_name" : {"contains" : "object|field", "coerce" : "field_coerce_function, **kwargs}
        },
        "required" : ["field_name"],
        "structs" : {
            "field_name" : {
                <construct>
            }
        }
    }

    :param obj:
    :param struct:
    :param coerce:
    :return:
    """
    if obj is None:
        return None

    # check that all the required fields are there
    keys = list(obj.keys())
    for r in struct.get("required", []):
        if r not in keys:
            c = context if context != "" else "root"
            raise DataStructureException("Field '{r}' is required but not present at '{c}'".format(r=r, c=c))

    # check that there are no fields that are not allowed
    # Note that since the construct mechanism copies fields explicitly, silent_prune literally just turns off this
    # check
    if not silent_prune:
        allowed = list(struct.get("fields", {}).keys()) + struct.get("objects", []) + list(struct.get("lists", {}).keys())
        for k in keys:
            if k not in allowed:
                c = context if context != "" else "root"
                raise DataStructureException("Field '{k}' is not permitted at '{c}'".format(k=k, c=c))


    # this is the new object we'll be creating from the old
    constructed = DataObj()

    # now check all the fields
    for field_name, instructions in struct.get("fields", {}).items():
        val = obj.get(field_name)
        if val is None:
            continue
        coerce_fn = coerce.get(instructions.get("coerce", "unicode"))
        if coerce_fn is None:
            raise DataStructureException("No coersion function defined for type '{x}' at '{c}'".format(x=instructions.get("coerce", "unicode"), c=context + field_name))

        kwargs = construct_kwargs("field", "set", instructions)

        try:
            constructed._set_single(field_name, val, coerce=coerce_fn, **kwargs)
        except DataSchemaException as e:
            raise DataStructureException(str(e))

    # next check all the objetcs (which will involve a recursive call to this function)
    for field_name in struct.get("objects", []):
        val = obj.get(field_name)
        if val is None:
            continue
        if type(val) != dict:
            raise DataStructureException("Found '{x}' = '{y}' but expected object/dict".format(x=context + field_name, y=val))

        instructions = struct.get("structs", {}).get(field_name)

        if instructions is None:
            # this is the lowest point at which we have instructions, so just accept the data structure as-is
            # (taking a deep copy to destroy any references)
            try:
                constructed._set_single(field_name, deepcopy(val))
            except DataSchemaException as e:
                raise DataStructureException(str(e))
        else:
            # we need to recurse further down
            beneath = construct(val, instructions, coerce=coerce, context=context + field_name + ".", silent_prune=silent_prune)

            # what we get back is the correct sub-data structure, which we can then store
            try:
                constructed._set_single(field_name, beneath)
            except DataSchemaException as e:
                raise DataStructureException(str(e))

    # now check all the lists
    for field_name, instructions in struct.get("lists", {}).items():
        vals = obj.get(field_name)
        if vals is None:
            continue

        # prep the keyword arguments for the setters
        kwargs = construct_kwargs("list", "set", instructions)

        contains = instructions.get("contains")
        if contains == "field":
            # coerce all the values in the list
            coerce_fn = coerce.get(instructions.get("coerce", "unicode"))
            if coerce_fn is None:
                raise DataStructureException("No coersion function defined for type '{x}' at '{c}'".format(x=instructions.get("coerce", "unicode"), c=context + field_name))

            for i in range(len(vals)):
                val = vals[i]
                try:
                    constructed._add_to_list(field_name, val, coerce=coerce_fn, **kwargs)
                except DataSchemaException as e:
                    raise DataStructureException(str(e))

        elif contains == "object":
            # for each object in the list, send it for construction
            for i in range(len(vals)):
                val = vals[i]

                if type(val) != dict:
                    raise DataStructureException("Found '{x}[{p}]' = '{y}' but expected object/dict".format(x=context + field_name, y=val, p=i))

                subinst = struct.get("structs", {}).get(field_name)
                if subinst is None:
                    try:
                        constructed._add_to_list(field_name, deepcopy(val))
                    except DataSchemaException as e:
                        raise DataStructureException(str(e))
                else:
                    # we need to recurse further down
                    beneath = construct(val, subinst, coerce=coerce, context=context + field_name + "[" + str(i) + "].", silent_prune=silent_prune)

                    # what we get back is the correct sub-data structure, which we can then store
                    try:
                        constructed._add_to_list(field_name, beneath)
                    except DataSchemaException as e:
                        raise DataStructureException(str(e))

        else:
            raise DataStructureException("Cannot understand structure where list '{x}' elements contain '{y}'".format(x=context + field_name, y=contains))

    return constructed.data


def construct_merge(target, source):
    merged = deepcopy(target)

    for field, instructions in source.get("fields", {}).items():
        if "fields" not in merged:
            merged["fields"] = {}
        if field not in merged["fields"]:
            merged["fields"][field] = deepcopy(instructions)

    for obj in source.get("objects", []):
        if "objects" not in merged:
            merged["objects"] = []
        if obj not in merged["objects"]:
            merged["objects"].append(obj)

    for field, instructions in source.get("lists", {}).items():
        if "lists" not in merged:
            merged["lists"] = {}
        if field not in merged["lists"]:
            merged["lists"][field] = deepcopy(instructions)

    for r in source.get("required", []):
        if "required" not in merged:
            merged["required"] = []
        if r not in merged["required"]:
            merged["required"].append(r)

    for field, struct in source.get("structs", {}).items():
        if "structs" not in merged:
            merged["structs"] = {}
        if field not in merged["structs"]:
            merged["structs"][field] = deepcopy(struct)

    return merged

def construct_lookup(path, struct):
    bits = path.split(".")

    # if there's more than one path element, we will need to recurse
    if len(bits) > 1:
        # it has to be an object, in order for the path to still have multiple
        # segments
        if bits[0] not in struct.get("objects", []):
            return None, None, None
        substruct = struct.get("structs", {}).get(bits[0])
        return construct_lookup(".".join(bits[1:]), substruct)
    elif len(bits) == 1:
        # first check the fields
        instructions = struct.get("fields", {}).get(bits[0])
        if instructions is not None:
            return "field", None, instructions

        # then check the lists
        instructions = struct.get("lists", {}).get(bits[0])
        if instructions is not None:
            structure = struct.get("structs", {}).get(bits[0])
            return "list", structure, instructions

        # then check the objects
        if bits[0] in struct.get("objects", []):
            structure = struct.get("structs", {}).get(bits[0])
            return "object", structure, None

    return None, None, None

def construct_kwargs(type, dir, instructions):
    # if there are no instructions there are no kwargs
    if instructions is None:
        return {}

    # take a copy of the instructions that we can modify
    kwargs = deepcopy(instructions)

    # remove the known arguments for the field type
    if type == "field":
        if "coerce" in kwargs:
            del kwargs["coerce"]

    elif type == "list":
        if "coerce" in kwargs:
            del kwargs["coerce"]
        if "contains" in kwargs:
            del kwargs["contains"]

    nk = {}
    if dir == "set":
        for k, v in kwargs.items():
            # basically everything is a "set" argument unless explicitly stated to be a "get" argument
            if not k.startswith("get__"):
                if k.startswith("set__"):    # if it starts with the set__ prefix, remove it
                    k = k[5:]
                nk[k] = v
    elif dir == "get":
        for k, v in kwargs.items():
            # must start with "get" argument
            if k.startswith("get__"):
                nk[k[5:]] = v

    return nk

def construct_data_keys(struct):
    return list(struct.get("fields", {}).keys()) + struct.get("objects", []) + list(struct.get("lists", {}).keys())

############################################################
## Unit test support

def test_dataobj(obj, fields_and_values):
    """
    Test a dataobj to make sure that the getters and setters you have specified
    are working correctly.

    Provide it a data object and a list of fields with the values to set and the expeceted return values (if required):

    {
        "key" : ("set value", "get value")
    }

    If you provide only the set value, then the get value will be required to be the same as the set value in the test

    {
        "key" : "set value"
    }

    :param obj:
    :param fields_and_values:
    :return:
    """
    for k, valtup in fields_and_values.items():
        if not isinstance(valtup, tuple):
            valtup = (valtup,)
        set_val = valtup[0]
        try:
            setattr(obj, k, set_val)
        except AttributeError:
            assert False, "Unable to set attribute {x} with value {y}".format(x=k, y=set_val)

    for k, valtup in fields_and_values.items():
        if not isinstance(valtup, tuple):
            valtup = (valtup,)
        get_val = valtup[0]
        if len(valtup) > 1:
            get_val = valtup[1]
        val = getattr(obj, k)
        assert val == get_val, (k, val, get_val)