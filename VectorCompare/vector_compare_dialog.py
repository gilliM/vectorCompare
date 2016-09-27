# -*- coding: utf-8 -*-
"""
/***************************************************************************
 VectorCompareDialog
                                 A QGIS plugin
 Comparaison of polygon layer - first for classifcation purposes
                             -------------------
        begin                : 2016-09-27
        git sha              : $Format:%H$
        copyright            : (C) 2016 by EOInt
        email                : gillian.milani@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic, QtCore
from qgis.core import QgsMapLayerRegistry, QgsCoordinateReferenceSystem, QgsVectorLayer, QgsField, QgsFeatureRequest
import processing
import copy
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from pandas.tools.plotting import table
from pandas import DataFrame
from matplotlib.colors import ListedColormap
import matplotlib.path as mpath
import matplotlib.patches as mpatches
from pyplot_widget import pyPlotWidget
import math

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'vector_compare_dialog_base.ui'))


class VectorCompareDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent = None):
        """Constructor."""
        super(VectorCompareDialog, self).__init__(parent)
        self.setupUi(self)
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.targetLayerCB.currentIndexChanged.connect(self.changeTargetLayer)
        self.referenceLayerCB.currentIndexChanged.connect(self.changeReferenceLayer)

    def reset_iface(self, iface):
        self.iface = iface
        self.actualizeLayers()

    def actualizeLayers(self):
        self.targetLayerCB.clear()
        self.referenceLayerCB.clear()
        for layer in QgsMapLayerRegistry.instance().mapLayers().values():
            if layer.type() == 0:  # vector
                if layer.geometryType() == 0 or layer.geometryType() == 2:
                    self.targetLayerCB.addItem(layer.name())
                    self.referenceLayerCB.addItem(layer.name())

    def changeTargetLayer(self):
        self.attributeTargetCB.clear()
        layer_name = self.targetLayerCB.currentText()
        layer = None
        for lyr in QgsMapLayerRegistry.instance().mapLayers().values():
            if lyr.name() == layer_name:
                layer = lyr
                for field in layer.fields():
                    name_field = field.name()
                    self.attributeTargetCB.addItem(name_field)
                break

    def changeReferenceLayer(self):
        self.attributeReferenceCB.clear()
        layer_name = self.referenceLayerCB.currentText()
        layer = None
        for lyr in QgsMapLayerRegistry.instance().mapLayers().values():
            if lyr.name() == layer_name:
                layer = lyr
                for field in layer.fields():
                    name_field = field.name()
                    self.attributeReferenceCB.addItem(name_field)
                break

    def run(self):
        targetName = self.targetLayerCB.currentText()
        referenceName = self.referenceLayerCB.currentText()
        attributeTargetName = self.attributeTargetCB.currentText()
        attributeReferenceName = self.attributeReferenceCB.currentText()

        for lyr in QgsMapLayerRegistry.instance().mapLayers().values():
            if lyr.name() == targetName: targetLayer = lyr
            if lyr.name() == referenceName: referenceLayer = lyr

        #  QgsMapLayerRegistry.instance().addMapLayer(mem_layer)
        output = processing.runalg("qgis:intersection", referenceLayer, targetLayer, None)
        layer = self.iface.addVectorLayer(output["OUTPUT"], "intersection", "ogr")
        if layer.featureCount() == 0:
            QtGui.QMessageBox.about(self, "No intersection", "No intersection exists between the two layers\nPlease check the selected layers and their projections.")

            return
        self.printPdf(layer, attributeTargetName, attributeReferenceName)

    def printPdf(self, layer, attributeTargetName, attributeReferenceName):
        if attributeTargetName == attributeReferenceName:
            attributeTargetName = attributeTargetName + "_2"

        uniquevalues = [];
        provider = layer.dataProvider()
        fields = provider.fields()
        id = fields.indexFromName(attributeReferenceName)
        valuesReference = provider.uniqueValues(id)
        id = fields.indexFromName(attributeTargetName)
        valuesTarget = provider.uniqueValues(id)

        presentValues = copy.copy(valuesReference)
        for value in valuesTarget:
            if value not in presentValues:
                presentValues.append(value)

        present_class = np.sort(presentValues)
        n_class = len(present_class)

        areas = [ feat.geometry().area() for feat in layer.getFeatures() ]
        field = QgsField("area", QtCore.QVariant.Double)
        provider.addAttributes([field])
        layer.updateFields()
        idx = layer.fieldNameIndex('area')
        for area in areas:
            new_values = {idx : float(area)}
            provider.changeAttributeValues({areas.index(area):new_values})

        tot_res = np.zeros((n_class, n_class))

        for i in range(n_class):
            for j in range(n_class):
                request = QgsFeatureRequest().setFilterExpression(u""""%s" = %s AND "%s" = %s """ % (attributeTargetName, present_class[i], attributeReferenceName, present_class[j]))
                it = layer.getFeatures(request)
                for feature in it:
                    area = feature.attributes()[idx]
                    if isinstance(area, float):
                        tot_res[j, i] += area



        tot_col = np.reshape(np.sum(tot_res, 0), (1, n_class))
        tot_row = np.reshape(np.sum(tot_res, 1), (n_class, 1))

        p_row = np.nan_to_num(np.diag(tot_res) / tot_row.T)
        p_col = np.nan_to_num(np.diag(tot_res) / tot_col)

        outputFile = '/Users/gmilani/dev/temp/pdf_changemap.pdf'
        with PdfPages(outputFile) as pdf:
            c_plot = pyPlotWidget()
            ax = c_plot.figure.add_subplot(1, 1, 1)
            ax.set_title('Confusion Matrix')
            ax.axis('off')

            headers = map(str, present_class)
            headers.append('Prod. Acc.')

            rowLabels = map(str, present_class)
            rowLabels.append('User Acc.')

            t1 = np.concatenate((tot_res, np.reshape(p_row, (-1, 1))), 1)

            tpt_col1 = np.concatenate((p_col, np.reshape([np.nan], (1, 1))), 1)
            t1 = np.concatenate((t1, tpt_col1), 0)

            overallAccuracy = np.array(np.trace(tot_res), dtype = np.float32) / np.sum(tot_res)
            B = np.sum(np.sum(tot_res, axis = 0) / (float(tot_res.shape[0]) * np.sum(tot_res)))
            kappa = (overallAccuracy - B) / (1 - B)

            average_precision = self.round_sigfigs(np.average(p_row), 3)
            average_recall = self.round_sigfigs(np.average(p_col), 3)
            f1_score = self.round_sigfigs(2 * (average_precision * average_recall) / (average_precision + average_recall), 3)

            for i in range(t1.shape[0]):
                for j in range(t1.shape[1]):
                    t1[i, j] = self.round_sigfigs(t1[i, j], 3)

            df = DataFrame(t1, columns = headers, dtype = np.float32)
            table(ax, df, rowLabels = rowLabels, loc = 'upper right', colWidths = [1.0 / (n_class + 2)] * (n_class + 1))
            c_plot.canvas.draw()



            txt1 = "Overall accuracy: %s     Kappa: %s" % (self.round_sigfigs(overallAccuracy, 3), "Kappa: %s" % self.round_sigfigs(kappa, 3))
            txt2 = "Precision: %s     Recall: %s     F1-Score: %s" % (average_precision, average_recall, f1_score)
            txt3 = """The overall accuracy represents the total number of correctly classified areas divided by
            the total of reference area."""
            txt4 = """The kappa statistic is a metric that compares an observed Accuracy with an expected Accuracy.
            It is more robust than the overall accuracy"""
            txt5 = """The producer accuracy (Prod. Acc) is the fraction of correctly classified areas with respect
            to the reference areas"""
            txt6 = """The user accuracy (User Acc.) is the fraction of  correctly classified areas to areas
            classified as it in the target layer."""
            txt7 = """The precision is the average of the producer accuracies.
The recall is the average of the user accuracies"""
            txt9 = """The F1-score is the harmonic mean of precision and recall. It removes part of the bias
            introduced by the unbalanced presence of certain classes."""

            c_plot.figure.text(.1, .5, txt1, fontsize = 15)
            c_plot.figure.text(.1, .4, txt2, fontsize = 15)
            c_plot.figure.text(.1, .3, txt3, fontsize = 10)
            c_plot.figure.text(.1, .25, txt4, fontsize = 10)
            c_plot.figure.text(.1, .2, txt5, fontsize = 10)
            c_plot.figure.text(.1, .15, txt6, fontsize = 10)
            c_plot.figure.text(.1, .15, txt6, fontsize = 10)
            c_plot.figure.text(.1, .1, txt7, fontsize = 10)
            c_plot.figure.text(.1, .05, txt9, fontsize = 10)
            pdf.savefig(c_plot.figure)

            url = QtCore.QUrl('file://' + outputFile)
            QtGui.QDesktopServices.openUrl(url)


    def round_sigfigs(self, num, sig_figs):
        num = np.nan_to_num(num)
        if num != 0:
            return round(num, -int(math.floor(math.log10(abs(num))) - (sig_figs - 1)))
        else:
            return 0  # Can't take the log of 0
