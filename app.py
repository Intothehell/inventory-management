from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import sqlite3
from datetime import datetime
import random
import string

app = Flask(__name__)
app.secret_key = 'inventory_system_secret_key_2024'

# Database initialization
def init_db():
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  user_type TEXT NOT NULL,
                  full_name TEXT NOT NULL)''')
    
    # Create inventory table
    c.execute('''CREATE TABLE IF NOT EXISTS inventory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  serial_number TEXT UNIQUE NOT NULL,
                  part_name TEXT NOT NULL,
                  part_type TEXT NOT NULL,
                  category TEXT NOT NULL,
                  dimensions TEXT,
                  quantity INTEGER NOT NULL,
                  unit_price REAL NOT NULL,
                  location TEXT,
                  supplier TEXT,
                  date_added TEXT,
                  last_updated TEXT,
                  notes TEXT)''')
    
    # Create activity log table
    c.execute('''CREATE TABLE IF NOT EXISTS activity_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  action TEXT NOT NULL,
                  item_id INTEGER,
                  timestamp TEXT NOT NULL)''')
    
    # Insert default users if not exists
    users = [
        ('admin1', 'admin123', 'admin', 'System Administrator 1'),
        ('admin2', 'admin456', 'admin', 'System Administrator 2'),
        ('viewer1', 'viewer123', 'viewer', 'Viewer User 1'),
        ('viewer2', 'viewer456', 'viewer', 'Viewer User 2')
    ]
    
    for user in users:
        try:
            c.execute("INSERT INTO users (username, password, user_type, full_name) VALUES (?, ?, ?, ?)", user)
        except sqlite3.IntegrityError:
            pass  # User already exists
    
    # Insert sample inventory data if empty
    c.execute("SELECT COUNT(*) FROM inventory")
    if c.fetchone()[0] == 0:
        sample_items = [
            ('INV-20240101-0001', 'Gate Valve', 'Valve', 'Industrial', '2in', 15, 45.99, 'Shelf A1', 'ValveCo', datetime.now().isoformat(), datetime.now().isoformat(), 'Bronze gate valve'),
            ('INV-20240101-0002', 'PVC Pipe', 'Pipe', 'Plumbing', '3in x 10ft', 50, 12.50, 'Rack B3', 'PipeSupply', datetime.now().isoformat(), datetime.now().isoformat(), 'Schedule 40 PVC'),
            ('INV-20240101-0003', 'Copper Coupling', 'Coupling', 'Plumbing', '1/2in', 8, 3.25, 'Bin C2', 'CopperWorks', datetime.now().isoformat(), datetime.now().isoformat(), 'Low stock warning'),
            ('INV-20240101-0004', 'Ball Valve', 'Valve', 'Industrial', '1.5in', 25, 32.75, 'Shelf A2', 'ValveCo', datetime.now().isoformat(), datetime.now().isoformat(), 'Stainless steel'),
            ('INV-20240101-0005', 'Elbow Fitting', 'Fitting', 'Plumbing', '90° 1in', 100, 2.99, 'Bin D4', 'FittingCorp', datetime.now().isoformat(), datetime.now().isoformat(), 'PVC elbow'),
            ('INV-20240101-0006', 'Check Valve', 'Valve', 'Industrial', '2.5in', 5, 89.99, 'Shelf A3', 'FlowTech', datetime.now().isoformat(), datetime.now().isoformat(), 'Low stock'),
            ('INV-20240101-0007', 'Galvanized Pipe', 'Pipe', 'Construction', '4in x 8ft', 30, 28.50, 'Rack B1', 'MetalSupply', datetime.now().isoformat(), datetime.now().isoformat(), 'Heavy duty'),
            ('INV-20240101-0008', 'Compression Coupling', 'Coupling', 'Plumbing', '3/4in', 45, 4.75, 'Bin C1', 'PlumbMaster', datetime.now().isoformat(), datetime.now().isoformat(), 'Brass fitting'),
            ('INV-20240101-0009', 'Butterfly Valve', 'Valve', 'Industrial', '3in', 12, 120.50, 'Shelf A4', 'IndustrialValves', datetime.now().isoformat(), datetime.now().isoformat(), 'Industrial grade'),
            ('INV-20240101-0010', 'Reducer Coupling', 'Coupling', 'Plumbing', '2in to 1.5in', 20, 8.25, 'Bin C3', 'PlumbMaster', datetime.now().isoformat(), datetime.now().isoformat(), 'PVC reducer')
        ]
        
        for item in sample_items:
            c.execute('''INSERT INTO inventory 
                      (serial_number, part_name, part_type, category, dimensions, quantity, unit_price, location, supplier, date_added, last_updated, notes)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', item)
    
    conn.commit()
    conn.close()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session or session['user_type'] != 'admin':
            flash('Admin access required!', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

# Generate serial number
def generate_serial_number(prefix="INV"):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{timestamp}-{random_str}"

# Log activity
def log_activity(user_id, action, item_id=None):
    conn = get_db_connection()
    conn.execute("INSERT INTO activity_log (user_id, action, item_id, timestamp) VALUES (?, ?, ?, ?)",
                 (user_id, action, item_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                           (username, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_type'] = user['user_type']
            session['full_name'] = user['full_name']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    
    # Get categorized counts
    categorized_counts = conn.execute('''
        SELECT part_type, COUNT(*) as count, 
               SUM(quantity * unit_price) as total_value,
               SUM(CASE WHEN quantity < 10 THEN 1 ELSE 0 END) as low_stock_count
        FROM inventory 
        GROUP BY part_type
        ORDER BY count DESC
    ''').fetchall()
    
    # Get total summary
    total_summary = conn.execute('''
        SELECT 
            COUNT(*) as total_items,
            SUM(quantity) as total_quantity,
            SUM(quantity * unit_price) as total_value,
            SUM(CASE WHEN quantity < 10 THEN 1 ELSE 0 END) as total_low_stock
        FROM inventory
    ''').fetchone()
    
    # Get recent activity
    recent_activity = conn.execute('''
        SELECT a.*, u.username 
        FROM activity_log a 
        JOIN users u ON a.user_id = u.id 
        ORDER BY a.timestamp DESC 
        LIMIT 10
    ''').fetchall()
    
    # Get low stock items details
    low_stock_items = conn.execute('''
        SELECT part_name, part_type, quantity, location 
        FROM inventory 
        WHERE quantity < 10 
        ORDER BY quantity ASC 
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                          categorized_counts=categorized_counts,
                          total_summary=total_summary,
                          recent_activity=recent_activity,
                          low_stock_items=low_stock_items)

@app.route('/inventory')
@login_required
def view_inventory():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM inventory ORDER BY date_added DESC').fetchall()
    conn.close()
    return render_template('view_inventory.html', items=items)

@app.route('/add_item', methods=['GET', 'POST'])
@login_required
@admin_required
def add_item():
    if request.method == 'POST':
        serial_number = generate_serial_number()
        part_name = request.form['part_name']
        part_type = request.form['part_type']
        category = request.form['category']
        dimensions = request.form['dimensions']
        quantity = int(request.form['quantity'])
        unit_price = float(request.form['unit_price'])
        location = request.form['location']
        supplier = request.form['supplier']
        notes = request.form['notes']
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO inventory 
            (serial_number, part_name, part_type, category, dimensions, quantity, unit_price, location, supplier, date_added, last_updated, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (serial_number, part_name, part_type, category, dimensions, quantity, unit_price, location, supplier, 
              datetime.now().isoformat(), datetime.now().isoformat(), notes))
        conn.commit()
        
        # Get the inserted item id
        item_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()
        
        # Log activity
        log_activity(session['user_id'], f"Added item: {part_name}", item_id)
        
        flash('Item added successfully!', 'success')
        return redirect(url_for('view_inventory'))
    
    return render_template('add_item.html')

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_item(item_id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        part_name = request.form['part_name']
        part_type = request.form['part_type']
        category = request.form['category']
        dimensions = request.form['dimensions']
        quantity = int(request.form['quantity'])
        unit_price = float(request.form['unit_price'])
        location = request.form['location']
        supplier = request.form['supplier']
        notes = request.form['notes']
        
        conn.execute('''
            UPDATE inventory 
            SET part_name = ?, part_type = ?, category = ?, dimensions = ?, quantity = ?, unit_price = ?, 
                location = ?, supplier = ?, last_updated = ?, notes = ?
            WHERE id = ?
        ''', (part_name, part_type, category, dimensions, quantity, unit_price, location, supplier, 
              datetime.now().isoformat(), notes, item_id))
        conn.commit()
        
        # Log activity
        log_activity(session['user_id'], f"Updated item: {part_name}", item_id)
        
        flash('Item updated successfully!', 'success')
        return redirect(url_for('view_inventory'))
    
    item = conn.execute('SELECT * FROM inventory WHERE id = ?', (item_id,)).fetchone()
    conn.close()
    
    if item is None:
        flash('Item not found!', 'error')
        return redirect(url_for('view_inventory'))
    
    return render_template('edit_item.html', item=item)

@app.route('/delete_item/<int:item_id>')
@login_required
@admin_required
def delete_item(item_id):
    conn = get_db_connection()
    
    # Get item info before deleting for logging
    item = conn.execute('SELECT part_name FROM inventory WHERE id = ?', (item_id,)).fetchone()
    
    conn.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()
    
    if item:
        # Log activity
        log_activity(session['user_id'], f"Deleted item: {item['part_name']}")
    
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('view_inventory'))

@app.route('/filter_items', methods=['GET', 'POST'])
@login_required
def filter_items():
    conn = get_db_connection()
    
    # Get unique values for filters
    categories = conn.execute('SELECT DISTINCT category FROM inventory WHERE category IS NOT NULL ORDER BY category').fetchall()
    part_types = conn.execute('SELECT DISTINCT part_type FROM inventory WHERE part_type IS NOT NULL ORDER BY part_type').fetchall()
    suppliers = conn.execute('SELECT DISTINCT supplier FROM inventory WHERE supplier IS NOT NULL ORDER BY supplier').fetchall()
    
    items = []
    
    if request.method == 'POST':
        filters = []
        params = []
        
        category = request.form.get('category')
        part_type = request.form.get('part_type')
        dimensions = request.form.get('dimensions')
        supplier = request.form.get('supplier')
        
        query = 'SELECT * FROM inventory WHERE 1=1'
        
        if category and category != 'all':
            query += ' AND category = ?'
            params.append(category)
        
        if part_type and part_type != 'all':
            query += ' AND part_type = ?'
            params.append(part_type)
        
        if dimensions:
            query += ' AND dimensions LIKE ?'
            params.append(f'%{dimensions}%')
        
        if supplier and supplier != 'all':
            query += ' AND supplier = ?'
            params.append(supplier)
        
        query += ' ORDER BY part_name'
        items = conn.execute(query, params).fetchall()
    
    conn.close()
    
    return render_template('filter_items.html', 
                          items=items, 
                          categories=categories,
                          part_types=part_types,
                          suppliers=suppliers)

@app.route('/api/search_dimensions')
@login_required
def search_dimensions():
    query = request.args.get('q', '')
    
    conn = get_db_connection()
    results = conn.execute('''
        SELECT DISTINCT dimensions 
        FROM inventory 
        WHERE dimensions IS NOT NULL AND dimensions LIKE ? 
        LIMIT 10
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    return jsonify([result['dimensions'] for result in results if result['dimensions']])

@app.route('/api/inventory_data')
@login_required
def inventory_data():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM inventory').fetchall()
    conn.close()
    
    data = [dict(item) for item in items]
    return jsonify(data)

# ============ TYPE-BASED VIEWS - ADD THESE ROUTES ============

@app.route('/type/<string:part_type>')
@login_required
def view_by_type(part_type):
    """View all items of a specific type (Valve, Pipe, etc.)"""
    conn = get_db_connection()
    
    try:
        # Get items by specific type
        items = conn.execute('''
            SELECT * FROM inventory 
            WHERE UPPER(part_type) = UPPER(?) 
            ORDER BY part_name
        ''', (part_type,)).fetchall()
        
        # Get type statistics
        type_stats = conn.execute('''
            SELECT 
                COUNT(*) as total_items,
                SUM(quantity) as total_quantity,
                SUM(quantity * unit_price) as total_value,
                SUM(CASE WHEN quantity < 10 THEN 1 ELSE 0 END) as low_stock_count
            FROM inventory 
            WHERE UPPER(part_type) = UPPER(?)
        ''', (part_type,)).fetchone()
        
        # Get unique dimensions for this type
        dimensions = conn.execute('''
            SELECT DISTINCT dimensions 
            FROM inventory 
            WHERE UPPER(part_type) = UPPER(?) AND dimensions IS NOT NULL AND dimensions != ''
            ORDER BY dimensions
        ''', (part_type,)).fetchall()
        
        # Get unique categories for this type
        categories = conn.execute('''
            SELECT DISTINCT category 
            FROM inventory 
            WHERE UPPER(part_type) = UPPER(?) AND category IS NOT NULL AND category != ''
            ORDER BY category
        ''', (part_type,)).fetchall()
        
        # Handle None values
        if type_stats is None or type_stats['total_items'] is None:
            type_stats = {
                'total_items': 0,
                'total_quantity': 0,
                'total_value': 0,
                'low_stock_count': 0
            }
        
    except Exception as e:
        flash(f'Error loading {part_type} items: {str(e)}', 'error')
        items = []
        type_stats = {'total_items': 0, 'total_quantity': 0, 'total_value': 0, 'low_stock_count': 0}
        dimensions = []
        categories = []
    
    finally:
        conn.close()
    
    return render_template('type_view.html', 
                         part_type=part_type,
                         items=items,
                         type_stats=type_stats,
                         dimensions=dimensions,
                         categories=categories)

@app.route('/type/<string:part_type>/filter', methods=['POST'])
@login_required
def filter_by_type(part_type):
    """Filter items within a specific type"""
    conn = get_db_connection()
    
    dimensions = request.form.get('dimensions', 'all')
    category = request.form.get('category', 'all')
    
    try:
        # Build query with filters
        query = 'SELECT * FROM inventory WHERE UPPER(part_type) = UPPER(?)'
        params = [part_type]
        
        if dimensions and dimensions != 'all':
            query += ' AND dimensions LIKE ?'
            params.append(f'%{dimensions}%')
        
        if category and category != 'all':
            query += ' AND category = ?'
            params.append(category)
        
        query += ' ORDER BY part_name'
        items = conn.execute(query, params).fetchall()
        
        # Get stats
        stats_query = 'SELECT COUNT(*) as total_items FROM inventory WHERE UPPER(part_type) = UPPER(?)'
        stats_params = [part_type]
        
        if dimensions and dimensions != 'all':
            stats_query += ' AND dimensions LIKE ?'
            stats_params.append(f'%{dimensions}%')
        
        if category and category != 'all':
            stats_query += ' AND category = ?'
            stats_params.append(category)
        
        filtered_stats = conn.execute(stats_query, stats_params).fetchone()
        
        # Get filter options
        dimensions_list = conn.execute('''
            SELECT DISTINCT dimensions 
            FROM inventory 
            WHERE UPPER(part_type) = UPPER(?) AND dimensions IS NOT NULL AND dimensions != ''
            ORDER BY dimensions
        ''', (part_type,)).fetchall()
        
        categories_list = conn.execute('''
            SELECT DISTINCT category 
            FROM inventory 
            WHERE UPPER(part_type) = UPPER(?) AND category IS NOT NULL AND category != ''
            ORDER BY category
        ''', (part_type,)).fetchall()
        
        type_stats = {
            'total_items': filtered_stats['total_items'] or 0,
            'total_quantity': 0,
            'total_value': 0,
            'low_stock_count': 0
        }
        
        flash(f'Found {filtered_stats["total_items"] or 0} items matching your filter', 'success')
        
    except Exception as e:
        flash(f'Error filtering items: {str(e)}', 'error')
        items = []
        type_stats = {'total_items': 0, 'total_quantity': 0, 'total_value': 0, 'low_stock_count': 0}
        dimensions_list = []
        categories_list = []
    
    finally:
        conn.close()
    
    return render_template('type_view.html', 
                         part_type=part_type,
                         items=items,
                         type_stats=type_stats,
                         dimensions=dimensions_list,
                         categories=categories_list,
                         filtered=True)

# ============ END TYPE-BASED VIEWS ============

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)