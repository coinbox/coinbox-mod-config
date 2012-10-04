from pydispatch import dispatcher
import logging
logger = logging.getLogger(__name__)

import cbpos
from cbpos.modules import BaseModuleLoader

class ModuleLoader(BaseModuleLoader):
    dependencies = ('base',)
    name = 'Configuration Interface Module'

    def menu(self):
        from cbpos.mod.config.views import MainConfigPage
            
        return [[],
                [{'parent': 'System', 'label': 'Configuration', 'page': MainConfigPage, 'image': self.res('images/menu-configuration.png')}]]
    
    def argparser(self):
        parser1 = cbpos.subparsers.add_parser('config', description="Run qtPos database configuration")
        parser1.set_defaults(handle=self.load_config)
        
        parser2 = cbpos.subparsers.add_parser('raw-config', description="Run qtPos raw configuration editor")
        parser2.set_defaults(handle=self.load_raw_config)

    def load_config(self, args):
        cbpos.load_database(False)
        cbpos.load_menu(False)
        logger.info('Running configuration...')
        
        dispatcher.connect(self.do_load_config, signal='ui-post-init', sender=dispatcher.Any)
        cbpos.break_init()
    
    def load_raw_config(self, args):
        cbpos.use_translation(False)
        cbpos.load_database(False)
        cbpos.load_menu(False)
        logger.info('Running raw configuration...')
        
        cbpos.break_init()
        dispatcher.connect(self.do_load_raw, signal='ui-post-init', sender=dispatcher.Any)

    def do_load_config(self):
        # Prompt the user to change database configuration
        from cbpos.mod.config.views.dialogs import DatabaseConfigDialog
        win = DatabaseConfigDialog()
        cbpos.ui.window = win
    
    def do_load_raw(self):
        # Prompt the user to change raw configuration data
        from cbpos.mod.config.views.dialogs import RawConfigDialog
        win = RawConfigDialog()
        cbpos.ui.window = win