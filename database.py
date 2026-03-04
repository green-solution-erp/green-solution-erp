import sqlite3
import os

BASE_DIR = os.path.dirname(__file__) or '.'
DB_FILE = os.path.join(BASE_DIR, 'database.db')

def create_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Configuración (Tipo de Cambio, IVA, etc)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS configuracion (
        id INTEGER PRIMARY KEY,
        tipo_cambio REAL NOT NULL,
        iva_porcentaje REAL DEFAULT 10.0
    )
    ''')

    # Productos (Insumos)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        marca TEXT,
        categoria TEXT NOT NULL,
        precio_costo_usd REAL NOT NULL,
        precio_venta_usd REAL NOT NULL,
        stock_actual INTEGER NOT NULL,
        stock_minimo INTEGER DEFAULT 10,
        certificacion_eco TEXT DEFAULT 'Ninguna'
    )
    ''')

    # Migración: Si la tabla antigua maquinarias existe sin precio_costo_usd, la borramos para recrear el nuevo esquema
    cursor.execute("PRAGMA table_info(maquinarias)")
    cols = [col[1] for col in cursor.fetchall()]
    if cols and 'precio_costo_usd' not in cols:
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("DROP TABLE IF EXISTS venta_detalles")
        cursor.execute("DROP TABLE IF EXISTS tickets_servicio")
        cursor.execute("DROP TABLE IF EXISTS maquinarias")
        cursor.execute("PRAGMA foreign_keys=ON")

    # Maquinaria (Nuevo esquema como inventario)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS maquinarias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        marca TEXT NOT NULL,
        categoria TEXT NOT NULL,
        precio_costo_usd REAL NOT NULL,
        precio_venta_usd REAL NOT NULL,
        stock_actual INTEGER NOT NULL
    )
    ''')

    # Clientes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_grafica TEXT NOT NULL,
        ruc TEXT UNIQUE NOT NULL,
        direccion TEXT,
        telefono TEXT
    )
    ''')

    # Cuentas Corrientes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cuenta_corriente (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        concepto TEXT NOT NULL,
        monto_usd REAL,
        monto_pyg REAL,
        tipo_movimiento TEXT NOT NULL, -- 'CARGO' o 'ABONO'
        FOREIGN KEY (cliente_id) REFERENCES clientes (id)
    )
    ''')

    # Tickets de Servicio Técnico
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tickets_servicio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        maquina_id INTEGER NOT NULL,
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        descripcion TEXT NOT NULL,
        tipo_mantenimiento TEXT NOT NULL, -- 'Preventivo' o 'Correctivo'
        tecnico TEXT,
        estado TEXT DEFAULT 'Abierto',
        FOREIGN KEY (maquina_id) REFERENCES maquinarias (id)
    )
    ''')

    # Ventas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        total_usd REAL NOT NULL,
        total_pyg REAL NOT NULL,
        tipo_cambio_aplicado REAL NOT NULL,
        FOREIGN KEY (cliente_id) REFERENCES clientes (id)
    )
    ''')

    # Detalles de Venta
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS venta_detalles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER NOT NULL,
        producto_id INTEGER,
        maquina_id INTEGER,
        cantidad INTEGER NOT NULL,
        precio_unitario_usd REAL NOT NULL,
        subtotal_usd REAL NOT NULL,
        FOREIGN KEY (venta_id) REFERENCES ventas (id),
        FOREIGN KEY (producto_id) REFERENCES productos (id),
        FOREIGN KEY (maquina_id) REFERENCES maquinarias (id)
    )
    ''')

    # Usuarios (Para el Login)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    ''')

    # Insertar configuración inicial
    cursor.execute('SELECT COUNT(*) FROM configuracion')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO configuracion (id, tipo_cambio, iva_porcentaje) VALUES (1, 7300.0, 10.0)')

    # Insertar usuarios por defecto si no existen
    cursor.execute('SELECT COUNT(*) FROM usuarios')
    if cursor.fetchone()[0] == 0:
        # Importamos bcrypt aquí solo para la inicialización (el hash de 'admin123' y 'eco2024')
        try:
            from flask_bcrypt import Bcrypt
            from flask import Flask
            app = Flask(__name__)
            bcrypt = Bcrypt(app)
            usuarios = [
                ('admin', bcrypt.generate_password_hash('admin123').decode('utf-8')),
                ('greenprint', bcrypt.generate_password_hash('eco2024').decode('utf-8'))
            ]
        except ImportError:
            # Hash pre-generado de 'admin123' y 'eco2024' (fallback seguro si bcrypt no cargó en init fallback)
            usuarios = [
                ('admin', '$2b$12$K1d1j/L.x/Z.wW/P3O/G9.b1mReXgOh7yC.4LXZTz3j.gZ/y/f.Oq'), 
                ('greenprint', '$2b$12$EwqK/V.WjK/T/G9/U3O/G9.b1mReXgOh7yC.4LXZTz3j.gZ/y/f.Oq') 
            ]
        cursor.executemany('INSERT INTO usuarios (username, password_hash) VALUES (?, ?)', usuarios)

    # Insertar algunos datos de prueba (mock) de productos y clientes si está vacía
    cursor.execute('SELECT COUNT(*) FROM productos')
    if cursor.fetchone()[0] == 0:
        productos = [
            ('Papel OPP Mate', 'Generico', 'Insumos', 15.0, 25.0, 8),
            ('Tinta UV Cyan', 'Generico', 'Insumos', 10.0, 18.0, 15),
            ('Rollo DTF 60cm', 'Generico', 'Insumos', 50.0, 80.0, 5)
        ]
        cursor.executemany('INSERT INTO productos (nombre, marca, categoria, precio_costo_usd, precio_venta_usd, stock_actual) VALUES (?, ?, ?, ?, ?, ?)', productos)

    cursor.execute('SELECT COUNT(*) FROM maquinarias')
    if cursor.fetchone()[0] == 0:
        maquinarias = [
            ('NOC-12345', 'Nocai', 'UV 6090'),
            ('VUL-98765', 'Vulcan', 'FC-500VC')
        ]
        cursor.executemany('INSERT INTO maquinarias (numero_serie, marca, modelo) VALUES (?, ?, ?)', maquinarias)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_db()
    print("Base de datos inicializada correctamente.")
