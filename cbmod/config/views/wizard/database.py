from PySide import QtGui, QtCore

import cbpos

logger = cbpos.get_logger(__name__)

from cbpos.database import Profile, Driver, ProfileNotFoundError, DriverNotFoundError

from cbmod.base.views.wizard import BaseWizardPage
from cbmod.config.views.widgets.database import DriverForm, DatabaseSetupWorker

class DatabaseInfoWizardPage(BaseWizardPage):
    
    configPageId = None
    setupPageId = None
    
    def __init__(self, parent=None):
        super(DatabaseInfoWizardPage, self).__init__(parent)
        
        self.label = QtGui.QLabel(cbpos.tr.config_("DATABASE_SETUP_INFORMATION"), self)
        
        self.configureBox = QtGui.QGroupBox(cbpos.tr.config_("DATABASE_PROFILE_SELECTION_RADIO_BOX"), self)
        
        self.profileNew = QtGui.QRadioButton(cbpos.tr.config_("DATABASE_PROFILE_RADIO_CREATE_NEW"), self.configureBox)
        self.profileSelect = QtGui.QRadioButton(cbpos.tr.config_("DATABASE_PROFILE_RADIO_SELECT_EXISTING"), self.configureBox)
        self.profileEdit = QtGui.QRadioButton(cbpos.tr.config_("DATABASE_PROFILE_RADIO_EDIT_EXISTING"), self.configureBox)
        
        self.profileNew.toggled.connect(self.onProfileSelectionToggled)
        self.profileSelect.toggled.connect(self.onProfileSelectionToggled)
        self.profileEdit.toggled.connect(self.onProfileSelectionToggled)
        
        self.profileCombo = QtGui.QComboBox(self.configureBox)
        self.profileCombo.setEditable(False)
        self.profileCombo.currentIndexChanged.connect(self.onProfileComboChanged)
        
        self.registerField('database_profile_new', self.profileNew)
        self.registerField('database_profile_select', self.profileSelect)
        self.registerField('database_profile_edit', self.profileEdit)
        self.registerField('database_profile_name', self.profileCombo, 'currentText')
        
        self.profileNew.setChecked(True)
        
        configureLayout = QtGui.QVBoxLayout()
        configureLayout.addWidget(self.profileNew)
        configureLayout.addWidget(self.profileSelect)
        configureLayout.addWidget(self.profileEdit)
        configureLayout.addWidget(self.profileCombo)
        self.configureBox.setLayout(configureLayout)
        
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.configureBox)
        
        self.setLayout(layout)
    
    def onProfileSelectionToggled(self):
        if self.profileNew.isChecked():
            self.profileCombo.setEnabled(False)
        elif self.profileEdit.isChecked() or self.profileSelect.isChecked():
            self.profileCombo.setEnabled(True)
        else:
            self.profileCombo.setEnabled(False)
        self.completeChanged.emit()
    
    def onProfileComboChanged(self):
        self.completeChanged.emit()
    
    def initializePage(self):
        self.profileCombo.clear()
        for p in Profile.get_all():
            self.profileCombo.addItem(p.name, p)
        self.profileCombo.setCurrentIndex(-1)
    
    def validatePage(self):
        if self.field('database_profile_new'):
            return True
        
        selected_profile_name = self.field('database_profile_name')
        if not selected_profile_name:
            return False
        
        try:
            profile = Profile.get(selected_profile_name)
        except ProfileNotFoundError:
            return False
        else:
            if not profile.editable and self.field('database_profile_edit'):
                return False
        
        return True
    
    def isComplete(self):
        if self.validatePage():
            return super(DatabaseInfoWizardPage, self).isComplete()
        else:
            return False
    
    def nextId(self):
        if self.field('database_profile_new') or self.field('database_profile_edit'):
            return self.configPageId
        elif self.field('database_profile_select'):
            return self.setupPageId
        else:
            # Should not happen, unless none of the radio buttons are selected
            return self.setupPageId

