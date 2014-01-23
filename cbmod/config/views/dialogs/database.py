from PySide import QtGui, QtCore

import Queue
from sqlalchemy import exc

import cbpos
from cbpos.database import Profile, Driver, \
                        ProfileNotFoundError, DriverNotFoundError

logger = cbpos.get_logger(__name__)

class DatabaseConfigWorker(QtCore.QThread):
    stateChange = QtCore.Signal((int, int), (int, int, object))
    stateRun = QtCore.Signal(int)
    
    STATE_INIT, STATE_LOAD, STATE_CREATE, STATE_TEST, STATE_DONE = range(1, 6)
    START, ERROR, DONE = range(3)
    
    def __init__(self, parent=None):
        super(DatabaseConfigWorker, self).__init__(parent)
        self.__state_queue = Queue.Queue()
        self.exiting = False
        self.stateRun.connect(self.onStateRunSignal)
    
    def run(self):
        while not self.exiting:
            try:
                state = self.__state_queue.get(False)
            except Queue.Empty:
                QtCore.QThread.msleep(100)
                continue
            else:
                self.runState(state)
    
    def onStateRunSignal(self, state):
        self.__state_queue.put(state)
    
    def runState(self, state):
        self.stateChange.emit(state, self.START)
        
        if state == self.STATE_INIT:
            # Start the database AFTER potential changes in the configuration
            try:
                cbpos.database.init()
            except (ImportError, exc.SQLAlchemyError) as e:
                # Either the required db backend is not installed
                # Or there is a database error (connection, etc.)
                self.stateChange[int, int, object].emit(state, self.ERROR, e)
                return
            except Exception as e:
                # Unexpected error occured
                self.stateChange[int, int, object].emit(state, self.ERROR, e)
                return
        elif state == self.STATE_LOAD:
            # Load database models of every module
            try:
                cbpos.modules.load_database()
            except Exception as e:
                self.stateChange[int, int, object].emit(state, self.ERROR, e)
                logger.exception("Could not load database")
                return
        elif state == self.STATE_CREATE:
            # Flush the chosen database and recreate the structure
            try:
                cbpos.modules.config_database()
            except Exception as e:
                self.stateChange[int, int, object].emit(state, self.ERROR, e)
                logger.exception("Could not create database tables")
                return
        elif state == self.STATE_TEST:
            # Add initial testing values
            try:
                cbpos.modules.config_test_database()
            except Exception as e:
                self.stateChange[int, int, object].emit(state, self.ERROR, e)
                logger.exception("Could not insert test database values")
                return
        elif state == self.STATE_DONE:
            self.exiting = True
        
        self.stateChange.emit(state, self.DONE)

