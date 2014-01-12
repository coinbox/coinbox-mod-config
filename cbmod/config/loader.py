from pydispatch import dispatcher

import cbpos
logger = cbpos.get_logger(__name__)

from cbpos.modules import BaseModuleLoader

class ModuleLoader(BaseModuleLoader):
    def menu(self):
        from cbpos.interface import MenuItem
        from cbpos.mod.config.views import MainConfigPage
        
        return [
                [],
                [MenuItem('configuration', parent='system',
                          label=cbpos.tr.config._('Configuration'),
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
        cbpos.load_database(False)
        cbpos.load_menu(False)
        logger.info('Running configuration...')
        
        dispatcher.connect(self.do_run_config, signal='ui-post-init', sender=dispatcher.Any)
        cbpos.break_init()
    
    def do_run_config(self):
        # Prompt the user to change database configuration
        from cbpos.mod.config.views.dialogs import DatabaseConfigDialog
        win = DatabaseConfigDialog()
        cbpos.ui.set_main_window(win)
    
    def run_raw_config(self, args):
        cbpos.use_translation(False)
        cbpos.load_database(False)
        cbpos.load_menu(False)
        logger.info('Running raw configuration...')
        
        cbpos.break_init()
        dispatcher.connect(self.do_run_raw_config, signal='ui-post-init',
                           sender=dispatcher.Any)
    
    def do_run_raw_config(self):
        # Prompt the user to change raw configuration data
        from cbpos.mod.config.views.dialogs import RawConfigDialog
        win = RawConfigDialog()
        cbpos.ui.set_main_window(win)
