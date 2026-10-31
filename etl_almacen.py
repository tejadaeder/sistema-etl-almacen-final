import pandas as pd
import mysql.connector
import json



def cargar_configuracion(ruta_archivo='config.json'):
    with open(ruta_archivo, 'r') as archivo:
        configuracion = json.load(archivo)
    return configuracion


def ejecutar_etl():

    print("1. Leyendo archivo CSV...")
    df = pd.read_csv('almacen_inventario_sucio_500.csv')

    print("2. Eliminando duplicados...")
    df = df.drop_duplicates(subset=['id'], keep='first').copy()

    print("3. Eliminando filas con valores nulos...")
    df = df.dropna(subset=['id', 'nombre', 'categoria','stock', 'precio']).copy()

    print("4.- Estandarizando textos - como quitar espacios extras")
    df['nombre'] = df['nombre'].astype(str).str.strip().str.title()
    df['categoria'] = df['categoria'].astype(str).str.strip().str.title()

    print("5.- Limpiar simbolo moneda y convertir a numerico")

    df['precio'] = df['precio'].astype(str).str.replace('S/.','',regex=False).str.strip()
    df['precio'] = pd.to_numeric(df['precio'], errors='coerce')
    df['stock'] = pd.to_numeric(df['stock'], errors='coerce')

    df = df.dropna(subset=['stock', 'precio'])
    df = df[(df['stock'] > 0) & (df['precio'] > 0)].copy()
    df['stock'] = df['stock'].astype(int)

    print("6.- Generar los 2 campos calculados")
    df['valor_inventario'] = df.apply(lambda r: calcular_valor_inventario(r['stock'], r['precio']), axis=1)
    df['estado_stock'] = df.apply(lambda r: clasificar_estado_stock(r['stock']), axis=1)

    print(f" Registros procesados: {len(df)}")

    print("7.- Guardando en base de datos MySQL... ")
    db_config = cargar_configuracion('config.json')

    conexion = mysql.connector.connect(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database']
    )

    cursor = conexion.cursor()
    cursor.execute("TRUNCATE TABLE productos;")

    sql = "INSERT INTO productos (id, nombre, categoria, stock, precio, valor_inventario, estado_stock) VALUES (%s, %s, %s, %s, %s, %s, %s)"

    datos_insetar = [(row['id'], row['nombre'], row['categoria'], row['stock'], row['precio'], row['valor_inventario'], row['estado_stock']) for index, row in df.iterrows()]

    cursor.executemany(sql, datos_insetar)
    conexion.commit()

    print(f" Registros insertados: {cursor.rowcount}")
    cursor.close()
    conexion.close()

    
def calcular_valor_inventario(stock: int, precio: float):
    return round(stock * precio, 2)

def clasificar_estado_stock(stock: int):
    if stock < 20:
        return 'Critico'
    else:
        return 'Saludable'


if __name__ == "__main__":
    ejecutar_etl()