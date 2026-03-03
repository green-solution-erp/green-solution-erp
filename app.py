from flask import Flask, render_template, request, redirect, url_for, flash, g
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_erp'
BASE_DIR = os.path.dirname(__file__) or '.'
DB_FILE = os.path.join(BASE_DIR, 'database.db')

if not os.path.exists(DB_FILE):
    import database
    database.create_db()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_FILE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_config():
    db = get_db()
    return db.execute('SELECT * FROM configuracion WHERE id = 1').fetchone()

@app.route('/')
def dashboard():
    db = get_db()
    # Calcular métricas para el dashboard
    # Stock crítico
    stock_critico = db.execute('SELECT * FROM productos WHERE stock_actual <= stock_minimo').fetchall()
    
    # Total a cobrar en cuentas corrientes
    clientes_saldos = db.execute('''
        SELECT c.nombre_grafica, 
               SUM(CASE WHEN cc.tipo_movimiento = 'CARGO' THEN cc.monto_usd ELSE 0 END) - 
               SUM(CASE WHEN cc.tipo_movimiento = 'ABONO' THEN cc.monto_usd ELSE 0 END) as saldo_usd
        FROM clientes c
        LEFT JOIN cuenta_corriente cc ON c.id = cc.cliente_id
        GROUP BY c.id
    ''').fetchall()
    
    total_cobrar_usd = sum((row['saldo_usd'] or 0) for row in clientes_saldos)
    
    # Ventas del mes (mock)
    ventas_mes_usd = db.execute("SELECT SUM(total_usd) as total FROM ventas WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')").fetchone()['total'] or 0
    
    config = get_config()
    
    return render_template('dashboard.html', 
                           stock_critico=stock_critico, 
                           total_cobrar_usd=total_cobrar_usd,
                           ventas_mes_usd=ventas_mes_usd,
                           config=config)

@app.route('/configuracion', methods=['GET', 'POST'])
def configuracion():
    db = get_db()
    if request.method == 'POST':
        tipo_cambio = float(request.form['tipo_cambio'])
        iva_porcentaje = float(request.form['iva_porcentaje'])
        
        db.execute('UPDATE configuracion SET tipo_cambio = ?, iva_porcentaje = ? WHERE id = 1', (tipo_cambio, iva_porcentaje))
        db.commit()
        flash('Configuración actualizada correctamente.', 'success')
        return redirect(url_for('configuracion'))
        
    config = get_config()
    return render_template('configuracion.html', config=config)

