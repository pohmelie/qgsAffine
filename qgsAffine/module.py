import pathlib
import itertools

from PyQt5 import uic
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon
from qgis.core import QgsProject, QgsWkbTypes, QgsPoint
from qgis.gui import QgsMessageViewer


class UIValue:

    def __set_name__(self, owner, name):
        self.name = f"spin{name.capitalize()}"

    def __get__(self, instance, owner):
        return getattr(instance.ui, self.name).value()

    def __set__(self, instance, value):
        getattr(instance.ui, self.name).setValue(value)


class Affine:

    a = UIValue()
    b = UIValue()
    tx = UIValue()
    c = UIValue()
    d = UIValue()
    ty = UIValue()

    def __init__(self, ui):
        self.ui = ui


class AffineUI:

    def __init__(self, iface):
        self.ui = uic.loadUi(self.here / "ui.ui")
        self.iface = iface
        self.affine_namespace = Affine(self.ui)

    @property
    def here(self):
        return pathlib.Path(__file__).parent

    @property
    def project(self):
        return QgsProject.instance()

    def initGui(self):
        icon = QIcon(str(self.here / "icon.svg"))
        self.action = QAction(icon, "Affine Transformation...", self.iface.mainWindow())
        self.action.setWhatsThis("Configuration for test plugin")
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu("&Geoprocessing Tools", self.action)

        self.ui.pushButtonRun.clicked.connect(self.affine)
        self.ui.pushButtonInvert.clicked.connect(self.invert)
        self.ui.pushButtonClose.clicked.connect(self.finish)

    def unload(self):
        self.iface.removePluginVectorMenu("&Geoprocessing Tools", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        self.ui.comboBoxLayer.clear()
        for name, layer in self.project.mapLayers().items():
            if layer.type() == 0:
                self.ui.comboBoxLayer.addItem(name)
        self.ui.show()

    def affine(self):
        warn = QgsMessageViewer()
        layer_name = self.ui.comboBoxLayer.currentText()
        vlayer = self.project.mapLayers().get(layer_name)
        if vlayer is None:
            warn.setMessageAsPlainText("Select a layer to transform")
            warn.showMessage()
            return
        if not vlayer.isEditable():
            warn.setMessageAsPlainText("Layer not in edit mode")
            warn.showMessage()
            return
        if self.ui.radioButtonWholeLayer.isChecked():
            vlayer.selectAll()
        if vlayer.geometryType() == QgsWkbTypes.PolygonGeometry:
            start = 1
        else:
            start = 0
        v = self.affine_namespace
        for fid in vlayer.selectedFeatureIds():
            feature = vlayer.getFeature(fid)
            geometry = feature.geometry()
            for i in itertools.count(start=start):
                vertex = geometry.vertexAt(i)
                if vertex == QgsPoint(0, 0):
                    break
                # matrix form: x' = A x + b
                # x' = a x + b y + tx
                # y' = c x + d y + ty
                newx = v.a * vertex.x() + v.b * vertex.y() + v.tx
                newy = v.c * vertex.x() + v.d * vertex.y() + v.ty
                vlayer.moveVertex(newx, newy, fid, i)
        self.iface.mapCanvas().zoomToSelected()

    def invert(self):
        # matrix form: x' = A x + b
        # --> x = A^-1 x' - A^-1 b
        # A^-1 = [d -b; -c a] / det A
        # only valid if det A = a d - b c != 0
        v = self.affine_namespace
        det = v.a * v.d - v.b * v.c
        if det == 0:
            warn = QgsMessageViewer()
            warn.setMessageAsPlainText("Transformation is not invertable")
            warn.showMessage()
            return
        v.a, v.b, v.c, v.d = v.d / det, -v.b / det, -v.c / det, v.a / det
        v.tx, v.ty = -v.a * v.tx - v.b * v.ty, -v.c * v.tx - v.d * v.ty

    def finish(self):
        self.ui.close()
