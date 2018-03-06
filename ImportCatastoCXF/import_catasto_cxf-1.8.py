# -*- coding: utf-8 -*-
"""
/***************************************************************************
 import_catasto
                                 A QGIS plugin
 import dati catastali
                              -------------------
        begin                : 2015-02-24
        copyright            : (C) 2015 by A.R. Gaeta / Vertical Srl
        email                : ar_gaeta@yahoo.it
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
# Importiamo la GUI interface di QGis:
from qgis.gui import *
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from import_catastodialog import import_catastoDialog


class import_catasto:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # Riferimento all'area mamma
        self.canvas = self.iface.mapCanvas() #CHANGE
        # questo tool di QGIS emette un QgsPoint ad ogni click del mouse sull'area mappa
        self.clickTool = QgsMapToolEmitPoint(self.canvas)
        # initialize plugin directory
        self.plugin_dir = QFileInfo(QgsApplication.qgisUserDbFilePath()).path() + "/python/plugins/import_catasto"
        # initialize locale
        localePath = ""
        locale = QSettings().value("locale/userLocale").toString()[0:2]

        if QFileInfo(self.plugin_dir).exists():
            localePath = self.plugin_dir + "/i18n/import_catasto_" + locale + ".qm"

        if QFileInfo(localePath).exists():
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = import_catastoDialog()

    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(
            QIcon(":/plugins/import_catasto/icon.png"),
            u"import dati catastali", self.iface.mainWindow())
        # connect the action to the run method
        QObject.connect(self.action, SIGNAL("triggered()"), self.run)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u"&import_catasto", self.action)

        #result = QObject.connect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.handleMouseDown)
        #Al caricamento del plugin in QGis, appare un messaggio di testo. Se è TRUE va tutto bene.
        #QMessageBox.information( self.iface.mainWindow(),"Info", "connect = %s"%str(result) )

        # connette la funzione di selezione al segnale canvasClicked
        #result = QObject.connect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.selectFeature)
        #QMessageBox.information( self.iface.mainWindow(),"Info", "connect = %s"%str(result) )

        #Connettiamo un elemento della GUI di QtDesigner ad un comando:
        QObject.connect(self.dlg.ui.chkActivate, SIGNAL("stateChanged(int)"), self.changeActive)

        #Proviamo a vedere se risponde al dirBrowse_btn che è un toolButton che ho messo io:
        #QObject.connect(self.dlg.ui.dirBrowse_btn, SIGNAL("clicked()"), self.choose_file)
        #dirBrowse_btn.clicked.connect(selectFile)
        QObject.connect(self.dlg.ui.fileBrowse_btn, SIGNAL("clicked()"), self.selectFile)

        #Selezioniamo una directory:
        QObject.connect(self.dlg.ui.dirBrowse_btn, SIGNAL("clicked()"), self.selectDir)

        #Con questo pulsante cerchiamo di captare le variabili fin qui impostate - in futuro questo tasto dovrebbe lanciare poi il mio codice python:
        QObject.connect(self.dlg.ui.importBtn, SIGNAL("clicked()"), self.importCXF)


    def selectFile(self):
        #Pulisco quanto scritto nella dirBrowse che è una lineEdit - vedi import_catastodialog.py:
        self.dlg.clearFileBrowser()
        #E gli scrivo il path scelto - OK!!
        #self.dlg.setFileBrowser( QFileDialog.getOpenFileName(None, 'Open Directory', '', 'LOG file (*.log)') )
        self.dlg.setFileBrowser( QFileDialog.getOpenFileName(None, 'Open Directory', '', 'CXF file (*.cxf)') )

    def selectDir(self):
        #Pulisco quanto scritto nella dirBrowse che è una lineEdit - vedi import_catastodialog.py:
        self.dlg.clearDirBrowser()
        #Solo per le directory:
        self.dlg.setDirBrowser( QFileDialog.getExistingDirectory(None, 'Open working directory', '', QFileDialog.ShowDirsOnly) )

    def importCXF(self):
        #mi connetto alla linea di testo che contiene il percorso della directoory ad esempio - OK!!
        text = self.dlg.ui.dirBrowse_txt.text()
        QMessageBox.information( self.iface.mainWindow(),"Info", "connect = %s"%str(text) )

    def choose_file(self):
        #questa non funziona forse passo troppi argomenti??
        file_name = QFileDialog.getOpenFileName(self, "Open Data File", "", "CSV data files (*.csv)")


    def handleMouseDown(self, point, button):
        self.dlg.clearTextBrowser()
        self.dlg.setTextBrowser( str(point.x()) + " , " +str(point.y()) )
        #QMessageBox.information( self.iface.mainWindow(),"Info", "X,Y = %s,%s" % (str(point.x()),str(point.y())) )

    def changeActive(self,state):
         if (state==Qt.Checked):
                 # connessione al segnale click
                 QObject.connect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.handleMouseDown)
                 # connessione della funzione di selezione al segnale canvasClicked
                 QObject.connect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.selectFeature)
         else:
                 # disconnessione dal segnale click
                 QObject.disconnect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.handleMouseDown)
                 # disconnessione della funzione di selezione dal segnale canvasClicked
                 QObject.disconnect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.selectFeature)

    def selectFeature(self, point, button):
           QMessageBox.information( self.iface.mainWindow(),"Info", "in selectFeature function" )
           # risultati filtrati in base ad un rettangolo
           pntGeom = QgsGeometry.fromPoint(point)
           # buffer di 2 unità di mappa
           pntBuff = pntGeom.buffer( (self.canvas.mapUnitsPerPixel() * 2),0)
           rect = pntBuff.boundingBox()
           # acquisisce layer corrente e fornitore
           cLayer = self.canvas.currentLayer()
           selectList = []
           if cLayer:
                   provider = cLayer.dataProvider()
                   feat = QgsFeature()
                   # crea la dichiarazione di selezione
                   provider.select([],rect) # gli argomenti significano: no attributi, filtro rettangolo per limitare il numero di elementi
                   while provider.nextFeature(feat):
                           # se la geometria selezionata interseca il nostro punto, inseriscila in una lista
                           if feat.geometry().intersects(pntGeom):
                                   selectList.append(feat.id())
    
                   # effettua la selezione
                   cLayer.setSelectedFeatures(selectList)
           else:
                   QMessageBox.information( self.iface.mainWindow(),"Info", "No layer currently selected in TOC" )

    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu(u"&import_catasto", self.action)
        self.iface.removeToolBarIcon(self.action)

    # run method that performs all the real work
    def run(self):
        # attiviamo il clickTool
        self.canvas.setMapTool(self.clickTool)
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result == 1:
            # do something useful (delete the line containing pass and
            # substitute with your code)
            pass
