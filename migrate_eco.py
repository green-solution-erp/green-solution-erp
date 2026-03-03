import sqlite3

DB_FILE = 'database.db'

def migrate():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE productos ADD COLUMN certificacion_eco TEXT DEFAULT "Ninguna"')
        print("Añadida columna certificacion_eco a productos.")
    except sqlite3.OperationalError:
        print("La columna certificacion_eco ya existe.")
        
    try:
        cursor.execute('ALTER TABLE maquinarias ADD COLUMN eficiencia_energetica TEXT DEFAULT "Estándar"')
        print("Añadida columna eficiencia_energetica a maquinarias.")
    except sqlite3.OperationalError:
        print("La columna eficiencia_energetica ya existe.")
        
    # Update mock data to match eco-friendly vibe
    cursor.execute('UPDATE productos SET certificacion_eco = "FSC Mix" WHERE nombre = "Papel OPP Mate"')
    cursor.execute('UPDATE maquinarias SET eficiencia_energetica = "Alta Eficiencia (Low Impact)" WHERE marca = "Nocai"')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    migrate()
