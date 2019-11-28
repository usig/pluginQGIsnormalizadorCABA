# pluginQGISnormalizadorCABA
Es un plugin de la aplicación QGIS. El mismo levanta un archivo CSV y lo normaliza con la APIs "Servicios USIG y "Datos útiles" de GCBA

### ¿Como esta compuesto el plugin?

El plugin, el cual esta programado en Python, esta compuesto por una clase llamada “normalizadorCABA” la cual contiene 9 métodos. Los métodos son:

__init__ : método que inicializa todas las variables y widgets.

__initGui__: es el que crea el icono del plugin que esta ubicado en la barra de herramientas.

__unload__ : encargado de remover los rastros del plugin si este es eliminado.

__aceptarCapa__ : esta conectado al botón del widget de selección de capas, se encarga de guardar el dato seleccionado en una variable.

__aceptarColumna__ : igual que el método anterior pero aplicado a las columnas.

__cancelarAccion__ : método que cierra cualquier widget que este abierto.

__run__ : es accionado al presionar el icono del plugin, es el que va abrir los widgets solicitando la selección de datos al usuario. Esta conectado el método “normalizando” y “postNormalizacion”

__normalizando__ : luego de seleccionar todos los datos, este método es llamado. Encargado se comunicarse con las 2 APIs y rellenar las columnas del archivo CSV.

__postNormalizacion__ : este método es llamado después de normalizar el archivo. Se encarga de verificar de que no hubo errores en la normalización ademas de informar la existencia de lo mismos. Luego crea una copia del archivo CSV original pero con los datos añadidos por el plugin
