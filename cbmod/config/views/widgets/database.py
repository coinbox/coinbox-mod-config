from PySide import QtCore, QtGui

import Queue
from sqlalchemy import exc

import cbpos

from cbpos.modules import all_loaders

logger = cbpos.get_logger(__name__)

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

class DatabaseSetupWorker(QtCore.QThread):
    stateProgress = QtCore.Signal(int, float)
    stateError = QtCore.Signal(int, object)
    stateRun = QtCore.Signal(int)
    
    STATE_NONE, STATE_INIT, STATE_LOAD, STATE_CREATE, STATE_TEST, STATE_DONE = range(6)
    START, FINISH, DONE = 0, 99, 100
    
    class Communicator(QtCore.QObject):
        def __init__(self, worker):
            super(DatabaseSetupWorker.Communicator, self).__init__()
            self.worker = worker
        
        def runState(self, state):
            self.worker.stateProgress.emit(state, self.worker.START)
            
            if state == self.worker.STATE_INIT:
                # Start the database AFTER potential changes in the configuration
                try:
                    cbpos.database.init()
                except (ImportError, exc.SQLAlchemyError) as e:
                    # Either the required db backend is not installed
                    # Or there is a database error (connection, etc.)
                    self.worker.stateError.emit(state, e)
                    return
                except Exception as e:
                    # Unexpected error occured
                    self.worker.stateError.emit(state, e)
                    return
            elif state == self.worker.STATE_LOAD:
                # Load database models of every module
                try:
                    loaders = all_loaders()
                    count_loaders = float(len(loaders))
                    for i, mod in enumerate(loaders):
                        logger.debug('Loading DB models for %s', mod.base_name)
                        models = mod.load_models()
                        self.worker.stateProgress.emit(state, self.worker.FINISH * (i/count_loaders))
                except Exception as e:
                    self.worker.stateError.emit(state, e)
                    logger.exception("Could not load database")
                    return
            elif state == self.worker.STATE_CREATE:
                # Flush the chosen database and recreate the structure
                try:
                    logger.debug('Clearing database...')
                    cbpos.database.clear()
                    self.worker.stateProgress.emit(state, self.worker.FINISH * 0.5)
                    logger.debug('Creating database...')
                    cbpos.database.create()
                except Exception as e:
                    self.worker.stateError.emit(state, e)
                    logger.exception("Could not create database tables")
                    return
            elif state == self.worker.STATE_TEST:
                # Add initial testing values
                try:
                    loaders = all_loaders()
                    count_loaders = float(len(loaders))
                    for i, mod in enumerate(loaders):
                        logger.debug('Adding test values for %s', mod.base_name)
                        mod.test_models()
                        self.worker.stateProgress.emit(state, self.worker.FINISH * (i/count_loaders))
                except Exception as e:
                    self.worker.stateError.emit(state, e)
                    logger.exception("Could not insert test database values")
                    return
            elif state == self.worker.STATE_DONE:
                self.worker.quit()
            
            self.worker.stateProgress.emit(state, self.worker.DONE)
    
    def __init__(self, parent=None):
        super(DatabaseSetupWorker, self).__init__(parent)
        self.on_main = DatabaseSetupWorker.Communicator(self)
        
        self.on_worker = DatabaseSetupWorker.Communicator(self)
        self.on_worker.moveToThread(self)
        
        self.stateRun.connect(self.on_worker.runState)
    
    def run(self):
        return self.exec_()