class DatabaseConfigDialog(QtGui.QMainWindow):
    def __init__(self):
        super(DatabaseConfigDialog, self).__init__()
        
        self.mainWidget = MainWidget(self)
        self.setCentralWidget(self.mainWidget)
        self.statusBar().showMessage('Select the database profile to use and configure it.')
        
        self.setGeometry(300, 300, 350, 300)
        self.setWindowTitle('Database Configuration')
        
        self.thread = None
        
        self.mainWidget.populate()
    
    def continueProcess(self):
        self.mainWidget = DatabaseProgressWidget(self)
        self.setCentralWidget(self.mainWidget)
        self.statusBar().showMessage('Configuring database...')
        
        self.thread = DatabaseConfigWorker()
        self.thread.start()
        
        self.thread.stateChange[int, int].connect(self.onStateChangeSignal)
        self.thread.stateChange[int, int, object].connect(self.onStateChangeSignal)
        self.thread.stateRun.emit(self.thread.STATE_INIT)
    
    def closeEvent(self, event):
        if self.thread is None:
            event.accept()
        else:
            self.thread.exiting = True
            if self.thread.wait(300): # Wait 3 times the delay in the main loop just to be safe
                event.accept()
            else:
                event.ignore()
    
    def __handleWorkerError(self, message, exception=None):
        self.mainWidget.setMessage(message + "\n\n" + str(exception))
        self.mainWidget.setProgress(self.thread.STATE_DONE)
        self.thread.exiting = True
    
    def onStateChangeSignal(self, state, stage, exception=None):
        self.mainWidget.setProgress(state)
        if state == self.thread.STATE_INIT:
            # First, connect to the database
            if stage == self.thread.START:
                self.mainWidget.setMessage("Connecting to database...")
            elif stage == self.thread.ERROR:
                self.__handleWorkerError("Could not connect to database!", exception)
            elif stage == self.thread.DONE:
                self.mainWidget.setMessage("Connected to database.")
                self.thread.stateRun.emit(self.thread.STATE_LOAD)
        elif state == self.thread.STATE_LOAD:
            # Second, load the models
            if stage == self.thread.START:
                self.mainWidget.setMessage("Loading models...")
            elif stage == self.thread.ERROR:
                self.__handleWorkerError("Error loading models!", exception)
            elif stage == self.thread.DONE:
                self.mainWidget.setMessage("Models loaded.")
                reply = QtGui.QMessageBox.question(self, "Database configuration",
                    """Reconfigure Database?
This will drop the tables in the database you chose and recreate it.""",
                    QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
                )
                if reply == QtGui.QMessageBox.Yes:
                    self.thread.stateRun.emit(self.thread.STATE_CREATE)
                else:
                    self.thread.stateRun.emit(self.thread.STATE_DONE)
        elif state == self.thread.STATE_CREATE:
            # Third, create the tables
            if stage == self.thread.START:
                self.mainWidget.setMessage("Creating tables...")
            elif stage == self.thread.ERROR:
                self.__handleWorkerError("Error creating tables!", exception)
            elif stage == self.thread.DONE:
                self.mainWidget.setMessage("Tables created.")
                reply = QtGui.QMessageBox.question(self, "Database configuration",
                    """Insert test values?""",
                    QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
                )
                if reply == QtGui.QMessageBox.Yes:
                    self.thread.stateRun.emit(self.thread.STATE_TEST)
                else:
                    self.thread.stateRun.emit(self.thread.STATE_DONE)
        elif state == self.thread.STATE_TEST:
            # Fourth, insert the test values
            if stage == self.thread.START:
                self.mainWidget.setMessage("Inserting test values...")
            elif stage == self.thread.ERROR:
                self.__handleWorkerError("Error inserting test values!", exception)
            elif stage == self.thread.DONE:
                self.mainWidget.setMessage("Inserted test values.")
                self.thread.stateRun.emit(self.thread.STATE_DONE)
        elif state == self.thread.STATE_DONE and stage == self.thread.DONE:
            # Fifth, we are done
            self.mainWidget.setMessage("Done.")
            self.mainWidget.setProgress(self.thread.STATE_DONE)

