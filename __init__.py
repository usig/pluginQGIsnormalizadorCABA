# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QAction, QMessageBox, QInputDialog, QLineEdit, QDialog, QPushButton, QLabel, QProgressBar, QComboBox
from PyQt5.QtCore import QFileInfo, Qt, QProcess, QVariant
from qgis.core import Qgis,QgsProject, QgsMapLayer, QgsField, QgsProcessingContext, QgsProcessingUtils, QgsVectorDataProvider, QgsFeature, QgsVectorLayer, QgsApplication, QgsTask, QgsMessageLog
from qgis.gui import QgsFileWidget, QgsBusyIndicatorDialog
from qgis.utils import iface
import threading
import requests
import json
import pandas as pd
import random
from time import sleep


def classFactory(iface):
    return normalizadorCABA(iface)


class normalizadorCABA():
    def __init__(self, iface):
        #Defino un widget y le añado un label, un input para los archivos y un boton. A todos los objeto

        self.iface = iface
        self.capa = ""
        self.campo = ""
        self.indexCampo = ""
        self.nombreCapa = ""
        self.rutaFinal = ""
        self.rutaArchivo = ""
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
        self.action = QAction(u'Geocodificador CABA', self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        #En caso de que el plugin sea desinstalado, con esta funcion se eliminara todo su rastro de la interfaz
        self.iface.removeToolBarIcon(self.action)
        del self.action


    def aceptarCapa(self):
        #Se carga en una variable el nombre de la capa que está seleccionada en un combobox
        self.nombreCapa = self.comboColumna.currentText()
        self.capa = QgsProject.instance().mapLayersByName(self.nombreCapa)
        self.comboColumna.clear()
        self.seleccionarCapa.accept()

    def aceptarColumna(self):
        #Se carga en una variable el nombre de la columna que esta seleccionada en un combobox
        self.campo = self.comboColumna2.currentText()
        self.indexCampo = self.comboColumna2.currentIndex()
        self.seleccionarColumna.accept()
        self.comboColumna2.clear()

    def cancelarAccion(self):
        #Cierra cualquiera de los widgets que esté abierto
        self.cerrarPlugin = 1
        self.comboColumna2.clear()
        self.seleccionarColumna.reject()
        self.comboColumna.clear()
        self.seleccionarCapa.reject()

    def run(self):
        #Inicializo la variable en 0 por si el plugin ya fue utilizado
        self.errorNormalizando = 0
        #Cargo la lista con las capas cargadas
        listaCapas = QgsProject.instance().mapLayers().values()
        #Añado las capas a un combobox
        for cursorCapa in listaCapas:
            if cursorCapa.type() == QgsMapLayer.VectorLayer:
                self.comboColumna.addItem( cursorCapa.name(), cursorCapa )
        #Si no se cargo ninguna capa, abro un widget
        if self.comboColumna.currentText() == "":
            self.errorProyecto.exec()
            return 1
        #Abro el selector de capas
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
        #Añado los items del combo de columnas
        self.comboColumna2.addItems(list(nombresCamposCapa))
        self.comboColumna2.setCurrentIndex(1)
        #Abro el selector de columnas
        self.seleccionarColumna.exec()  
        if self.cerrarPlugin == 1:
            self.cerrarPlugin = 0
            return
        #Se procede a normalizar
        self.normalizando()
        #Una vez normalizado, con este método se verifican los errores y se guarda la capa          normalizada
        self.postNormalizacion()
    

    def normalizando(self):
        #Muestro un widget que indica que se va a estar normalizando
        self.avisoPreNormalizacion.exec()
        #Se guarda en una variable la ruta de la capa
        self.rutaArchivo = iface.activeLayer().dataProvider().dataSourceUri()
        posicionArchivo = self.rutaArchivo.find('?type=')
        #Se busca una posicion especifica del archivo para trabajar con el correctamente
        if self.rutaArchivo.find('file://') == -1:
            self.rutaFinal = self.rutaArchivo[:posicionArchivo]
        else:  
            self.rutaFinal = self.rutaArchivo[7:posicionArchivo]
        #Se verifica que el archivo es de tipo csv
        if self.rutaFinal.find('.csv') == -1:
            self.errorNormalizando = -2
            return

        #Se busca cual es el separador
        posicionSeparador = self.rutaArchivo.find('delimiter=') + 10
        separador = self.rutaArchivo[posicionSeparador:posicionSeparador + 1]
        #Se verifica que el archivo no contenga caracteres especiales
        try:
            df = pd.read_csv(self.rutaFinal,sep=separador)
        except:
            self.errorNormalizando = -3
            return
        #Se cargan las urls de las APIs y los Headers
        server = 'https://servicios.usig.buenosaires.gob.ar/normalizar/'
        server2 = 'https://ws.usig.buenosaires.gob.ar/datos_utiles'
        headers = {
            'Content-Type': 'application/json'
        }
        self.tamañoArchivo = len(df)
       	self.iterations = 0
 
        #Hilo que se iba a utilizar para visualizar el estado de la normalización
        #tareaNormalizar = QgsTask.fromFunction('Normalizando...', self.normalizandoArchivo, on_finished=self.completed,wait_time=self.tamañoArchivo)
        #Se agrega el hilo a un task manager
        #QgsApplication.taskManager().addTask(tareaNormalizar)

        #Se recorre fila por fila consultando a las APIs y se van creando y llenando las nuevas columnas con datos útiles
        for i in range (0, len(df)):
            try:
                url = server + '?direccion=' + str(df.loc[i,self.campo])+'&geocodificar=TRUE'
                #Solicita a la API
                response = requests.request('GET', url, headers = headers, allow_redirects=False)
                #Devuelve un resultado
                resultado_du = response.json()
                #Se añaden los datos a las columnas
                df.loc[i,'coord_x'] = resultado_du['direccionesNormalizadas'][0]['coordenadas']['x']
                df.loc[i,'coord_y'] = resultado_du['direccionesNormalizadas'][0]['coordenadas']['y']
                df.loc[i,'direccion_normalizada']= resultado_du['direccionesNormalizadas'][0]['direccion']
                #En base a las coordenadas conseguidas en la primera API, el resto de la información se consigue en la segunda API
                url2 = server2 + '?x=' + str(df.loc[i,'coord_x'])+ '&y=' + str(df.loc[i,'coord_y'])
                #Solicita a la segunda API
                response2 = requests.request('GET', url2, headers = headers, allow_redirects=False)
                #Devuelve un resultado
                resultado_du2 = response2.json()
                #Se añaden los datos a las columnas
                df.loc[i,'comuna'] = resultado_du2['comuna']
                df.loc[i,'barrio'] = resultado_du2['barrio']
                df.loc[i,'comisaria'] = resultado_du2['comisaria']
                df.loc[i,'area_hospitalaria'] = resultado_du2['area_hospitalaria']
                df.loc[i,'region_sanitaria'] = resultado_du2['region_sanitaria']
                df.loc[i,'status_geocode'] = 'OK'
            except:
                #Si no se encuentra alguna dirección solicitada, se creará una columna para esta fila con el status "error"
                df.loc[i,'status_geocode'] = 'Error'
                #Se añade el error al contador
                self.errorNormalizando = self.errorNormalizando + 1
                continue
                self.iterations += 1
            print(str(i) + " de " + str(self.tamañoArchivo - 1) + " registros realizados.")
            #Si la cantidad de errores es igual a la cantidad de registros es porque se ingreso un dato incorrecto
        if len(df) == self.errorNormalizando:
            self.errorNormalizando = -1
            return
        else:
            #Si la cantidad de errores es menor a la cantidad de registros entonces se crea el nuevo archivo normalizado
            #y se informa la cantidad de errores que hubo
            posC = self.rutaFinal.find('.csv')
            self.rutaFinal = self.rutaFinal[:posC] + "Normalizado.csv"
            df.reset_index().to_csv(self.rutaFinal,header=True,index=False)
            return

    def postNormalizacion(self):
        #Con estos if se verifica si hubo algunos errores en la normalización y los muestra por pantalla
        if self.errorNormalizando < 0:
            #Error de campo
            if self.errorNormalizando == -1: 
                QMessageBox.information(None, u'Normalizador de Direcciones', u'El campo seleccionado no corresponde a las direcciones. \nVerifique que el campo seleccionado contenga tanto la dirección como la altura.')
            #Error de archivo seleccionado
            if self.errorNormalizando == -2:    
                QMessageBox.information(None, u'Normalizador de Direcciones', u'La capa seleccionada no pertenece a un archivo CSV')
            #Error de capa
            if self.errorNormalizando == -3: 
                QMessageBox.information(None, u'Normalizador de Direcciones', u'La capa pertenece a un archivo que contiene caracteres especiales.\nCambie el nombre del archivo para normalizar')    
        else:
            #Se carga la capa actualizada
            uri = "file://" + self.rutaFinal + "?delimiter={}&xField={}&yField={}".format(",", "coord_x", "coord_y")
            vlayer = QgsVectorLayer(uri, self.nombreCapa + "Normalizado" , "delimitedtext")
            #Widget que indica que se termino de normalizar y muestra la ruta del archivo normalizado. Además indica la cantidad de errores que hubieron
            QMessageBox.information(None, u'Normalizador de Direcciones', u'El archivo CSV se ha normalizado.\nHubo errores en ' + str(self.errorNormalizando) + ' registros.\nEl Archivo se encuentra en la ruta:\n' + str(self.rutaFinal) + '.')
            #Se añade la capa normalizada
            QgsProject.instance().addMapLayer(vlayer)



