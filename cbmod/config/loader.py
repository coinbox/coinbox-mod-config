from pydispatch import dispatcher

import cbpos
logger = cbpos.get_logger(__name__)

from cbpos.modules import BaseModuleLoader

class ModuleLoader(BaseModuleLoader):
    def menu(self):
        from cbpos.interface import MenuItem
        from cbmod.config.views import MainConfigPage
        
        return [
                [],
                [MenuItem('configuration', parent='system',
                          label=cbpos.tr.config_('Configuration'),
                          icon=cbpos.res.config('images/menu-configuration.png'),
                          page=MainConfigPage)
                 ]
                ]
    
    def load_argparsers(self):
        parser1 = cbpos.subparsers.add_parser('config', description="Run qtPos database configuration")
        parser1.set_defaults(handle=self.run_config)
        
        parser2 = cbpos.subparsers.add_parser('raw-config', description="Run qtPos raw configuration editor")
        parser2.set_defaults(handle=self.run_raw_config)

    def run_config(self, args):
        logger.info('Running database configuration...')
        
        cbpos.loader.autoload_database(False)
        cbpos.loader.autoload_interface(False)
        
        dispatcher.connect(self.do_run_config, signal='ui-post-init', sender=dispatcher.Any)
    
    def do_run_config(self):
        # Prompt the user to change database configuration
        from cbmod.config.views.dialogs import DatabaseConfigDialog
        win = DatabaseConfigDialog()
        cbpos.ui.chain_window(win, cbpos.ui.PRIORITY_FIRST_HIGHEST)
    
    def run_raw_config(self, args):
        logger.info('Running raw configuration...')
        
        cbpos.loader.autoload_translation(False)
        cbpos.loader.autoload_database(False)
        cbpos.loader.autoload_interface(False)
        
        dispatcher.connect(self.do_run_raw_config, signal='ui-post-init', sender=dispatcher.Any)
    
    def do_run_raw_config(self):
        # Prompt the user to change raw configuration data
        from cbmod.config.views.dialogs import RawConfigDialog
        win = RawConfigDialog()
        cbpos.ui.chain_window(win, cbpos.ui.PRIORITY_FIRST_HIGHEST)
