import cbpos
from cbpos.modules import BaseModuleMetadata

class ModuleMetadata(BaseModuleMetadata):
    base_name = 'config'
    version = '0.1.0'
    display_name = 'Configuration Interface Module'
    dependencies = (
        ('base', '0.1'),
    )
    config_defaults = tuple()
