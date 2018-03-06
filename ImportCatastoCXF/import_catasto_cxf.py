# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ImportCatastoCXF
                                 A QGIS plugin
 Importa dati catastali geometrici da file CXF
                              -------------------
        begin                : 2016-07-06
        git sha              : $Format:%H$
        copyright            : (C) 2015 by A.R.Gaeta/Vertical Srl
        email                : ar_gaeta@yahoo.it
        version              : 0.6
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from import_catasto_cxf_dockwidget import ImportCatastoCXFDockWidget
import os.path

#Importo i miei script dedicati e altre cose utili per il catasto:
from optparse import OptionParser
from cxf import parse_foglio
from cxf_ogr import write_foglio
from os.path import basename as path_basename
import os
from osgeo import ogr

#importo alcune librerie per gestione dei layer caricati
#from qgis.core import *
from qgis.core import QgsVectorLayer, QgsMapLayerRegistry
#from qgis.utils import iface
#from qgis.gui import *

'''
PER FAR FUNZIONARE I DRIVER POSTGRESQL HO COPIATO gdal110.dll DA 'C:\OSGeo4W\bin' NEL PERCORSO DEL MIO PLUGIN CIOE' 'C:\ARPA-2015\fatti_miei\AndreaMGOS-lavori\QGis_custom_plugins\ImportCatastoCXF' ED ANCHE IN 'C:\Users\riccardo\.qgis2\python\plugins\ImportCatastoCXF'
'''

'''
Ottimizzazioni:
- il messaggio di buona riuscita della conversione in realta' e' slegato dalla effettiva buona riuscita...
- restituire come messaggio anche una statistica sui dati caricati, che normalmente il codice python restituisce da cxf.py --> "print key, value"
'''