class MainWidget(QtGui.QWidget):
    def __init__(self, parent=None, flags=0):
        super(MainWidget, self).__init__(parent, flags)
        
        self.profiles = QtGui.QComboBox()
        self.profiles.activated[int].connect(self.onProfileActivated)
        self.profiles.editTextChanged.connect(self.onProfileTextChanged)
        
        self.addBtn = QtGui.QPushButton('+')
        self.addBtn.pressed.connect(self.onAddButton)
        self.removeBtn = QtGui.QPushButton('-')
        self.removeBtn.pressed.connect(self.onRemoveButton)
        
        self.forms = {}
        
        self.tabs = QtGui.QTabWidget()
        drivers = Driver.get_all()
        drivers.sort(key=lambda d: d.name)
        for driver in drivers:
            self.forms[driver.name] = form = DriverForm(driver, self)
            self.tabs.addTab(form, driver.display)

        buttonBox = QtGui.QDialogButtonBox()
        
        self.okBtn = buttonBox.addButton(QtGui.QDialogButtonBox.Ok)
        self.okBtn.pressed.connect(self.onOkButton)
        
        self.applyBtn = buttonBox.addButton(QtGui.QDialogButtonBox.Apply)
        self.applyBtn.pressed.connect(self.onApplyButton)
        
        self.cancelBtn = buttonBox.addButton(QtGui.QDialogButtonBox.Cancel)
        self.cancelBtn.pressed.connect(self.onCancelButton)

        profileLayout = QtGui.QHBoxLayout()
        profileLayout.addWidget(self.profiles, 1)
        profileLayout.addWidget(self.addBtn)
        profileLayout.addWidget(self.removeBtn)

        form = QtGui.QFormLayout()
        form.setSpacing(10)
        
        rows = [[profileLayout],
                [self.tabs],
                [buttonBox]
                ]

        [form.addRow(*row) for row in rows]
        self.setLayout(form)
    
    def populate(self, profile_name=None):
        self._last_profile = None
        self._last_profile_values = None
        self._last_profile_name = None
        self._tmp_profile_name = None
        self.profiles.clear()
        for p in Profile.get_all():
            self.profiles.addItem(p.name, p)
        try:
            if profile_name is None:
                profile = Profile.get_used()
            else:
                profile = Profile.get(profile_name)
        except ProfileNotFoundError:
            QtGui.QMessageBox.information(self, 'Edit Profile',
                "Profile not found in configuration, using default.", QtGui.QMessageBox.Ok)
            self.setProfile(Profile.get('default'))
        else:
            self.setProfile(profile)
    
    def onProfileActivated(self, index):
        self._last_profile_name = self._tmp_profile_name
        profile = self.profiles.itemData(index)
        self.setProfile(profile)
    
    def onProfileTextChanged(self, profile_name):
        self._tmp_profile_name = self._last_profile_name
        self._last_profile_name = profile_name
    
    def onAddButton(self):
        # Generate a new unique name for the profile
        n = 0
        profile_name = "profile{}".format(n)
        while True:
            try:
                Profile.get(profile_name)
            except ProfileNotFoundError:
                break
            else:
                n += 1
                profile_name = "profile{}".format(n)
        
        # Create and save the new (empty) profile
        profile = Profile(name=profile_name, driver=Driver.get('sqlite'))
        profile.save()
        
        # Prompt to save the changes to the current profile
        self.saveProfile(auto=True)
        
        # Re-populate the profiles list with the new one selected
        self.populate(profile_name)
    
    def onRemoveButton(self):
        if not self._last_profile.editable:
            return
        self._last_profile.delete()
        self.populate()
    
    def onOkButton(self):
        self.saveProfile(auto=False)
        self._last_profile.use()
        self.window().continueProcess()
    
    def onApplyButton(self):
        self.saveProfile(auto=False)
        self._last_profile.use()
        self.populate()
    
    def onCancelButton(self):
        self.window().close()
    
    def changed(self, other=None):
        if other is not None and self._last_profile == other:
            return True
        if self._last_profile_name is not None and self._last_profile_name != self._last_profile.name:
            return True
        form = self.tabs.currentWidget()
        if form.values() != self._last_profile_values:
            return True
        return False
    
    def setProfile(self, profile):
        if self._last_profile and self.changed(other=profile):
            if not self.saveProfile(auto=True):
                return
            self.populate()
        else:
            #TODO: self.profiles.findData(profile) is not working...
            index = self.profiles.findText(profile.name)
            self.profiles.setCurrentIndex(index)
        for f in self.forms.itervalues():
            f.clear()
        form = self.forms[profile.driver.name]
        self.tabs.setCurrentWidget(form)
        form.setProfile(profile)
        
        self.tabs.setEnabled(profile.editable)
        self.profiles.setEditable(profile.editable)
        self.removeBtn.setEnabled(profile.editable)
        
        self._last_profile = profile
        self._tmp_profile_name = profile.name
        self._last_profile_name = profile.name
        self._last_profile_values = form.values()
    
    def saveProfile(self, auto=False):
        changed = self.changed()
        if changed and auto:
            reply = QtGui.QMessageBox.question(self, 'Save Profile?',
                                               "Changes to this profile have not been saved. Save now?", QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.Cancel)
            if reply == QtGui.QMessageBox.Cancel:
                self.profiles.setEditText(self._last_profile_name)
                return False
            elif reply == QtGui.QMessageBox.No:
                return True
        if self._last_profile_name != self._last_profile.name and self._last_profile_name in Profile.get_all_names():
            QtGui.QMessageBox.information(self, 'Save Profile',
                "A profile with this name already exists. Choose another name.", QtGui.QMessageBox.Ok)
            return False
        form = self.tabs.currentWidget()
        self._last_profile.name = self._last_profile_name
        return form.save(self._last_profile)

