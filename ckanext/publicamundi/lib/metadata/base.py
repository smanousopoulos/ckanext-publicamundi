import threading
import logging
import json
import zope.interface
import zope.interface.verify
import zope.schema
from collections import namedtuple

from ckanext.publicamundi.lib import dictization
from ckanext.publicamundi.lib import logger
from ckanext.publicamundi.lib.json_encoder import JsonEncoder
from ckanext.publicamundi.lib.metadata import adapter_registry
from ckanext.publicamundi.lib.metadata.ibase import IObject, ISerializer
from ckanext.publicamundi.lib.metadata.serializers import get_field_serializer
from ckanext.publicamundi.lib.metadata.serializers import get_key_tuple_serializer

_cache = threading.local()

FieldContext = namedtuple('FieldContext', ['key', 'obj'], verbose=False)

class Object(object):
    zope.interface.implements(IObject)

    default_factories = {
        zope.schema.TextLine: None,
        zope.schema.Text: None,
        zope.schema.BytesLine: None,
        zope.schema.Bytes: None,
        zope.schema.Int: None,
        zope.schema.Float: None,
        zope.schema.Bool: None,
        zope.schema.Datetime: None,
        zope.schema.Date: None,
        zope.schema.Time: None,
        zope.schema.List: list,
        zope.schema.Tuple: list,
        zope.schema.Dict: dict,
    }

    KEY_GLUE = '.'

    ## interface IObject

    @classmethod
    def schema(cls):
        return cls.get_schema()

    def get_field(self, k):
        '''Return a bound field for attribute k'''
        cls = type(self)
        S = cls.get_schema()
        return S.get(k).bind(FieldContext(key=k, obj=self))

    def validate(self):
        '''Return a list <errors> structured as:

          errors ::= [ (k, ef), ... ]
          ef ::= [ ex1, ex2, ...]
          ex ::= Invalid(arg0, arg1, ...)
          arg0 ::= errors
          arg0 ::= <literal-value>

        Notation:
          ef : field-errors
          ex : exception (derived from Invalid)

        '''
        cls = type(self)
        return cls.Validator(self).validate()

    def to_dict(self, flat=False, opts={}):
        if flat:
            res = self.flatten(opts)
            if 'serialize-keys' in opts:
                key_serializer = get_key_tuple_serializer(self.KEY_GLUE)
                res = { key_serializer.dumps(k): v for k, v in res.items() }
        else:
            res = self.dictize(opts)
        return res

    def from_dict(self, d, is_flat=None, opts={}):
        assert isinstance(d, dict)
        cls = type(self)
        
        # Decide if input is a flattened dict
        if is_flat is None:
            is_flat = isinstance(d.iterkeys().next(), tuple)
        if is_flat:
            if 'unserialize-keys' in opts:
                key_serializer = get_key_tuple_serializer(cls.KEY_GLUE)
                d = dictization.unflatten({
                    key_serializer.loads(k): v for k, v in d.items()
                })
                opts.pop('unserialize-keys')
            else:
                d = dictization.unflatten(d)
                
        # Load self
        self.load(d, opts)
        # Allow method chaining
        return self

    def to_json(self, flat=False, indent=None):
        cls = type(self)
        opts = {
            'serialize-keys': flat,
            'serialize-values': True,
        }
        d = self.to_dict(flat, opts)
        return json.dumps(d, indent=indent)

    def from_json(self, s, is_flat=False):
        cls = type(self)
        d = json.loads(s)
        opts = {
            'unserialize-keys': is_flat,
            'unserialize-values': True,
        }
        return self.from_dict(d, is_flat, opts=opts)

    ## Constructor based on keyword args 

    def __init__(self, **kwargs):
        cls = type(self)
        S = cls.get_schema()
        for k,F in zope.schema.getFields(S).items():
            a = getattr(cls, k)
            if isinstance(a, property):
                continue
            v = kwargs.get(k)
            if v is None:
                factory = cls.get_field_factory(k, F)
                v = factory() if factory else F.default
            setattr(self, k, v)

    ## Provide a string representation

    def __repr__(self):
        cls = type(self)
        typename = cls.__name__ #"%s:%s" %(cls.__module__, cls.__name__)
        s = '<' + typename
        for k,F in self.get_fields().items():
            f = F.get(self)
            if f:
                s += ' %s=%s' %(k, repr(f))
        s += '>'
        return s

    ## Introspective class methods

    @classmethod
    def lookup_schema(cls):
        S = None
        for iface in zope.interface.implementedBy(cls):
            if iface.extends(IObject):
                S = iface
                break
        return S

    @classmethod
    def get_schema(cls):
        S = None
        if not hasattr(_cache, 'schema'):
            _cache.schema = {}
        try:
            S = _cache.schema[cls]
        except KeyError:
            S  = cls.lookup_schema()
            _cache.schema[cls] = S
        return S

    @classmethod
    def get_field_names(cls):
        S = cls.get_schema()
        return zope.schema.getFieldNames(S) 

    @classmethod
    def get_fields(cls):
        S = cls.get_schema()
        return zope.schema.getFields(S)

    @classmethod
    def get_flattened_fields(cls):
        return cls.flatten_schema(cls.get_schema())

    @staticmethod
    def flatten_schema(schema):
        res = {}
        fields = zope.schema.getFields(schema)
        for k, F in fields.items():
            res1 = Object.flatten_field(F)
            for k1, F1 in res1.items():
                res[(k,)+k1] = F1
        return res

    @staticmethod
    def flatten_field(F):
        assert isinstance(F, zope.schema.Field)
        res = None
        if isinstance(F, zope.schema.Object):
            res = Object.flatten_schema(F.schema)
        elif isinstance(F, zope.schema.List) or isinstance(F, zope.schema.Tuple):
            res = {}
            res1 = Object.flatten_field(F.value_type)
            for i in range(0, F.max_length):
                for k1,F1 in res1.items():
                    res[(i,)+k1] = F1
        elif isinstance(F, zope.schema.Dict):
            assert isinstance(F.key_type, zope.schema.Choice), \
                'Only zope.schema.Choice supported for key_type'
            res = {}
            res1 = Object.flatten_field(F.value_type)
            for v in F.key_type.vocabulary:
                for k1,F1 in res1.items():
                    res[(v.token,)+k1] = F1
        else:
            res = { (): F }
        return res

    @classmethod
    def get_field_factory(cls, k, F=None):
        assert not k or isinstance(k, basestring)
        assert not F or isinstance(F, zope.schema.Field)
        assert k or F, 'At least one of k(key), F(Field) should be specified'
        factory = None
        # Check if a factory is defined explicitly as a class attribute
        if k and hasattr(cls, k):
            a = getattr(cls, k)
            if callable(a):
                factory = a
                return factory
        # Find a sensible factory for this field 
        if not F:
            S = cls.get_schema()
            F = S.get(k)
            if not F:
                raise ValueError('Cannot find field %s for schema %s' %(k,S))
        if isinstance(F, zope.schema.Object):
            factory = adapter_registry.lookup([], F.schema)
        else:
            factory = F.defaultFactory or cls.default_factories.get(type(F))
        return factory

    ## Validation 

    class Validator(object):

        def __init__(self, obj, opts=None):
            self.obj = obj
            self.opts = opts or {}
            return

        def validate(self):
            '''Return <errors> following the structure of Object.validate() result'''
            errors = self.validate_schema()
            if errors:
                # Stop here, do not check invariants
                return errors
            else:
                return self.validate_invariants()

        def validate_schema(self):
            '''Return <errors>'''
            S = self.obj.get_schema()
            errors = []
            for k,F in zope.schema.getFields(S).items():
                f = F.get(self.obj)
                ef = self._validate_schema_for_field(f, F)
                if ef:
                    errors.append((k, ef))
            return errors

        def _validate_schema_for_field(self, f, F):
            '''Return <ef>, i.e. an array of field-specific exceptions'''
            ef = []
            # Check if empty
            if f is None:
                # Check if required
                try:
                    F.validate(f)
                except zope.interface.Invalid as ex:
                    ef.append(ex)
                return ef
            # If here, we are processing an non-empty field
            if isinstance(F, zope.schema.Object):
                # Check interface is provided by instance f 
                try:
                    zope.interface.verify.verifyObject(F.schema, f)
                except zope.interface.Invalid as ex:
                    ef.append(ex)
                # If provides, descend into object's schema validation
                if not ef and isinstance(f, Object):
                    cls = type(self)
                    errors = cls(f, self.opts).validate_schema()
                    if errors:
                        ef.append(zope.interface.Invalid(errors))
            elif isinstance(F, zope.schema.List) or isinstance(F, zope.schema.Tuple):
                # Check is a list type
                if not (isinstance(f, list) or isinstance(f, tuple)):
                    try:
                        F.validate(f)
                    except zope.interface.Invalid as ex:
                        ef.append(ex)
                # If type is ok, proceed to schema validation
                if not ef:
                    exs = self._validate_schema_for_field_items(enumerate(f), F)
                    if exs:
                        ef.extend(exs)
            elif isinstance(F, zope.schema.Dict):
                # Check is a dict type
                if not isinstance(f, dict):
                    try:
                        F.validate(f)
                    except zope.interface.Invalid as ex:
                        ef.append(ex)
                # If type is ok, proceed to schema validation
                if not ef:
                    exs = self._validate_schema_for_field_items(f.iteritems(), F)
                    if exs:
                        ef.extend(exs)
            else:
                # A leaf field: validate directly via Field
                try:
                    F.validate(f)
                except zope.interface.Invalid as ex:
                    ef.append(ex)
            return ef

        def _validate_schema_for_field_items(self, items, F):
            '''Return list of <ex> i.e. a list of Invalid-based exceptions'''
            exs = []
            # Hydrate items (must be re-used)
            items = list(items)

            # 1. Validate length contraints
            if F.min_length and len(items) < F.min_length:
                exs.append(zope.schema.interfaces.TooShort(
                    'The collection is too short (< %d)' % (F.min_length)))
            
            if F.max_length and len(items) > F.max_length:
                exs.append(zope.schema.interfaces.TooBig(
                    'The collection is too big (> %d)' % (F.max_length)))

            # 2. Validate items
            errors = []
            # 2.1 Validate item keys (if exist)
            if hasattr(F, 'key_type') and F.key_type:
                assert isinstance(F.key_type, zope.schema.Choice)
                for k,y in items:
                    try:
                        F.key_type.validate(k)
                    except zope.interface.Invalid as ex:
                        errors.append((k, [ex]))
                pass
            # 2.2 Validate item values
            for k,y in items:
                ef = self._validate_schema_for_field(y, F.value_type)
                if ef:
                    errors.append((k, ef))
            if errors:
                exs.append(zope.interface.Invalid(errors))

            return exs

        def validate_invariants(self):
            '''Return <errors>'''
            errors = []
            S = self.obj.get_schema()

            # Descend into field invariants
            recurse = False
            try:
                recurse = S.getTaggedValue('recurse-on-invariants')
            except KeyError:
                pass
            if recurse:
                for k,F in zope.schema.getFields(S).items():
                    f = F.get(self.obj)
                    if not f:
                        continue
                    ef = self._validate_invariants_for_field(f, F)
                    if ef:
                        errors.append((k, ef))

            # Check own invariants
            try:
                S.validateInvariants(self.obj)
            except zope.interface.Invalid as ex:
                errors.append((None, [ex]))

            return errors

        def _validate_invariants_for_field(self, f, F):
            '''Returns <ef>, i.e. an array of field-specific exceptions'''
            ef = []

            ex  = None
            if isinstance(F, zope.schema.Object):
                cls = type(self)
                errors = cls(f, self.opts).validate_invariants()
                if errors:
                    ex = zope.interface.Invalid(errors)
            elif isinstance(F, zope.schema.List) or isinstance(F, zope.schema.Tuple):
                ex = self._validate_invariants_for_field_items(enumerate(f), F)
            elif isinstance(F, zope.schema.Dict):
                ex = self._validate_invariants_for_field_items(f.iteritems(), F)

            if ex:
                ef.append(ex)
            return ef

        def _validate_invariants_for_field_items(self, items, F):
            '''Return <ex> i.e. an Invalid-based exception'''
            ex = None
            
            errors = []
            for k,y in items:
                ef = self._validate_invariants_for_field(y, F.value_type)
                if ef:
                    errors.append((k, ef))
            
            if errors:
                ex = zope.interface.Invalid(errors)
            return ex    

    ## Error helpers - Convert error lists 

    def dictize_errors(self, errors):
        ''' Convert an <errors> structure to a nested dict '''
        return self._dictize_errors(errors)

    INVARIANT_ERROR_KEY = '__after'

    def _dictize_errors(self, errors):
        cls = type(self)
        S = cls.get_schema()
        res = dict()
        for k, ef in errors:
            # Fixme Pick the 1st exception (is this ok?)
            ex = ef[0]
            if k is None:
                # Found a failed invariant
                # Todo: maybe use defaultdict(list)
                if not res.has_key(cls.INVARIANT_ERROR_KEY):
                    res[cls.INVARIANT_ERROR_KEY] = list()
                res[cls.INVARIANT_ERROR_KEY].append(str(ex))
            else:
                # Found a field-specific error
                F = S.get(k)
                if not F:
                    continue
                f = F.get(self)
                res[k] = self._dictize_errors_for_field(ex, f, F)
        return res

    def _dictize_errors_for_field(self, ex, f, F):
        assert isinstance(ex, zope.interface.Invalid), \
            'Validation errors should derive from Invalid'
        
        # Check if we must descend 
        if not (ex.args and isinstance(ex.args[0], list)):
            # Treat this as a literal, stop descending
            return '%s: %s' %(type(ex).__name__, str(ex).strip())

        # If here, we have a valid <errors> list
        errors = ex.args[0]
        if isinstance(F, zope.schema.Object):
            # If supports further dictization, descent into object
            if isinstance(f, Object):
                return f._dictize_errors(errors)
            else:
                return errors
        elif isinstance(F, zope.schema.List) or isinstance(F, zope.schema.Tuple):
            return self._dictize_errors_for_field_collection(errors, f, F)
        elif isinstance(F, zope.schema.Dict):
            return self._dictize_errors_for_field_collection(errors, f, F)
        else:
            return '%s: %s' %(type(ex).__name__, repr(errors))

    def _dictize_errors_for_field_collection(self, errors, f, F):
        res = {}
        for k, ef in errors:
            # Fixme again, pick the 1st exception
            ex = ef[0]
            # Note that here, k will be either an integer or a string
            res[k] = self._dictize_errors_for_field(ex, f[k], F.value_type)
        return res

    def flatten_errors(self, errors):
        ''' Convert an <errors> structure to a flattened dict '''
        error_dict = self._dictize_errors(errors)
        return dictization.flatten(error_dict)

    ## Dictization helpers

    class Dictizer(object):

        def __init__(self, obj, opts={}):
            self.obj = obj
            self.opts = opts

        def dictize(self):
            obj = self.obj
            obj_cls = type(obj)
            S = obj_cls.get_schema()
            res = {}
            fields = zope.schema.getFields(S)
            for k, F in fields.items():
                a = getattr(obj_cls, k)
                if isinstance(a, property):
                    continue
                f = F.get(obj)
                if f is None:
                    res[k] = None
                else:
                    res[k] = self._dictize_field(f, F)
            return res

        def _get_field_value(self, f, F):
            '''Get the value of a field considered as a leaf.
            Serialize this value if requested so.
            '''
            v = f
            if self.opts.get('serialize-values'):
                serializer = get_field_serializer(F)
                if serializer:
                    v = serializer.dumps(f)
            return v

        def _dictize_field(self, f, F):
            if isinstance(F, zope.schema.Object):
                if isinstance(f, Object):
                    cls = type(self)
                    return cls(f, self.opts).dictize()
                else:
                    # Can only dictize derivatives of Object
                    return None
            elif isinstance(F, zope.schema.List) or isinstance(F, zope.schema.Tuple):
                a = list()
                for i,y in enumerate(f):
                    a.append(self._dictize_field(y, F.value_type))
                return a
            elif isinstance(F, zope.schema.Dict):
                d = dict()
                for k,y in f.items():
                    d[k] = self._dictize_field(y, F.value_type)
                return d
            else:
                # A leaf field 
                return self._get_field_value(f, F)

        def flatten(self):
            obj = self.obj
            obj_cls = type(obj)
            S = obj_cls.get_schema()
            res = {}
            fields = zope.schema.getFields(S)
            for k, F in fields.items():
                a = getattr(obj_cls, k)
                if isinstance(a, property):
                    continue
                f = F.get(obj)
                if f is None:
                    pass
                else:
                    res1 = self._flatten_field(f, F)
                    for k1,v1 in res1.items():
                        res[(k,)+k1] = v1
            return res

        def _flatten_field(self, f, F):
            if isinstance(F, zope.schema.Object):
                if isinstance(f, Object):
                    cls = type(self)
                    return cls(f, self.opts).flatten()
                else:
                    # Can only flatten derivatives of Object (see _dictize_field()) 
                    return None
            elif isinstance(F, zope.schema.List) or isinstance(F, zope.schema.Tuple):
                return self._flatten_field_items(enumerate(f), F)
            elif isinstance(F, zope.schema.Dict):
                return self._flatten_field_items(f.iteritems(), F)
            else:
                # A leaf field
                v = self._get_field_value(f, F)
                return { (): v }

        def _flatten_field_items(self, items, F):
            d = dict()
            for k,y in items:
                res1 = self._flatten_field(y, F.value_type)
                for k1,v1 in res1.items():
                    d[(k,)+k1] = v1
            return d

    class Loader(object):

        def __init__(self, obj, opts={}):
            self.obj = obj
            self.opts = opts

        def load(self, d):
            obj = self.obj
            obj_cls = type(obj)
            S = obj_cls.get_schema()
            for k, F in zope.schema.getFields(S).items():
                a = getattr(obj_cls, k)
                if isinstance(a, property):
                    continue
                v = d.get(k)
                factory = obj.get_field_factory(k, F)
                f = None
                if v is None:
                    # No value given, use factory (if exists)
                    f = factory() if factory else F.default
                else:
                    # Input provided a value on k
                    f = self._create_field(v, F, factory)
                setattr(obj, k, f)
            return

        def _create_field(self, v, F, factory=None):
            assert isinstance(F, zope.schema.Field)
            cls = type(self)
            # Find a factory (if not given)
            if not factory:
                factory = self.obj.get_field_factory(None, F)
            # Create a new field instance
            if isinstance(F, zope.schema.Object):
                f = factory()
                if isinstance(f, Object):
                    cls(f, self.opts).load(v)
                else:
                    # Can only load derivatives of Object
                    pass
                return f
            elif isinstance(F, zope.schema.List) or isinstance(F, zope.schema.Tuple):
                a = list()
                for i,y in enumerate(v):
                    f1 = self._create_field(y, F.value_type)
                    a.append(f1)
                return a
            elif isinstance(F, zope.schema.Dict):
                d = dict()
                for k,y in v.items():
                    f1 = self._create_field(y, F.value_type)
                    d[k] = f1
                return d
            else:
                # A leaf field (may need to be unserialized)
                f = v
                if self.opts.get('unserialize-values'):
                    serializer = get_field_serializer(F)
                    if serializer:
                        f = serializer.loads(v)
                return f

    class Factory(object):

        def __init__(self, iface, opts={}):
            assert iface.extends(IObject), 'Expected a schema-providing interface'
            self.target_iface = iface
            self.target_cls = adapter_registry.lookup([], iface, '')
            if not self.target_cls:
                raise ValueError('Cannot find a class that implements %s' %(iface))
            self.opts = {
                'unserialize-values': False,
            }
            self.opts.update(opts)

        def from_dict(self, d, is_flat=False):
            return self.target_cls().from_dict(d, is_flat, self.opts)

        def __call__(self, d={}, is_flat=False):
            return self.from_dict(d, is_flat)

    def dictize(self, opts=None):
        cls = type(self)
        return cls.Dictizer(self, opts).dictize()

    def flatten(self, opts=None):
        cls = type(self)
        return cls.Dictizer(self, opts).flatten()

    def load(self, d, opts=None):
        cls = type(self)
        return cls.Loader(self, opts).load(d)

