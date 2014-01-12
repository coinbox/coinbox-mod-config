from PySide import QtCore, QtGui

import cbpos
import sys

class RawConfigDialog(QtGui.QMainWindow):
    
    def __init__(self):
        super(RawConfigDialog, self).__init__()
        
        self.mainWidget = MainWidget()
        
        self.setCentralWidget(self.mainWidget)
        
        self.setGeometry(300, 300, 350, 300)
        self.setWindowTitle('Raw Configuration Editor')

class MainWidget(QtGui.QWidget):
    
    def __init__(self):
        super(MainWidget, self).__init__()
        
        self.initUI()
        self.populate()
        
    def initUI(self):
        self.tabs = QtGui.QTabWidget(self)
        self.tabs.setTabsClosable(True)
        #self.tabs.setIconSize(QtCore.QSize(32, 32))
        #self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.onTabRemoved)

        buttonBox = QtGui.QDialogButtonBox()
        
        self.addBtn = buttonBox.addButton("Add", QtGui.QDialogButtonBox.ActionRole)
        self.addBtn.pressed.connect(self.onAddButton)
        
        self.defaultsBtn = buttonBox.addButton("Defaults", QtGui.QDialogButtonBox.RejectRole)
        self.defaultsBtn.pressed.connect(self.onDefaultsButton)
        
        self.okBtn = buttonBox.addButton(QtGui.QDialogButtonBox.Ok)
        self.okBtn.pressed.connect(self.onOkButton)
        
        self.applyBtn = buttonBox.addButton(QtGui.QDialogButtonBox.Apply)
        self.applyBtn.pressed.connect(self.onApplyButton)
        
        self.cancelBtn = buttonBox.addButton(QtGui.QDialogButtonBox.Cancel)
        self.cancelBtn.pressed.connect(self.onCancelButton)

        layout = QtGui.QVBoxLayout()
        layout.setSpacing(10)
        
        layout.addWidget(self.tabs)
        layout.addWidget(buttonBox)
        
        self.setLayout(layout)
    
    def populate(self):
        index = self.tabs.currentIndex()
        self.tabs.clear()
        for section_name, section in cbpos.config:
            self.tabs.addTab(SectionTab(section), section_name)
        
        if index<self.tabs.count():
            self.tabs.setCurrentIndex(index)
    
    def save(self):
        for i in xrange(self.tabs.count()):
            self.tabs.widget(i).save()
        cbpos.config.save()
    
    def onTabRemoved(self, index):
        section_name = self.tabs.tabText(index)
        cbpos.config[section_name] = None
        self.tabs.removeTab(index)
    
    def onDefaultsButton(self):
        cbpos.config.save_defaults(overwrite=True)
        self.parent().close()
    
    def onAddButton(self):
        dlg = AddOptionDialog(when_done=self.populate)
        dlg.exec_()
    
    def onOkButton(self):
        self.save()
        self.parent().close()
    
    def onApplyButton(self):
        self.save()
        self.populate()
    
    def onCancelButton(self):
        self.parent().close()

class SectionTab(QtGui.QWidget):
    def __init__(self, section):
        super(SectionTab, self).__init__()
        
        self.section = section
        self.initUI()
        
    def initUI(self):
        self.rows = []
        for option_name, option_value in self.section.iteritems():
            tp = None
            if isinstance(option_value, basestring):
                tp = unicode
                field = QtGui.QLineEdit()
                field.setText(option_value)
            elif isinstance(option_value, bool):
                tp = bool
                field = QtGui.QCheckBox()
                field.setChecked(option_value)
            elif isinstance(option_value, (int, float)):
                tp = int
                field = QtGui.QDoubleSpinBox()
                field.setRange(-sys.maxint, sys.maxint)
                field.setValue(option_value)
            elif isinstance(option_value, (list, tuple)):
                field = QtGui.QLineEdit()
                try:
                    field.setText(','.join(option_value))
                except TypeError:
                    # Not a list of strings
                    field.setText(','.join(repr(v) for v in option_value))
                    field.setEnabled(False)
                    tp = None
                else:
                    tp = list
            else:
                tp = None
                field = QtGui.QLineEdit()
                field.setText(repr(option_value))
                field.setEnabled(False)
            btn = QtGui.QPushButton("-")
            row = [option_name, type(option_value), field, btn]
            btn.pressed.connect(lambda r=row: self.onRemoveButton(r))
            self.rows.append(row)

        form = QtGui.QFormLayout()
        form.setSpacing(10)

        for row in self.rows:
            layout = QtGui.QHBoxLayout()
            [layout.addWidget(f) for f in row[2:]]
            form.addRow(row[0], layout)
        self.setLayout(form)
    
    def save(self):
        for option_name, tp, field, btn in self.rows:
            if not field.isEnabled(): continue
            if tp is unicode:
                self.section[option_name] = field.text()
            elif tp is bool:
                self.section[option_name] = field.isChecked()
            elif tp is int:
                self.section[option_name] = field.value()
            elif tp is list:
                self.section[option_name] = field.text().split(',')
            else:
                # TODO: what should we do with these?
                #self.section[option_name] = eval(field.text())
                pass
    
    def onRemoveButton(self, row):
        option_name, tp, field, btn = row
        self.section[option_name] = None
        field.setEnabled(False)
        btn.setEnabled(False)

class AddOptionDialog(QtGui.QDialog):
    
    def __init__(self, when_done=None):
        super(AddOptionDialog, self).__init__()
        
        self.when_done = when_done if when_done is not None else lambda: None
        
        self.section = QtGui.QLineEdit()
        self.option = QtGui.QLineEdit()
        self.value = QtGui.QLineEdit()
        
        buttonBox = QtGui.QDialogButtonBox()
        
        self.okBtn = buttonBox.addButton(QtGui.QDialogButtonBox.Ok)
        self.okBtn.pressed.connect(self.onOkButton)
        
        self.cancelBtn = buttonBox.addButton(QtGui.QDialogButtonBox.Cancel)
        self.cancelBtn.pressed.connect(self.onCancelButton)
        
        form = QtGui.QFormLayout()
        form.setSpacing(10)
        
        form.addRow("Section", self.section)
        form.addRow("Option", self.option)
        form.addRow("Value", self.value)
        form.addRow(buttonBox)
        
        self.setLayout(form)
    
    def onOkButton(self):
        section, option, value = [field.text() for field in (self.section, self.option, self.value)]
        cbpos.config[section, option] = value
        cbpos.config.save()
        self.close()
        self.when_done()
    
    def onCancelButton(self):
        self.close()
