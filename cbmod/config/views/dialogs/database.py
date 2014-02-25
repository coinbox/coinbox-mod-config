from PySide import QtGui, QtCore

import Queue
from sqlalchemy import exc

import cbpos
from cbpos.database import Profile, Driver, \
                        ProfileNotFoundError, DriverNotFoundError

from cbmod.base.views.wizard import BaseWizard, BaseWizardPage
from cbmod.config.views.wizard import DatabaseInfoWizardPage, DatabaseProfileConfigWizardPage, DatabaseSetupWizardPage

logger = cbpos.get_logger(__name__)

class DatabaseConfigDialog(BaseWizard):
    def __init__(self, parent=None, flags=0):
        super(DatabaseConfigDialog, self).__init__(parent, flags)
        
        self.setWindowTitle(cbpos.tr.config_("Coinbox Database Setup"))
        
        self.__info_page = DatabaseInfoWizardPage(self)
        self.__info_page.pageId = self.addPage(self.__info_page)
        
        self.__profile_page = DatabaseProfileConfigWizardPage(self)
        self.__profile_page.pageId = self.addPage(self.__profile_page)
        self.__info_page.configPageId = self.__profile_page.pageId
        
        self.__setup_page = DatabaseSetupWizardPage(self)
        self.__setup_page.pageId = self.addPage(self.__setup_page)
        self.__info_page.setupPageId = self.__setup_page.pageId