class DatabaseProfileConfigWizardPage(BaseWizardPage):
    def __init__(self, parent=None):
        super(DatabaseProfileConfigWizardPage, self).__init__(parent)
        
        self.profileText = QtGui.QLineEdit(self)
        self.registerField('database_profile_new_name*', self.profileText)
        
        self.driverChoice = QtGui.QComboBox(self)
        self.driverChoice.setEditable(False)
        self.driverChoice.currentIndexChanged.connect(self.onDriverChoiceChanged)
        
        self.driverFormPanel = QtGui.QGroupBox(self)
        self.driverFormPanel.setCheckable(False)
        self.driverFormPanel.setFlat(False)
        
        self.driverFormTabs = QtGui.QTabWidget(self.driverFormPanel)
        self.driverFormTabs.setTabsClosable(False)
        self.driverFormTabs.tabBar().setVisible(False)
        
        self.driverForms = {}
        self.drivers = Driver.get_all()
        self.drivers.sort(key=lambda d: d.display)
        for driver in self.drivers:
            self.driverForms[driver.name] = form = DriverForm(driver, self)
            self.driverFormTabs.addTab(form, driver.display)
            self.driverChoice.addItem(driver.display)
        
        self.driverFormPanel.setTitle(self.drivers[0].display)
        
        panelLayout = QtGui.QVBoxLayout()
        panelLayout.addWidget(self.driverFormTabs)
        self.driverFormPanel.setLayout(panelLayout)
        
        layout = QtGui.QFormLayout()
        layout.addRow(cbpos.tr.config_("Profile Name"), self.profileText)
        layout.addRow(cbpos.tr.config_("Database Driver"), self.driverChoice)
        layout.addRow(self.driverFormPanel)
        
        self.setLayout(layout)
    
    def onDriverChoiceChanged(self, index):
        self.current_driver = self.drivers[index]
        self.driverFormPanel.setTitle(self.current_driver.display)
        self.driverForms[self.current_driver.name].clear()
        self.driverFormTabs.setCurrentIndex(index)
    
    def initializePage(self):
        selected_profile_name = self.field('database_profile_name')
        if not selected_profile_name:
            return
        
        # Fill the form with the selected profile
        try:
            profile = Profile.get(selected_profile_name)
        except ProfileNotFoundError:
            logger.debug("Profile named {} was not found".format(selected_profile_name))
            self.wizard().back()
        else:
            if not profile.editable:
                logger.debug("Profile named {} is not editable".format(selected_profile_name))
                self.wizard.back()
        
        index = self.drivers.index(profile.driver)
        self.driverChoice.setCurrentIndex(index)
        for form in self.driverForms.itervalues():
            form.clear()
        self.driverForms[self.current_driver.name].setProfile(profile)
        
        self.profileText.setText(selected_profile_name)
    
    def validatePage(self):
        selected_profile_name = self.field('database_profile_name')
        new_profile_name = self.field('database_profile_new_name')
        if selected_profile_name:
            try:
                selected_profile = Profile.get(selected_profile_name)
            except ProfileNotFoundError:
                logger.debug("Profile named {} was not found".format(selected_profile_name))
                return False
        else:
            selected_profile = None
        
        if new_profile_name == selected_profile_name:
            profile = selected_profile
        else:
            try:
                profile = Profile.get(new_profile_name)
            except ProfileNotFoundError:
                if selected_profile:
                    profile = selected_profile
                    profile.name = new_profile_name
                else:
                    profile = Profile(name=new_profile_name, driver=self.current_driver)
            except:
                raise
            else:
                QtGui.QMessageBox.information(self, 'New Database Profile',
                    "A profile with this name already exists. Choose another name.", QtGui.QMessageBox.Ok)
                return False
        
        self.driverForms[self.current_driver.name].save(profile)
        profile.use()
        
        return True