class ImportCatastoCXF:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'ImportCatastoCXF_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = ImportCatastoCXFDockWidget()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&ImportCatastoCXF')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'ImportCatastoCXF')
        self.toolbar.setObjectName(u'ImportCatastoCXF')
        
        #Implemento alcune azioni sui miei pulsanti
        #APRI FILE
        self.dlg.fileBrowse_txt.clear()
        self.dlg.fileBrowse_btn.clicked.connect(self.select_input_file)
        
        #SELEZIONA CARTELLA
        self.dlg.dirBrowse_txt.clear()
        self.dlg.dirBrowse_btn.clicked.connect(self.select_output_dir)
        
        #AZIONO PULSANTE PERSONALIZZATO:
        #self.dlg.importBtn.setEnabled(True);
        self.dlg.importBtn.clicked.connect(self.import_action)
        
        #AZIONO pulsante per TESTARE CONNESSIONE AL DB:
        self.dlg.testBtn.clicked.connect(self.test_connection)
        
        #Verifico la destinazione (DB o SHP) escludendo la doppia scelta:
        self.dlg.chkShp.clicked.connect(self.choose_dest_shp)
        self.dlg.chkDB.clicked.connect(self.choose_dest_db)
        
    #--------------------------------------------------------------------------

    def activate_import(self):
        dirname_check = self.dlg.dirBrowse_txt.text()
        filename_check = self.dlg.fileBrowse_txt.text()
        db_check = self.dlg.testAnswer.text()
        if (filename_check and (dirname_check or db_check) ):
            self.dlg.importBtn.setEnabled(True);
        else:
            self.dlg.importBtn.setEnabled(False);
            
    def choose_dest_shp(self):
        shp_value = self.dlg.chkShp.isChecked()
        if (shp_value==True):
            self.dlg.chkDB.setChecked(False)
    
    def choose_dest_db(self):
        db_value = self.dlg.chkDB.isChecked()
        if (db_value==True):
            self.dlg.chkShp.setChecked(False)

    def select_input_file(self):
        filename = QFileDialog.getOpenFileName(self.dlg, "Load CXF file","", '*.cxf')
        self.dlg.fileBrowse_txt.setText(filename)
        #Verifico di avere tutte le informazioni necessarie per decidere se abilitare o meno il pulsante IMPORT
        self.activate_import()
        
    def select_output_dir(self):
        dirname = QFileDialog.getExistingDirectory(self.dlg, "Open output directory","", QFileDialog.ShowDirsOnly)
        self.dlg.dirBrowse_txt.setText(dirname)
        #Verifico di avere tutte le informazioni necessarie per decidere se abilitare o meno il pulsante IMPORT
        self.activate_import()
    
    def test_connection(self):
        self.dlg.testAnswer.clear()
        self.dlg.txtFeedback.clear()
        userDB = self.dlg.usrDB.text()
        pwdDB = self.dlg.pwdDB.text()
        hostDB = self.dlg.hostDB.text()
        portDB = self.dlg.portDB.text()
        nameDB = self.dlg.nameDB.text()
        schemaDB = self.dlg.schemaDB.text()
        dest_dir = "dbname=%s host=%s port=%s user=%s password=%s active_schema=%s" % (nameDB, hostDB, portDB, userDB, pwdDB, schemaDB)
        param_conn = "PG:%s" % (dest_dir)
        test_conn = ogr.Open(param_conn)
        if (test_conn==None):
            debug_text = "Connessione al DB fallita!! Rivedere i dati e riprovare"
            self.dlg.txtFeedback.setText(debug_text)
            self.dlg.importBtn.setEnabled(False);
        else:
            debug_text = "OK!"
            self.dlg.testAnswer.setText(debug_text)
            #Verifico di avere tutte le informazioni necessarie per decidere se abilitare o meno il pulsante IMPORT
            self.activate_import()
        
    def import_action(self):
        self.dlg.txtFeedback.setText('Attendi.....')
        chkbox_value = self.dlg.chkActivate.isChecked() #button per aggiungere il layer su mappa
        chkbox_str = '%s' % (chkbox_value)
        
        #Verifico se ho scelto di salvare su DB o su SHP:
        shp_value = self.dlg.chkShp.isChecked()
        db_value = self.dlg.chkDB.isChecked()
        
        input_cxf = self.dlg.fileBrowse_txt.text()
        #input_cxf = r'C:\ARPA-2015\fatti_miei\AndreaMGOS-lavori\QGis_custom_plugins\dati_cxf-orbassano\G087_003800.CXF'
        basename = path_basename(input_cxf).upper()
        foglio = parse_foglio(input_cxf[:-4])
        
        #Al momento non riuscendo ad escluderli, do precedenza a shp:
        if (shp_value==True):        
            output_dir = self.dlg.dirBrowse_txt.text()
            #output_dir = r'C:\Users\riccardo\Desktop'
            dest_dir = '%s\\%s' % (output_dir, basename[:-4])
            #foglio = parse_foglio(input_cxf[:-4])
            #Comando dinamico per scrivere su cartella scelta dall'utente:
            write_foglio(foglio, dest_dir, point_borders=False, format_name='ESRI Shapefile')
            
        elif (db_value==True):
            #Prova per scrivere su DB PostgreSQL in percorso fisso - IN SVILUPPO:
            userDB = self.dlg.usrDB.text()
            pwdDB = self.dlg.pwdDB.text()
            hostDB = self.dlg.hostDB.text()
            portDB = self.dlg.portDB.text()
            nameDB = self.dlg.nameDB.text()
            schemaDB = self.dlg.schemaDB.text()
            dest_dir = "dbname=%s host=%s port=%s user=%s password=%s active_schema=%s" % (nameDB, hostDB, portDB, userDB, pwdDB, schemaDB)
            param_conn = "PG:%s" % (dest_dir)
            #param_conn = PG:"dbname=tucatuca host=localhost port=5432 user=postgres password=ARTURO active_schema=public"
            write_foglio(foglio, param_conn, point_borders=False, format_name='PostgreSQL')
        
        '''
        Aggiungo il layer su mappa: funzione NON IMPLEMENTATA in quanto non so il NOME DEL LAYER GENERATO a prescindere!! Al momento carica gli SHP ma sicuramente penso sia impossibile riuscire a caricare i dati eventualmente caricati su DB.
        '''
        if (chkbox_value==True):
            pedice = "%s_%s_%s" % (foglio['CODICE COMUNE'], foglio['NUMERO FOGLIO'], foglio['CODICE SVILUPPO'])
            layer_path = '%s' % (dest_dir) #'C:\\Users\\riccardo\\Desktop\\G087_003800'
            
            #metodo di caricamento con QgsVectorLayer
            layer_bordi_name = 'CATASTO_BORDI_%s' % (pedice)
            layer_testi_name = 'CATASTO_TESTI_%s' % (pedice)
            layer_fiduciali_name = 'CATASTO_FIDUCIALI_%s' % (pedice)
            layer_simboli_name = 'CATASTO_SIMBOLI_%s' % (pedice)
            #carico elementi in mappa:
            layer_bordi = QgsVectorLayer(layer_path+"\\"+layer_bordi_name+".shp", layer_bordi_name, "ogr")
            layer_testi = QgsVectorLayer(layer_path+"\\"+layer_testi_name+".shp", layer_testi_name, "ogr")
            layer_fiduciali = QgsVectorLayer(layer_path+"\\"+layer_fiduciali_name+".shp", layer_fiduciali_name, "ogr")
            layer_simboli = QgsVectorLayer(layer_path+"\\"+layer_simboli_name+".shp", layer_simboli_name, "ogr")
            lista_layer_to_load=[layer_simboli, layer_fiduciali, layer_testi, layer_bordi]
            QgsMapLayerRegistry.instance().addMapLayers(lista_layer_to_load)
            #assegno uno stile - inmm se carico in LatLon, altrimenti lo stile piu' corretto e' senza pedice ed e' in unita mappa:
            layer_bordi.loadNamedStyle(os.getenv("HOME")+'/.qgis2/python/plugins/ImportCatastoCXF/qml_base/catasto_bordi_inmm.qml')
            layer_testi.loadNamedStyle(os.getenv("HOME")+'/.qgis2/python/plugins/ImportCatastoCXF/qml_base/catasto_testi_inmm.qml')
            layer_fiduciali.loadNamedStyle(os.getenv("HOME")+'/.qgis2/python/plugins/ImportCatastoCXF/qml_base/catasto_fiduciali_inmm.qml')
            layer_simboli.loadNamedStyle(os.getenv("HOME")+'/.qgis2/python/plugins/ImportCatastoCXF/qml_base/catasto_simboli_inmm.qml')
            
            '''
            #Questo metodo di caricamento in mappa e' piu' diretto ma non consente di applicare uno stile
            layer_name_arr = ['CATASTO_BORDI_', 'CATASTO_TESTI_', 'CATASTO_FIDUCIALI_', 'CATASTO_SIMBOLI_', 'CATASTO_LINEE_']
            for elemento in layer_name_arr:
                layername = '%s%s' % (elemento, pedice)
                layer_full_path = '%s\%s.shp' % (layer_path, layername)
                #carico elementi in mappa:
                layer = self.iface.addVectorLayer(layer_full_path, layername, "ogr")
                #assegno uno stile qml - NON FUNZIONA!
                if (elemento == 'CATASTO_BORDI_'):
                    layer.loadNamedStyle('qml_base/catasto_bordi.qml')
                elif (elemento == 'CATASTO_TESTI_'):
                    layer.loadNamedStyle('qml_base/catasto_testi.qml')
                elif (elemento == 'CATASTO_FIDUCIALI_'):
                    layer.loadNamedStyle('qml_base/catasto_fiduciali.qml')
                elif (elemento == 'CATASTO_SIMBOLI_'):
                    layer.loadNamedStyle('qml_base/catasto_simboli.qml')
                
                if not layer:
                    print "Layer failed to load!"
            '''
            

        self.dlg.txtFeedback.setText('Conversione avvenuta con successo!!')
        
        #self.dlg.txtFeedback.setText(os.getcwd()) #per sapere il percorso dei plugin: C:\PROGRA~1\QGISWI~1\bin
        

    #--------------------------------------------------------------------------

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('ImportCatastoCXF', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/ImportCatastoCXF/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Import Catasto CXF'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Import Catasto CXF'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        
        #resetto i campi di testo
        self.dlg.fileBrowse_txt.setText('')
        self.dlg.dirBrowse_txt.setText('')
        self.dlg.testAnswer.setText('')
        self.dlg.txtFeedback.setText('')
        self.dlg.chkActivate.setCheckState(False)
        
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
            '''
            Porto questa parte sotto l'azione del pulsante IMPORT
            input_cxf = self.dlg.fileBrowse_txt.text()
            basename = path_basename(input_cxf).upper()
            output_dir = self.dlg.dirBrowse_txt.text()
            dest_dir = '%s\\%s' % (output_dir, basename[:-4])
            foglio = parse_foglio(input_cxf[:-4])
            #write_foglio(foglio, output_dir+'\\'+basename[:-4], point_borders=False, format_name='ESRI Shapefile')
            #a quanto pare scritta ocsi' non riconosce correttamente la directory...
            write_foglio(foglio, dest_dir, point_borders=False, format_name='ESRI Shapefile')
            #ERRORE!!
            #File "C:/Users/riccardo/.qgis2/python/plugins\ImportCatastoCXF\ogr.py", line 169, in write_foglio     bordi.CreateField(f_comune)
            #AttributeError: 'NoneType' object has no attribute 'CreateField'
            #QUESTO ERRORE E' DOVUTO AL FATTO CHE NON RIESCE A CREARE LO SHP, PER QUESTO DEVI RIVEDERE LA SINTASSI DELLA DIRECTORY DOVE SALVARLO.
            '''
            #Una volta corretto questo pero' mi da un altro errore:
            '''
            File "C:/Users/riccardo/.qgis2/python/plugins\ImportCatastoCXF\ogr.py", line 214, in write_foglio
                feat.SetField('COMUNE', foglio['CODICE COMUNE'])
            File "C:\PROGRA~1\QGISWI~1\apps\Python27\lib\site-packages\osgeo\ogr.py", line 2700, in SetField
                return _ogr.Feature_SetField(self, *args)
            NotImplementedError: Wrong number of arguments for overloaded function 'Feature_SetField'.
            Possible C/C++ prototypes are:
                SetField(OGRFeatureShadow *,int,char const *)
                SetField(OGRFeatureShadow *,char const *,char const *)
                SetField(OGRFeatureShadow *,int,int)
                SetField(OGRFeatureShadow *,char const *,int)
                SetField(OGRFeatureShadow *,int,double)
                SetField(OGRFeatureShadow *,char const *,double)
                SetField(OGRFeatureShadow *,int,int,int,int,int,int,int,int)
                SetField(OGRFeatureShadow *,char const *,int,int,int,int,int,int,int)
            '''

            #SOLUZIONE: a quanto pare devi specificare la decodifica del tipo di campo ad esempio specificando in cxf_ogr.py:
            #feat.SetField('COMUNE', foglio['CODICE COMUNE'].encode('utf-8'))
            #In ogni caso mi da poi questo errore:
            '''
            Traceback (most recent call last):
            File "C:/Users/riccardo/.qgis2/python/plugins\ImportCatastoCXF\import_catasto_cxf.py", line 229, in run
                write_foglio(foglio, output_dir, point_borders=False, format_name='ESRI Shapefile')
            File "C:/Users/riccardo/.qgis2/python/plugins\ImportCatastoCXF\cxf_ogr.py", line 282, in write_foglio
                testi = ds.CreateLayer(nome_layer, target_srs, wkbPoint, papszOptions)
            File "C:\PROGRA~1\QGISWI~1\apps\Python27\lib\site-packages\osgeo\ogr.py", line 602, in CreateLayer
                return _ogr.DataSource_CreateLayer(self, *args, **kwargs)
            TypeError: in method 'DataSource_CreateLayer', argument 2 of type 'char const *'
            '''
            #SOLUZIONE: occorre anche qui inserire una decodifica per il nome da dare al layer, ad esempio:
            #nome_layer = nome_layer_not_utf.encode('utf-8')
