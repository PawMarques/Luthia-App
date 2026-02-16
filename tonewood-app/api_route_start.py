""" API ROUTE START """
@app.route('/api/formats/<int:category_id>')
def get_formats_by_category(category_id):
    """API endpoint to get formats available for a specific category"""
    from flask import jsonify
    
    try:
        # Get distinct formats for products in this category
        formats = db.session.query(Format).join(Product).filter(
            Product.category_id == category_id,
            Product.format_id.isnot(None)
        ).distinct().order_by(Format.name).all()
        
        result = [{'id': f.format_id, 'name': f.name} for f in formats]
        
        response = jsonify({'formats': result})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        print(f"Error in get_formats_by_category: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
""" API ROUTE END """