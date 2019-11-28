# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QAction, QMessageBox, QInputDialog, QLineEdit, QDialog, QPushButton, QLabel, QProgressBar, QComboBox
from PyQt5.QtCore import QFileInfo, Qt, QProcess, QVariant
from qgis.core import QgsProject, QgsMapLayer, QgsField, QgsProcessingContext, QgsProcessingUtils, QgsVectorDataProvider, QgsFeature, QgsVectorLayer
from qgis.gui import QgsFileWidget, QgsBusyIndicatorDialog
from qgis.utils import iface
import threading 
import requests
import json
import pandas as pd



def classFactory(iface):
    return MinimalPlugin(iface)


class MinimalPlugin:
    def __init__(self, iface):
        #Defino un widget y le añado un label, un input para los archivos y un boton. A todos los objeto


        self.iface = iface
        self.capa = ""
        self.campo = ""
        self.indexCampo = ""
        self.nombreCapa = ""
        self.rutaFinal = ""
        self.rutaArchivo = ""
        self.rutaCorrecta = False
        self.cerrarPlugin = 0
        self.errorNormalizando = 0

        #Widget de Capas
        self.seleccionarCapa = QDialog()
        self.seleccionarCapa.setFixedSize(385, 100)
        self.seleccionarCapa.setSizeGripEnabled(False)
        self.seleccionarCapa.setWindowFlags(Qt.WindowMinimizeButtonHint|Qt.WindowMaximizeButtonHint) 

        self.labelIndicacion = QLabel(self.seleccionarCapa)
        self.labelIndicacion.setText('Seleccione la capa a normalizar')
        self.labelIndicacion.move(30,10)

        self.comboColumna = QComboBox(self.seleccionarCapa)
        self.comboColumna.move(30,30)
        self.comboColumna.resize(325, 30)

        self.botonCancelar = QPushButton(self.seleccionarCapa)
        self.botonCancelar.setText('Cancelar')
        self.botonCancelar.move(190,65)
        self.botonCancelar.clicked.connect(self.cancelarAccion)

        self.botonAceptar = QPushButton(self.seleccionarCapa)
        self.botonAceptar.setText('Aceptar')
        self.botonAceptar.move(275,65)
        self.botonAceptar.clicked.connect(self.aceptarCapa)

        #Widget de Columna
        self.seleccionarColumna = QDialog()
        self.seleccionarColumna.setFixedSize(385, 100)
        self.seleccionarColumna.setSizeGripEnabled(False)
        self.seleccionarColumna.setWindowFlags(Qt.WindowMinimizeButtonHint|Qt.WindowMaximizeButtonHint) 

        self.labelIndicacion2 = QLabel(self.seleccionarColumna)
        self.labelIndicacion2.setText('Seleccione el campo con la direccion')
        self.labelIndicacion2.move(30,10)

        self.comboColumna2 = QComboBox(self.seleccionarColumna)
        self.comboColumna2.move(30,30)
        self.comboColumna2.resize(325, 30)

        self.botonCancelar2 = QPushButton(self.seleccionarColumna)
        self.botonCancelar2.setText('Cancelar')
        self.botonCancelar2.move(190,65)
        self.botonCancelar2.clicked.connect(self.cancelarAccion)

        self.botonAceptar2 = QPushButton(self.seleccionarColumna)
        self.botonAceptar2.setText('Aceptar')
        self.botonAceptar2.move(275,65)
        self.botonAceptar2.clicked.connect(self.aceptarColumna)

        #Mensajes de error
        self.errorProyecto = QMessageBox();
        self.errorProyecto.setText("Abra un proyecto con capas cargas e intente nuevamente");

        #Widget de carga
        self.main_window = iface.mainWindow()
        self.widgetNormalizando = QgsBusyIndicatorDialog("Normalizando...", self.main_window, fl=Qt.WindowFlags())
        self.widgetNormalizando.setModal(True)

        #Mensaje Pre Normalizacion (creado y utilizado para solucionar el bug con el widget carga)
        self.avisoPreNormalizacion = QMessageBox()
        self.avisoPreNormalizacion.setText("Porfavor, no manipule el archivo CSV mientras se esta normalizando")
        
    def initGui(self):
        #Defino el boton con el cual se ejecutara el Plugin
        self.action = QAction(u'Normalizar Direcciones', self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        #En caso de que el plugin sea desinstalado, con esta funcion se eliminara todo su rastro de la interfaz
        self.iface.removeToolBarIcon(self.action)
        del self.action


    def aceptarCapa(self):
        self.nombreCapa = self.comboColumna.currentText()
        self.capa = QgsProject.instance().mapLayersByName(self.nombreCapa)
        self.comboColumna.clear()
        self.seleccionarCapa.accept()

    def aceptarColumna(self):

        self.campo = self.comboColumna2.currentText()
        self.indexCampo = self.comboColumna2.currentIndex()
        self.seleccionarColumna.accept()
        self.comboColumna2.clear()

    def cancelarAccion(self):
        self.cerrarPlugin = 1
        self.comboColumna2.clear()
        self.seleccionarColumna.reject()
        self.comboColumna.clear()
        self.seleccionarCapa.reject()

    def normalizandoArchivo(self, capaSeleccionada):

        self.rutaArchivo = iface.activeLayer().dataProvider().dataSourceUri()
        posicionArchivo = self.rutaArchivo.find('?type=')

        if self.rutaArchivo.find('file://') == -1:
            self.rutaFinal = self.rutaArchivo[:posicionArchivo]
        else:   
            self.rutaFinal = self.rutaArchivo[7:posicionArchivo]

        if self.rutaFinal.find('.csv') == -1:
            self.errorNormalizando = -2
            return

        posicionSeparador = self.rutaArchivo.find('delimiter=') + 10
        separador = self.rutaArchivo[posicionSeparador:posicionSeparador + 1]
        try:
            df = pd.read_csv(self.rutaFinal,sep=separador)
        except:
                self.errorNormalizando = -3
                return

        server = 'https://servicios.usig.buenosaires.gob.ar/normalizar/'
        server2 = 'https://ws.usig.buenosaires.gob.ar/datos_utiles'
        headers = {
        'Content-Type': 'application/json'
        }

        for i in range (0, len(df)):
            try:
                url = server + '?direccion=' + str(df.loc[i,self.campo])+'&geocodificar=TRUE'
                response = requests.request('GET', url, headers = headers, allow_redirects=False)
                resultado_du = response.json()
                df.loc[i,'coord_x'] = resultado_du['direccionesNormalizadas'][0]['coordenadas']['x']
                df.loc[i,'coord_y'] = resultado_du['direccionesNormalizadas'][0]['coordenadas']['y']
                df.loc[i,'direccion_normalizada'] = resultado_du['direccionesNormalizadas'][0]['direccion']
                #En base a las coordenadas conseguidas en la primera API, el resto de la información se consigue en la segunda API
                url2 = server2 + '?x=' + str(df.loc[i,'coord_x'])+ '&y=' + str(df.loc[i,'coord_y'])
                response2 = requests.request('GET', url2, headers = headers, allow_redirects=False)
                resultado_du2 = response2.json()
                df.loc[i,'comuna'] = resultado_du2['comuna']
                df.loc[i,'barrio'] = resultado_du2['barrio']
                df.loc[i,'comisaria'] = resultado_du2['comisaria']
                df.loc[i,'area_hospitalaria'] = resultado_du2['area_hospitalaria']
                df.loc[i,'region_sanitaria'] = resultado_du2['region_sanitaria']

                df.loc[i,'status_geocode'] = 'OK'
            except:
                df.loc[i,'status_geocode'] = 'Error'
                self.errorNormalizando = self.errorNormalizando + 1
                continue
 
        if len(df) == self.errorNormalizando:
            self.errorNormalizando = -1
        else:
            posC = self.rutaFinal.find('.csv')
            self.rutaFinal = self.rutaFinal[:posC] + "Normalizado.csv"
            df.reset_index().to_csv(self.rutaFinal,header=True,index=False)
            print(self.rutaFinal)

            
    def barraCargando(self):
        self.widgetNormalizando.exec()

    def run(self):
        self.errorNormalizando = 0

        listaCapas = QgsProject.instance().mapLayers().values()

        for cursorCapa in listaCapas:
            if cursorCapa.type() == QgsMapLayer.VectorLayer: 
                self.comboColumna.addItem( cursorCapa.name(), cursorCapa ) 

        if self.comboColumna.currentText() == "":
            self.errorProyecto.exec()
            return 1

        self.seleccionarCapa.exec()

        if self.cerrarPlugin == 1:
            self.cerrarPlugin = 0
            return 

        #Seteo el layer con el cual voy a trabajar
        iface.setActiveLayer(self.capa[0])
        capaSeleccionada = iface.activeLayer()
 
        #Guardo todos los nombres de los campos en una variable
        camposCapa = capaSeleccionada.fields()   
        nombresCamposCapa = [campoCapa.name() for campoCapa in camposCapa]

        self.comboColumna2.addItems(list(nombresCamposCapa))
        self.comboColumna2.setCurrentIndex(1)

        self.seleccionarColumna.exec()   
        
        if self.cerrarPlugin == 1:
            self.cerrarPlugin = 0
            return

        t1 = threading.Thread(target=self.normalizandoArchivo, args=(capaSeleccionada,))
        t2 = threading.Thread(target=self.barraCargando,args=())
        
        t2.start()
        self.avisoPreNormalizacion.exec()
        t1.start()  
        t1.join() 
        self.widgetNormalizando.accept()

        if self.errorNormalizando < 0:
            if self.errorNormalizando == -1:  
                QMessageBox.information(None, u'Normalizador de Direcciones', u'El campo seleccionado no corresponde a las direcciones. \nVerifique que el campo seleccionado contenga tanto la dirección como la altura.')
            if self.errorNormalizando == -2:  
                QMessageBox.information(None, u'Normalizador de Direcciones', u'La capa seleccionada no pertenece a un archivo CSV')
            if self.errorNormalizando == -3:  
                QMessageBox.information(None, u'Normalizador de Direcciones', u'La capa pertenece a un archivo que contiene caracteres especiales.\nCambie el nombre del archivo para normalizar')
        
        else:
            #Se borra la capa desactualizada
            #QgsProject.instance().removeMapLayer(capaSeleccionada)
            #Se carga la capa actualizada
            uri = "file://" + self.rutaFinal + "?delimiter={}&xField={}&yField={}".format(",", "coord_x", "coord_y")
            vlayer = QgsVectorLayer(uri, self.nombreCapa + "Normalizado" , "delimitedtext")

            QMessageBox.information(None, u'Normalizador de Direcciones', u'El archivo CSV se ha normalizado.\nHubo errores en ' + str(self.errorNormalizando) + ' registros.\nEl Archivo se encuentra en la ruta:\n' + str(self.rutaFinal) + '.')

            #csvActualizado = QgsVectorLayer(self.rutaFinal, self.nombreCapa + "Normalizado", "ogr")
            QgsProject.instance().addMapLayer(vlayer)
      

