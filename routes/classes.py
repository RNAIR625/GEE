from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
from db_helpers import query_db, modify_db

# Create a Blueprint for class routes
classes_bp = Blueprint('classes', __name__)

@classes_bp.route('/')
def class_page():
    return render_template('class.html', active_page='class')

@classes_bp.route('/get_classes')
def get_classes():
    classes = query_db('SELECT * FROM GEE_FIELD_CLASSES')
    return jsonify([dict(cls) for cls in classes])

@classes_bp.route('/add_class', methods=['POST'])
def add_class():
    data = request.json
    try:
        modify_db(
            'INSERT INTO GEE_FIELD_CLASSES (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION) VALUES (?, ?, ?)',
            (data['className'], data['type'], data['description'])
        )
        return jsonify({'success': True, 'message': 'Class added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@classes_bp.route('/update_class', methods=['PUT'])
def update_class():
    data = request.json
    try:
        modify_db(
            'UPDATE GEE_FIELD_CLASSES SET FIELD_CLASS_NAME = ?, CLASS_TYPE = ?, DESCRIPTION = ?, UPDATE_DATE = ? WHERE GFC_ID = ?',
            (data['className'], data['type'], data['description'], datetime.now(), data['gfcId'])
        )
        return jsonify({'success': True, 'message': 'Class updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@classes_bp.route('/delete_class/<int:gfc_id>', methods=['DELETE'])
def delete_class(gfc_id):
    try:
        # Check if fields are using this class
        fields = query_db('SELECT COUNT(*) as count FROM GEE_FIELDS WHERE GFC_ID = ?', (gfc_id,), one=True)
        if fields['count'] > 0:
            return jsonify({'success': False, 'message': 'Cannot delete: Class is being used by fields'})
        
        modify_db('DELETE FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (gfc_id,))
        return jsonify({'success': True, 'message': 'Class deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