@app.route('/inventario', methods=['GET', 'POST'])
def inventario():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_producto':
            nombre = request.form['nombre']
            marca = request.form['marca']
            categoria = request.form['categoria']
            costo = float(request.form['precio_costo_usd'])
            venta = float(request.form['precio_venta_usd'])
            stock = int(request.form['stock_actual'])
            minimo = int(request.form['stock_minimo'])
            eco = request.form.get('certificacion_eco', 'Ninguna')
            
            db.execute('''
                INSERT INTO productos (nombre, marca, categoria, precio_costo_usd, precio_venta_usd, stock_actual, stock_minimo, certificacion_eco)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, marca, categoria, costo, venta, stock, minimo, eco))
            db.commit()
            flash('Producto agregado correctamente.', 'success')
            
        elif action == 'add_maquina':
            nro_serie = request.form['numero_serie']
            marca = request.form['marca']
            modelo = request.form['modelo']
            eficiencia = request.form.get('eficiencia_energetica', 'Estándar')
            
            try:
                db.execute('INSERT INTO maquinarias (numero_serie, marca, modelo, eficiencia_energetica) VALUES (?, ?, ?, ?)', 
                           (nro_serie, marca, modelo, eficiencia))
                db.commit()
                flash('Máquina registrada correctamente.', 'success')
            except sqlite3.IntegrityError:
                flash('Error: Ya existe una máquina con ese número de serie.', 'danger')
                
        return redirect(url_for('inventario'))
        
    productos = db.execute('SELECT * FROM productos ORDER BY nombre').fetchall()
    maquinarias = db.execute('SELECT * FROM maquinarias ORDER BY marca').fetchall()
    return render_template('inventario.html', productos=productos, maquinarias=maquinarias)

@app.route('/editar_producto/<int:id>', methods=['POST'])
def editar_producto(id):
    db = get_db()
    nombre = request.form['nombre']
    marca = request.form.get('marca', '')
    categoria = request.form['categoria']
    costo = float(request.form['precio_costo_usd'])
    venta = float(request.form['precio_venta_usd'])
    stock = int(request.form['stock_actual'])
    minimo = int(request.form['stock_minimo'])
    eco = request.form.get('certificacion_eco', 'Ninguna')
    
    db.execute('''
        UPDATE productos 
        SET nombre=?, marca=?, categoria=?, precio_costo_usd=?, precio_venta_usd=?, stock_actual=?, stock_minimo=?, certificacion_eco=? 
        WHERE id=?
    ''', (nombre, marca, categoria, costo, venta, stock, minimo, eco, id))
    db.commit()
    flash('Producto actualizado correctamente.', 'success')
    return redirect(url_for('inventario'))

@app.route('/eliminar_producto/<int:id>', methods=['POST'])
def eliminar_producto(id):
    db = get_db()
    db.execute('DELETE FROM productos WHERE id=?', (id,))
    db.commit()
    flash('Producto eliminado con éxito.', 'success')
    return redirect(url_for('inventario'))

@app.route('/clientes', methods=['GET', 'POST'])
def clientes():
    db = get_db()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_cliente':
            nombre = request.form['nombre_grafica']
            ruc = request.form['ruc']
            telefono = request.form['telefono']
            direccion = request.form['direccion']
            
            try:
                db.execute('INSERT INTO clientes (nombre_grafica, ruc, telefono, direccion) VALUES (?, ?, ?, ?)',
                           (nombre, ruc, telefono, direccion))
                db.commit()
                flash('Cliente registrado exitosamente.', 'success')
            except sqlite3.IntegrityError:
                flash('Error: El RUC ingresado ya existe.', 'danger')
                
        elif action == 'registrar_pago':
            cliente_id = request.form['cliente_id']
            monto = float(request.form['monto_usd'])
            concepto = request.form['concepto']
            config = get_config()
            monto_pyg = monto * config['tipo_cambio']
            
            db.execute('''
                INSERT INTO cuenta_corriente (cliente_id, concepto, monto_usd, monto_pyg, tipo_movimiento)
                VALUES (?, ?, ?, ?, 'ABONO')
            ''', (cliente_id, concepto, monto, monto_pyg))
            db.commit()
            flash('Pago registrado correctamente.', 'success')
            
        return redirect(url_for('clientes'))
        
    clientes_query = db.execute('''
        SELECT c.*, 
               (SUM(CASE WHEN cc.tipo_movimiento = 'CARGO' THEN cc.monto_usd ELSE 0 END) - 
                SUM(CASE WHEN cc.tipo_movimiento = 'ABONO' THEN cc.monto_usd ELSE 0 END)) as saldo_usd
        FROM clientes c
        LEFT JOIN cuenta_corriente cc ON c.id = cc.cliente_id
        GROUP BY c.id
        ORDER BY c.nombre_grafica
    ''').fetchall()
    
    return render_template('clientes.html', clientes=clientes_query)

@app.route('/soporte', methods=['GET', 'POST'])
def soporte():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_ticket':
            numero_serie = request.form['numero_serie']
            tipo = request.form['tipo_mantenimiento']
            tecnico = request.form['tecnico']
            descripcion = request.form['descripcion']
            
            db.execute('INSERT INTO tickets_servicio (numero_serie, tipo_mantenimiento, tecnico, descripcion) VALUES (?, ?, ?, ?)',
                       (numero_serie, tipo, tecnico, descripcion))
            db.commit()
            flash('Ticket registrado exitosamente.', 'success')
            
        elif action == 'cerrar_ticket':
            ticket_id = request.form['ticket_id']
            db.execute("UPDATE tickets_servicio SET estado = 'Cerrado' WHERE id = ?", (ticket_id,))
            db.commit()
            flash('Ticket cerrado.', 'success')
            
        return redirect(url_for('soporte'))
        
    tickets = db.execute('SELECT * FROM tickets_servicio ORDER BY estado ASC, id DESC').fetchall()
    maquinarias = db.execute('SELECT * FROM maquinarias').fetchall()
    return render_template('soporte.html', tickets=tickets, maquinarias=maquinarias)

@app.route('/ventas', methods=['GET', 'POST'])
def ventas():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'procesar_venta':
            cliente_id = request.form['cliente_id']
            producto_id = request.form['producto_id']
            cantidad = int(request.form['cantidad'])
            
            # Obtener datos del producto y configuración
            producto = db.execute('SELECT * FROM productos WHERE id = ?', (producto_id,)).fetchone()
            config = get_config()
            
            if producto and producto['stock_actual'] >= cantidad:
                total_usd = producto['precio_venta_usd'] * cantidad
                total_pyg = total_usd * config['tipo_cambio']
                
                # 1. Registrar venta
                cur = db.cursor()
                cur.execute('INSERT INTO ventas (cliente_id, total_usd, total_pyg, tipo_cambio_aplicado) VALUES (?, ?, ?, ?)',
                            (cliente_id, total_usd, total_pyg, config['tipo_cambio']))
                venta_id = cur.lastrowid
                
                # 2. Registrar detalle de venta
                cur.execute('INSERT INTO venta_detalles (venta_id, producto_id, cantidad, precio_unitario_usd, subtotal_usd) VALUES (?, ?, ?, ?, ?)',
                            (venta_id, producto_id, cantidad, producto['precio_venta_usd'], total_usd))
                
                # 3. Descontar stock
                cur.execute('UPDATE productos SET stock_actual = stock_actual - ? WHERE id = ?', (cantidad, producto_id))
                
                # 4. Cargar a cuenta corriente
                concepto = f"Venta #{venta_id} - {cantidad}x {producto['nombre']}"
                cur.execute('INSERT INTO cuenta_corriente (cliente_id, concepto, monto_usd, monto_pyg, tipo_movimiento) VALUES (?, ?, ?, ?, ?)',
                            (cliente_id, concepto, total_usd, total_pyg, 'CARGO'))
                
                db.commit()
                flash('Venta procesada y cargada a cuenta corriente correctamente.', 'success')
            else:
                flash('Error: Stock insuficiente.', 'danger')
                
        return redirect(url_for('ventas'))
        
    clientes = db.execute('SELECT id, nombre_grafica, ruc FROM clientes ORDER BY nombre_grafica').fetchall()
    productos = db.execute('SELECT id, nombre, precio_venta_usd, stock_actual FROM productos WHERE stock_actual > 0 ORDER BY nombre').fetchall()
    
    ventas_historial = db.execute('''
        SELECT v.id, v.fecha, v.total_usd, v.total_pyg, c.nombre_grafica 
        FROM ventas v
        JOIN clientes c ON v.cliente_id = c.id
        ORDER BY v.id DESC LIMIT 15
    ''').fetchall()
    
    return render_template('ventas.html', clientes=clientes, productos=productos, ventas_historial=ventas_historial)

if __name__ == '__main__':
    app.run(debug=True)
