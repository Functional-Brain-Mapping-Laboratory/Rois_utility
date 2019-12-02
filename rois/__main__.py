import sys
from PyQt5.QtWidgets import QApplication
from .GUI import RoisToolbox


if __name__ == '__main__':
    modern = False
    app = QApplication(sys.argv)
    RoisToolbox = RoisToolbox(QApplication=app)
    RoisToolbox.show()
    sys.exit(app.exec_())
