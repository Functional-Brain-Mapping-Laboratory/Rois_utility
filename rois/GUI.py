import os

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QDialogButtonBox,
    QApplication,
    QFileDialog,
    QLineEdit,
    QPushButton,
    QErrorMessage,
    QMessageBox,
)
from PyQt5.QtCore import Qt
import nibabel as nib
import pycartool

from .utils import open_lut, create_region_of_interest, save_rois


class RoisToolbox(QDialog):
    def __init__(self, parent=None, QApplication=None):
        super().__init__(parent)
        self.setWindowTitle(" Creating Rois")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        # Init
        self.spi = None
        self.atlas = None
        self.data_lut = None
        self.palette = None
        self.output_directory = None
        # SPI file
        grid.addWidget(QLabel("Source space:"), 0, 0)
        self.QLineEdit_spi = QLineEdit()
        grid.addWidget(self.QLineEdit_spi, 0, 1)
        self.QPushButton_spi = QPushButton("Open")
        self.QPushButton_spi.clicked.connect(self.open_spi)
        grid.addWidget(self.QPushButton_spi, 0, 3)
        # MRI file
        grid.addWidget(QLabel("Atlas mask:"), 1, 0)
        self.QLineEdit_atlas = QLineEdit()
        grid.addWidget(self.QLineEdit_atlas, 1, 1)
        self.QPushButton_atlas = QPushButton("Open")
        self.QPushButton_atlas.clicked.connect(self.open_atlas)
        grid.addWidget(self.QPushButton_atlas, 1, 3)
        # SPI file
        grid.addWidget(QLabel("LookUp Table:"), 2, 0)
        self.QLineEdit_lut = QLineEdit()
        grid.addWidget(self.QLineEdit_lut, 2, 1)
        self.QPushButton_lut = QPushButton("Open")
        self.QPushButton_lut.clicked.connect(self.open_lut)
        grid.addWidget(self.QPushButton_lut, 2, 3)
        # outputdir
        grid.addWidget(QLabel("Output directory:"), 3, 0)
        self.QLineEdit_output_dir = QLineEdit()
        self.output_directory = os.getcwd()
        self.QLineEdit_output_dir.setText(self.output_directory)
        grid.addWidget(self.QLineEdit_output_dir, 3, 1)
        self.QPushButton_open_output_dir = QPushButton("Open")
        self.QPushButton_open_output_dir.clicked.connect(self.open_output_directory)
        grid.addWidget(self.QPushButton_open_output_dir, 3, 3)
        # run
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        grid.addWidget(self.buttonbox, 4, 1, 1, 4)
        self.buttonbox.accepted.connect(self.run)
        self.buttonbox.rejected.connect(self.reject)
        self.buttonbox.setEnabled(False)
        vbox.addLayout(grid)

    def data_changed(self):
        if any(
            x is None
            for x in [
                self.spi,
                self.atlas,
                self.data_lut,
                self.palette,
                self.output_directory,
            ]
        ):
            self.buttonbox.setEnabled(False)
        else:
            self.buttonbox.setEnabled(True)

    def open_spi(self):
        filter = "spi(*.spi)"
        fname, _ = QFileDialog.getOpenFileName(self, "Open Source Space", filter=filter)
        if fname:
            self.fname_spi = fname
            self.spi = pycartool.spi.read_spi(self.fname_spi)
        else:
            self.fname_spi = None
        self.QLineEdit_spi.setText(self.fname_spi)
        self.data_changed()
        return ()

    def open_atlas(self):
        filter = "Nifti(*.nii)"
        fname, _ = QFileDialog.getOpenFileName(self, "Open Atlas", filter=filter)
        if fname:
            self.fname_atlas = fname
            self.atlas = nib.load(self.fname_atlas)
        else:
            self.fname_atlas = None
        self.QLineEdit_atlas.setText(self.fname_atlas)
        self.data_changed()
        return ()

    def open_lut(self):
        filter = "LookUp Table(*.txt)"
        fname, _ = QFileDialog.getOpenFileName(self, "Open LUT", filter=filter)
        if fname:
            self.fname_lut = fname
            self.data_lut, self.palette = open_lut(self.fname_lut)
        else:
            self.fname_lut = None

        self.QLineEdit_lut.setText(self.fname_lut)
        self.data_changed()
        return ()

    def open_output_directory(self):
        dirname = QFileDialog.getExistingDirectory(self, "Output directory")
        if dirname:
            self.output_directory = dirname
        else:
            self.output_directory = None
        self.QLineEdit_output_dir.setText(self.output_directory)
        self.data_changed()
        return ()

    def run(self):
        try:
            base_name_spi = os.path.basename(self.fname_spi)
            base_name_spi = os.path.splitext(base_name_spi)[0]

            base_name_atlas = os.path.basename(self.fname_atlas)
            base_name_atlas = os.path.splitext(base_name_atlas)[0]

            base_name = base_name_atlas + "__" + base_name_spi
            base_name = os.path.join(self.output_directory, base_name)

            fname_rois = base_name + ".rois"
            fname_source_mri = base_name + ".nii"
            fname_rois_spi = base_name + "_rois.spi"
            QApplication.setOverrideCursor(Qt.WaitCursor)
            rois, img, rois_spi = create_region_of_interest(
                self.atlas, self.spi, self.data_lut, self.palette
            )
            save_rois(rois, fname_rois)
            img.to_filename(fname_source_mri)
            rois_spi.save(fname_rois_spi)
            QApplication.restoreOverrideCursor()
            self.QMessageBox_finnish = QMessageBox()
            self.QMessageBox_finnish.setWindowTitle("Finished")
            self.QMessageBox_finnish.setText("Done.")
            self.QMessageBox_finnish.exec_()
        except Exception as e:
            QApplication.restoreOverrideCursor()
            self.QErrorMessage = QErrorMessage()
            print(e)
            self.QErrorMessage.showMessage(str(e))