class DatabaseSetupWizardPage(BaseWizardPage):
    def __init__(self, parent=None):
        super(DatabaseSetupWizardPage, self).__init__(parent)
        
        dsw = DatabaseSetupWorker
        
        statesLayout = QtGui.QGridLayout()
        
        self.stateIcons = {}
        self.stateLabels = {}
        self.stateDetails = {}
        
        labels = {dsw.STATE_INIT: "Initialize database",
                  dsw.STATE_LOAD: "Load database",
                  dsw.STATE_CREATE: "Create models",
                  dsw.STATE_TEST: "Insert test data",
                  dsw.STATE_DONE: "Finished setting up database"
                  }
        
        for i, state in enumerate((dsw.STATE_INIT, dsw.STATE_LOAD, dsw.STATE_CREATE, dsw.STATE_TEST, dsw.STATE_DONE)):
            self.stateIcons[state] = icon = QtGui.QLabel(self)
            self.stateLabels[state] = label = QtGui.QLabel(labels[state], self)
            self.stateDetails[state] = details = QtGui.QLabel(self)
            self.stateDetails[state].setWordWrap(True)
            
            statesLayout.addWidget(icon, i, 0)
            statesLayout.addWidget(label, i, 1)
            statesLayout.addWidget(details, i, 2)
        
        statesLayout.setColumnStretch(0, 0)
        statesLayout.setColumnStretch(1, 0)
        statesLayout.setColumnStretch(2, 1)
        
        self.progress = QtGui.QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        
        self.questionBox = QtGui.QGroupBox(self)
        self.questionBox.hide()
        
        self.prompt = QtGui.QLabel(self.questionBox)
        
        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Yes | 
                                                QtGui.QDialogButtonBox.No,
                                                QtCore.Qt.Horizontal,
                                                self.questionBox)
        
        self.buttonBox.accepted.connect(self.onPromptAccept)
        self.buttonBox.rejected.connect(self.onPromptReject)
        
        questionLayout = QtGui.QVBoxLayout()
        questionLayout.addWidget(self.prompt)
        questionLayout.addWidget(self.buttonBox)
        self.questionBox.setLayout(questionLayout)
        
        layout = QtGui.QVBoxLayout()
        layout.setSpacing(10)
        
        layout.addLayout(statesLayout)
        layout.addWidget(self.progress)
        layout.addStretch(1)
        layout.addWidget(self.questionBox)
        
        self.setLayout(layout)
        
        self.worker = None
        self.__error_occured = False
    
    def initializePage(self):
        # self.field('database_configure') does not matter
        self.worker = DatabaseSetupWorker()
        self.worker.start()
        
        self.worker.stateProgress.connect(self.onStateProgressSignal)
        self.worker.stateError.connect(self.onStateErrorSignal)
        
        self.worker.stateRun.emit(self.worker.STATE_INIT)
    
    def cleanupPage(self):
        self.worker.quit()
        self.worker.wait()
        # TODO: error when opening connection in a thread and closing it in another thread.
        # TODO: error when pressing back and coming back (looks like database tables are not cleared)
        
        for iconLbl in self.stateIcons.itervalues():
            iconLbl.setPixmap(None)
        
        for detailsLbl in self.stateDetails.itervalues():
            detailsLbl.setText("")
    
    def validatePage(self):
        if self.__error_occured:
            return False
        
        if self.worker.isRunning():
            return False
        
        return True
    
    def isComplete(self):
        if self.worker.isRunning():
            return False
        else:
            return super(DatabaseSetupWizardPage, self).isComplete()
    
    def onStateErrorSignal(self, state, exception):
        
        if state == self.worker.STATE_INIT:
            message = "Could not connect to database!"
        elif state == self.worker.STATE_LOAD:
            message = "Error loading models!"
        elif state == self.worker.STATE_CREATE:
            message = "Error creating tables!"
        elif state == self.worker.STATE_TEST:
            message = "Error inserting test values!"
        else:
            message = "An error occured!"
        
        self.__error_occured = True
        
        self.setMessage(state, -1, "<b>{message}</b><br />{exception}".format(
                    message=message,
                    exception=str(exception)
        ))
        self.setProgress(self.worker.STATE_DONE, self.worker.DONE)
        self.worker.quit()
        
        self.completeChanged.emit()
    
    def onStateProgressSignal(self, state, progress):
        self.setProgress(state, progress)
        
        if state == self.worker.STATE_INIT:
            # First, connect to the database
            if progress == self.worker.START:
                self.setMessage(state, progress, "Connecting to database...")
            elif progress == self.worker.DONE:
                self.setMessage(state, progress, "Connected to database.")
                self.worker.stateRun.emit(self.worker.STATE_LOAD)
        elif state == self.worker.STATE_LOAD:
            # Second, load the models
            if progress == self.worker.START:
                self.setMessage(state, progress, "Loading models...")
            elif progress == self.worker.DONE:
                self.setMessage(state, progress, "Models loaded.")
                self.setPrompt(question="""Reconfigure Database?
This will drop the tables in the database you chose and recreate it.""",
                               onAccept=self.worker.STATE_CREATE,
                               onReject=self.worker.STATE_DONE
                               )
        elif state == self.worker.STATE_CREATE:
            # Third, create the tables
            if progress == self.worker.START:
                self.setMessage(state, progress, "Creating tables...")
            elif progress == self.worker.DONE:
                self.setMessage(state, progress, "Tables created.")
                self.setPrompt(question="""Insert test values?""",
                               onAccept=self.worker.STATE_TEST,
                               onReject=self.worker.STATE_DONE
                               )
        elif state == self.worker.STATE_TEST:
            # Fourth, insert the test values
            if progress == self.worker.START:
                self.setMessage(state, progress, "Inserting test values...")
            elif progress == self.worker.DONE:
                self.setMessage(state, progress, "Inserted test values.")
                self.worker.stateRun.emit(self.worker.STATE_DONE)
        elif state == self.worker.STATE_DONE and progress == self.worker.DONE:
            # Fifth, we are done
            self.setMessage(state, progress, "Done.")
        
        self.completeChanged.emit()
    
    def setPrompt(self, question, onAccept, onReject):
        self.questionBox.show()
        self.prompt.setText(question)
        
        self.__question_accept_callback = lambda sig=onAccept: self.worker.stateRun.emit(sig)
        self.__question_reject_callback = lambda sig=onReject: self.worker.stateRun.emit(sig) 
    
    def onPromptAccept(self):
        self.__question_accept_callback()
        
        self.questionBox.hide()
    
    def onPromptReject(self):
        self.__question_reject_callback()
        
        self.questionBox.hide()
    
    def setMessage(self, state, stage, text):
        self.stateDetails[state].setText(text)
        if stage == self.worker.START:
            pass
        elif stage == self.worker.DONE:
            icon = QtGui.QIcon.fromTheme("dialog-ok-apply")
            pixmap = icon.pixmap(16, 16)
            self.stateIcons[state].setPixmap(pixmap)
        elif stage < self.worker.START:
            icon = QtGui.QIcon.fromTheme("dialog-close")
            pixmap = icon.pixmap(16, 16)
            self.stateIcons[state].setPixmap(pixmap)
    
    def setProgress(self, state, progress):
        self.progress.setValue((state - 1 + (progress/self.worker.DONE)) * 100.0 / self.worker.STATE_DONE)