class DriverForm(QtGui.QWidget):
    def __init__(self, driver, parent=None, flags=0):
        super(DriverForm, self).__init__(parent, flags)
        
        self.driver = driver
        self.rows = self.driver.form.copy()
        self.initUI()
        
    def initUI(self):
        if "host" in self.rows:
            self.rows["host"]["widget"] = QtGui.QLineEdit()
        if "port" in self.rows:
            self.rows["port"]["widget"] = widget = QtGui.QSpinBox()
            widget.setRange(0, 65535)
            widget.setSingleStep(1)
        if "username" in self.rows:
            self.rows["username"]["widget"] = QtGui.QLineEdit()
        if "password" in self.rows:
            self.rows["password"]["widget"] = widget = QtGui.QLineEdit()
            widget.setEchoMode(QtGui.QLineEdit.Password)
        if "database" in self.rows:
            self.rows["database"]["widget"] = QtGui.QLineEdit()
        if "query" in self.rows:
            self.rows["query"]["widget"] = QtGui.QLineEdit()

        form = QtGui.QFormLayout()
        form.setSpacing(10)

        rows_order = ('host', 'port', 'username', 'password', 'database', 'query')
        for field in rows_order:
            if field in self.rows:
                row = self.rows[field]
            else:
                continue
            row["checkbox"] = checkbox = QtGui.QCheckBox(row["label"])
            checkbox.setEnabled(not row["required"])
            checkbox.stateChanged.connect(lambda state, widget=row["widget"]: widget.setEnabled(bool(state)))
            row["widget"].setEnabled(row["required"])
            self.setField(field, None)
            form.addRow(checkbox, row["widget"])
        self.setLayout(form)

    def setField(self, field, value):
        if field not in self.rows:
            return
        self.rows[field]["checkbox"].setChecked(self.rows[field]["required"] or bool(value))
        value = value if value is not None else self.rows[field]["default"]
        if field in ('host', 'username', 'password', 'database', 'query'):
            self.rows[field]["widget"].setText(value)
        elif field == 'port':
            self.rows["port"]["widget"].setValue(int(value) if value is not None else 0)
    
    def getField(self, field):
        if field not in self.rows:
            return None
        if not self.rows[field]["checkbox"].isChecked():
            return None
        if field in ('host', 'username', 'password', 'database', 'query'):
            return self.rows[field]["widget"].text()
        elif field == 'port':
            return unicode(self.rows["port"]["widget"].value())

    def setProfile(self, profile):
        if profile.driver != self.driver:
            return
        for field in self.rows:
            self.setField(field, getattr(profile, field))

    def clear(self):
        for field in self.rows:
            self.setField(field, None)

    def values(self):
        v = {}
        v["driver"] = self.driver
        for field in self.rows:
            v[field] = self.getField(field)
        return v
    
    def save(self, profile):
        profile.driver = self.driver
        for field in self.rows:
            setattr(profile, field, self.getField(field))
        profile.save()
        return True

class DatabaseProgressWidget(QtGui.QWidget):
    def __init__(self, parent=None, flags=0):
        super(DatabaseProgressWidget, self).__init__(parent, flags)
        
        self.text = QtGui.QLabel(self)
        self.text.setWordWrap(True)
        
        self.progress = QtGui.QProgressBar(self)
        self.progress.setRange(0, DatabaseConfigWorker.STATE_DONE)
        self.progress.setTextVisible(False)
        
        buttonBox = QtGui.QDialogButtonBox()
        
        self.closeBtn = buttonBox.addButton(QtGui.QDialogButtonBox.Close)
        self.closeBtn.pressed.connect(self.onCloseButton)
        
        layout = QtGui.QVBoxLayout()
        layout.setSpacing(10)
        
        layout.addStretch(1)
        layout.addWidget(self.text)
        layout.addWidget(self.progress)
        layout.addStretch(1)
        layout.addWidget(buttonBox)
        
        self.setLayout(layout)
    
    def setMessage(self, text):
        self.text.setText(text)
        self.window().statusBar().showMessage(text.splitlines()[0])
    
    def setProgress(self, progress):
        self.progress.setValue(progress)
        self.closeBtn.setEnabled(progress == self.progress.maximum())
    
    def onCloseButton(self):
        self.window().close()
