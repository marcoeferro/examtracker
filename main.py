from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import os
import sqlite3
import time

# Obtén la ruta absoluta al chromedriver
driver_path = os.path.join(os.getcwd(), './chromedriver.exe')  # Usa una ruta absoluta al chromedriver

# Configurar opciones de Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")  # Ejecutar Chrome en modo headless (sin interfaz gráfica)
chrome_options.add_argument("--disable-gpu")  # Necesario para headless en Windows
chrome_options.add_argument("--no-sandbox")  # Por si se está ejecutando en un entorno con restricciones
chrome_options.add_argument("--disable-dev-shm-usage")  # Soluciona algunos problemas en contenedores

# Inicializar el servicio de ChromeDriver
service = Service(driver_path)

# Inicializar el driver de Chrome con las opciones y el servicio
driver = webdriver.Chrome(service=service, options=chrome_options)

# URL de la página web a scrapear
url = 'https://alu.unvime.edu.ar/g3w/fecha_examen?formulario_filtro[ra]=9220d714727dbe74790a6782a5241e56f7034064&formulario_filtro[ubicacion]=3b5e0365f0c2299dfd89eb3852a8ebb566382194&formulario_filtro[carrera]=b29b1565d9765a6a8b1c56798619c06dd91ba4f0&formulario_filtro[plan]=&formulario_filtro[materia]=&formulario_filtro[fecha_desde]=&formulario_filtro[fecha_hasta]=&formulario_filtro[tipo_mesa]='
driver.get(url)

# Espera para que se cargue la página
driver.implicitly_wait(10)  # Puedes ajustar el tiempo de espera según sea necesario
time.sleep(5)  # Espera adicional para asegurarse de que la página se cargue completamente

# Crear o conectarse a la base de datos SQLite
conn = sqlite3.connect('scrapeddata.db')
cursor = conn.cursor()

# Crear las tablas si no existen
cursor.execute('''
CREATE TABLE IF NOT EXISTS materias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    fecha_examen TEXT,
    tipo_inscripcion TEXT,
    inicio_inscripcion TEXT,
    fin_inscripcion TEXT,
    hora_inicio_examen TEXT,
    hora_fin_examen TEXT,
    aula TEXT,
    fecha_tope_bajas TEXT,
    docentes TEXT,
    propuestas INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    carrera TEXT,
    email TEXT NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS users_materias (
    usuario INTEGER,
    materia INTEGER,
    FOREIGN KEY(usuario) REFERENCES users(id),
    FOREIGN KEY(materia) REFERENCES materias(id)
)
''')

# Encontrar todos los divs con la clase "corte"
corte_divs = driver.find_elements(By.CSS_SELECTOR, 'div.corte')

# Lista para almacenar los datos extraídos
exam_data = []

# Iterar sobre cada div encontrado
for div in corte_divs:
    try:
        # Extraer el nombre de la materia del div de encabezado
        encabezado = div.find_element(By.CLASS_NAME, 'encabezado_cuadro').text.strip()
        
        # Encontrar la tabla principal dentro de cada div
        table_principal = div.find_element(By.CSS_SELECTOR, 'table.table-condensed.table-hover.table-striped')
        
        # Encontrar el body de la tabla principal
        table_body_principal = table_principal.find_element(By.TAG_NAME, 'tbody')
        
        # Extraer datos de la tabla principal
        rows_principal = table_body_principal.find_elements(By.TAG_NAME, 'tr')
        
        # Verificar que la tabla principal tenga filas
        if len(rows_principal) == 0:
            raise Exception("La tabla principal no tiene filas.")
        
        # Tomamos solo los primeros 5 td de la primera fila
        cols_principal = rows_principal[0].find_elements(By.TAG_NAME, 'td')[:5]
        cols_principal_text = [col.text.strip() for col in cols_principal]

        # Hacer clic en el botón "Ver" para mostrar la tabla secundaria
        try:
            button = rows_principal[0].find_element(By.CSS_SELECTOR, 'a.ver_mas_info')
            button.click()
            time.sleep(1)  # Esperar un momento para que se cargue la tabla secundaria
        except Exception as e:
            print(f"No se pudo hacer clic en el botón 'Ver': {e}")
            continue
        
        # Buscar la fila que contiene la tabla secundaria
        table_secundaria = None
        for row in rows_principal:
            if 'mas_info' in row.get_attribute('class'):
                table_secundaria = row.find_element(By.CSS_SELECTOR, 'table.table-condensed.table-hover.table-striped')
                break

        # Extraer datos de la tabla secundaria
        if table_secundaria:
            table_body_secundaria = table_secundaria.find_element(By.TAG_NAME, 'tbody')
            row_secundaria = table_body_secundaria.find_elements(By.TAG_NAME, 'tr')
            
            # Tomamos la info secundaria de la primera fila de la tabla secundaria
            if len(row_secundaria) > 0:
                cols_ver_mas = row_secundaria[0].find_elements(By.TAG_NAME, 'td')[:6]
                cols_ver_mas_text = [col.text.strip() for col in cols_ver_mas]
            else:
                cols_ver_mas_text = []
        else:
            cols_ver_mas_text = []
        
        # Crear el diccionario con la información principal extraída
        if len(cols_principal_text) >= 5 and len(cols_ver_mas_text) >= 6:
            exam_info = {
                # INFO PRINCIPAL
                "nombre": cols_principal_text[0],
                "fecha_examen": cols_principal_text[1],
                "tipo_inscripcion": cols_principal_text[2],
                "inicio_inscripcion": cols_principal_text[3],
                "fin_inscripcion": cols_principal_text[4],
                # INFO SECUNDARIA
                "hora_inicio_examen": cols_ver_mas_text[0],
                "hora_fin_examen": cols_ver_mas_text[1],
                "aula": cols_ver_mas_text[2],
                "fecha_tope_bajas": cols_ver_mas_text[3],
                "docentes": cols_ver_mas_text[4],
                "propuestas": cols_ver_mas_text[5],
            }
            exam_data.append(exam_info)
            
            # Insertar los datos en la base de datos
            cursor.execute('''
                INSERT INTO materias (nombre, fecha_examen, tipo_inscripcion, inicio_inscripcion, fin_inscripcion,
                                    hora_inicio_examen, hora_fin_examen, aula, fecha_tope_bajas, docentes, propuestas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                exam_info["nombre"], exam_info["fecha_examen"], exam_info["tipo_inscripcion"],
                exam_info["inicio_inscripcion"], exam_info["fin_inscripcion"], exam_info["hora_inicio_examen"],
                exam_info["hora_fin_examen"], exam_info["aula"], exam_info["fecha_tope_bajas"],
                exam_info["docentes"], exam_info["propuestas"]
            ))
            conn.commit()
    except Exception as e:
        print(f"Error al procesar div 'corte': {e}")

# Imprime los datos extraídos
for exam in exam_data:
    print(exam)

# Cierra el navegador
driver.quit()

# Cierra la conexión a la base de datos
conn.close()
