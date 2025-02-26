# app.py
from flask import Flask, render_template, request, redirect, url_for, jsonify, g    
import sqlite3
from datetime import datetime
import pdb; 

app = Flask(__name__)

DATABASE = 'instance/SLEP.DB'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    return redirect(url_for('class_page'))

@app.route('/class')
def class_page():
    return render_template('class.html', active_page='class')

@app.route('/fields')
def fields():
    return render_template('fields.html', active_page='fields')

# Add these routes after the existing routes in app.py



@app.route('/rules_group')
def rules_group():
    return render_template('rules_group.html', active_page='rules_group')

@app.route('/rules')
def rules():
    return render_template('rules.html', active_page='rules')

@app.route('/tables')
def tables():
    return render_template('tables.html', active_page='tables')

@app.route('/get_classes')
def get_classes():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM GEE_FIELD_CLASSES')
    classes = cursor.fetchall()
    return jsonify([dict(row) for row in classes])

@app.route('/get_fields')
def get_fields():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT f.*, c.FIELD_CLASS_NAME 
        FROM GEE_FIELDS f 
        LEFT JOIN GEE_FIELD_CLASSES c ON f.GFC_ID = c.GFC_ID
    ''')
    fields = cursor.fetchall()
    return jsonify([dict(row) for row in fields])

@app.route('/add_field', methods=['POST'])
def add_field():
    try:
        data = request.json
        if not data['fieldName'] or not data['type']:
            return jsonify({"success": False, "message": "Field Name and Type are required"})
            
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            INSERT INTO GEE_FIELDS 
            (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_PRECISION_SIZE, 
             GF_DEFAULT_VALUE, GF_DESCRIPTION, CREATE_DATE) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('gfcId'),
            data['fieldName'].strip(),
            data['type'].strip(),
            data.get('size'),
            data.get('precision'),
            data.get('defaultValue'),
            data.get('description', '').strip(),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        db.commit()
        return jsonify({"success": True, "message": "Field added successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/update_field', methods=['PUT'])
def update_field():
    try:
        data = request.json
        if not data['fieldName'] or not data['type']:
            return jsonify({"success": False, "message": "Field Name and Type are required"})
            
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            UPDATE GEE_FIELDS 
            SET GFC_ID = ?,
                GF_NAME = ?, 
                GF_TYPE = ?, 
                GF_SIZE = ?,
                GF_PRECISION_SIZE = ?,
                GF_DEFAULT_VALUE = ?,
                GF_DESCRIPTION = ?,
                UPDATE_DATE = ?
            WHERE GF_ID = ?
        ''', (
            data.get('gfcId'),
            data['fieldName'].strip(),
            data['type'].strip(),
            data.get('size'),
            data.get('precision'),
            data.get('defaultValue'),
            data.get('description', '').strip(),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            data['gfId']
        ))
        
        db.commit()
        return jsonify({"success": True, "message": "Field updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/delete_field/<int:gf_id>', methods=['DELETE'])
def delete_field(gf_id):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('DELETE FROM GEE_FIELDS WHERE GF_ID = ?', (gf_id,))
        db.commit()
        return jsonify({"success": True, "message": "Field deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/get_field_classes')
def get_field_classes():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT GFC_ID, FIELD_CLASS_NAME FROM GEE_FIELD_CLASSES')
    classes = cursor.fetchall()
    return jsonify([dict(row) for row in classes])


@app.route('/add_class', methods=['POST'])
def add_class():
    try:
        data = request.json
        if not data['className'] or not data['type']:
            return jsonify({"success": False, "message": "Class Name and Type are required"})
            
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            INSERT INTO GEE_FIELD_CLASSES 
            (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION, CREATE_DATE) 
            VALUES (?, ?, ?, ?)
        ''', (
            data['className'].strip(),
            data['type'].strip(),
            data['description'].strip(),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        db.commit()
        return jsonify({"success": True, "message": "Class added successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/update_class', methods=['PUT'])
def update_class():
    try:
        data = request.json
        if not data['className'] or not data['type']:
            return jsonify({"success": False, "message": "Class Name and Type are required"})
            
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            UPDATE GEE_FIELD_CLASSES 
            SET FIELD_CLASS_NAME = ?, 
                CLASS_TYPE = ?, 
                DESCRIPTION = ?,
                UPDATE_DATE = ?
            WHERE GFC_ID = ?
        ''', (
            data['className'].strip(),
            data['type'].strip(),
            data['description'].strip(),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            data['gfcId']
        ))
        
        db.commit()
        return jsonify({"success": True, "message": "Class updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/delete_class/<int:gfc_id>', methods=['DELETE'])
def delete_class(gfc_id):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('DELETE FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (gfc_id,))
        db.commit()
        return jsonify({"success": True, "message": "Class deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})



# Add these routes to app.py after the existing routes for Functions

@app.route('/function')
def function_page():
    return render_template('function.html', active_page='function')

@app.route('/get_functions')
def get_functions():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM GEE_BASE_FUNCTIONS')
    functions = cursor.fetchall()
    return jsonify([dict(row) for row in functions])

@app.route('/add_function', methods=['POST'])
def add_function():
    try:
        data = request.json
        if not data.get('funcName'):
            return jsonify({"success": False, "message": "Function Name is required"})
            
        db = get_db()
        cursor = db.cursor()
        
        # Insert into GEE_BASE_FUNCTIONS
        cursor.execute('''
            INSERT INTO GEE_BASE_FUNCTIONS 
            (FUNC_NAME, PARAM_COUNT, DESCRIPTION, CREATE_DATE) 
            VALUES (?, ?, ?, ?)
        ''', (
            data['funcName'].strip(),
            data.get('paramCount', 0),
            data.get('description', '').strip(),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        function_id = cursor.lastrowid
        
        # Insert parameters if provided
        params = data.get('parameters', [])
        for param in params:
            cursor.execute('''
                INSERT INTO GEE_BASE_FUNCTIONS_PARAMS 
                (GBF_ID, GBF_SEQ, PARAM_NAME, PARAM_TYPE, DESCRIPTION, CREATE_DATE) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                function_id,
                param.get('sequence'),
                param['paramName'].strip(),
                param['paramType'].strip(),
                param.get('description', '').strip(),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        db.commit()
        return jsonify({"success": True, "message": "Function added successfully", "id": function_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/update_function', methods=['PUT'])
def update_function():
    try:
        data = request.json
        if not data.get('funcName'):
            return jsonify({"success": False, "message": "Function Name is required"})
            
        db = get_db()
        cursor = db.cursor()
        
        # Update GEE_BASE_FUNCTIONS
        cursor.execute('''
            UPDATE GEE_BASE_FUNCTIONS 
            SET FUNC_NAME = ?,
                PARAM_COUNT = ?,
                DESCRIPTION = ?,
                UPDATE_DATE = ?
            WHERE GBF_ID = ?
        ''', (
            data['funcName'].strip(),
            data.get('paramCount', 0),
            data.get('description', '').strip(),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            data['gbfId']
        ))
        
        # Update parameters
        if 'parameters' in data:
            # First delete existing parameters
            cursor.execute('DELETE FROM GEE_BASE_FUNCTIONS_PARAMS WHERE GBF_ID = ?', (data['gbfId'],))
            
            # Insert new parameters
            for param in data['parameters']:
                cursor.execute('''
                    INSERT INTO GEE_BASE_FUNCTIONS_PARAMS 
                    (GBF_ID, GBF_SEQ, PARAM_NAME, PARAM_TYPE, DESCRIPTION, CREATE_DATE) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    data['gbfId'],
                    param.get('sequence'),
                    param['paramName'].strip(),
                    param['paramType'].strip(),
                    param.get('description', '').strip(),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
        
        db.commit()
        return jsonify({"success": True, "message": "Function updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/delete_function/<int:gbf_id>', methods=['DELETE'])
def delete_function(gbf_id):
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Delete parameters first due to foreign key constraint
        cursor.execute('DELETE FROM GEE_BASE_FUNCTIONS_PARAMS WHERE GBF_ID = ?', (gbf_id,))
        
        # Delete the function
        cursor.execute('DELETE FROM GEE_BASE_FUNCTIONS WHERE GBF_ID = ?', (gbf_id,))
        
        db.commit()
        return jsonify({"success": True, "message": "Function deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


# Add these parameter-related routes to app.py

@app.route('/get_function_params/<int:gbf_id>')
def get_function_params(gbf_id):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            SELECT * FROM GEE_BASE_FUNCTIONS_PARAMS 
            WHERE GBF_ID = ? 
            ORDER BY GBF_SEQ
        ''', (gbf_id,))
        params = cursor.fetchall()
        return jsonify([dict(row) for row in params])
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/add_param', methods=['POST'])
def add_param():
    try:
        data = request.json
        if not data.get('paramName') or not data.get('paramType'):
            return jsonify({"success": False, "message": "Parameter Name and Type are required"})
            
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            INSERT INTO GEE_BASE_FUNCTIONS_PARAMS 
            (GBF_ID, GBF_SEQ, PARAM_NAME, PARAM_TYPE, DESCRIPTION, CREATE_DATE) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['gbfId'],
            data['sequence'],
            data['paramName'].strip(),
            data['paramType'].strip(),
            data.get('description', '').strip(),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        # Update parameter count in the function table
        cursor.execute('''
            UPDATE GEE_BASE_FUNCTIONS 
            SET PARAM_COUNT = (
                SELECT COUNT(*) 
                FROM GEE_BASE_FUNCTIONS_PARAMS 
                WHERE GBF_ID = ?
            )
            WHERE GBF_ID = ?
        ''', (data['gbfId'], data['gbfId']))
        
        db.commit()
        return jsonify({"success": True, "message": "Parameter added successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/update_param', methods=['PUT'])
def update_param():
    try:
        data = request.json
        if not data.get('paramName') or not data.get('paramType'):
            return jsonify({"success": False, "message": "Parameter Name and Type are required"})
            
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            UPDATE GEE_BASE_FUNCTIONS_PARAMS 
            SET PARAM_NAME = ?,
                PARAM_TYPE = ?,
                GBF_SEQ = ?,
                DESCRIPTION = ?,
                UPDATE_DATE = ?
            WHERE GBFP_ID = ?
        ''', (
            data['paramName'].strip(),
            data['paramType'].strip(),
            data['sequence'],
            data.get('description', '').strip(),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            data['gbfpId']
        ))
        
        db.commit()
        return jsonify({"success": True, "message": "Parameter updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/delete_param/<int:gbfp_id>', methods=['DELETE'])
def delete_param(gbfp_id):
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get the GBF_ID before deleting the parameter
        cursor.execute('SELECT GBF_ID FROM GEE_BASE_FUNCTIONS_PARAMS WHERE GBFP_ID = ?', (gbfp_id,))
        result = cursor.fetchone()
        gbf_id = result['GBF_ID'] if result else None
        
        # Delete the parameter
        cursor.execute('DELETE FROM GEE_BASE_FUNCTIONS_PARAMS WHERE GBFP_ID = ?', (gbfp_id,))
        
        # Update parameter count in the function table
        if gbf_id:
            cursor.execute('''
                UPDATE GEE_BASE_FUNCTIONS 
                SET PARAM_COUNT = (
                    SELECT COUNT(*) 
                    FROM GEE_BASE_FUNCTIONS_PARAMS 
                    WHERE GBF_ID = ?
                )
                WHERE GBF_ID = ?
            ''', (gbf_id, gbf_id))
        
        db.commit()
        return jsonify({"success": True, "message": "Parameter deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    

if __name__ == '__main__':
    app.run(debug=True)
