import zope.interface

from ckanext.publicamundi.lib.metadata import adapter_registry
from ckanext.publicamundi.lib.metadata.base import Object
from ckanext.publicamundi.lib.metadata.schemata import *

class BaseMetadata(Object):
    zope.interface.implements(IBaseMetadata)

# Decorator for an object's null adapter (i.e. implementer)

def object_null_adapter(iface, name=''):
    assert hasattr(iface, 'interfaces')
    def decorate(cls):
        assert iface.implementedBy(cls)
        adapter_registry.register([], iface, name, cls)
        return cls
    return decorate

# Import types

from ckanext.publicamundi.lib.metadata.types.common import *
from ckanext.publicamundi.lib.metadata.types.metadata import *
from ckanext.publicamundi.lib.metadata.types.foo import Foo

