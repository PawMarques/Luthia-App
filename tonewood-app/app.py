from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from models import db, Species, Product, Vendor, Category, Grade, Format
import os
import traceback

app = Flask(__name__)

# Configure SQLite database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "tonewood.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Create tables if they don't exist
with app.app_context():
    db.create_all()

""" HOMEPAGE START """

def staleness_cell(last_updated):
    """Return an HTML table cell with colour-coded last updated date."""
    if not last_updated:
        return '<td style="color:#999; font-size:12px;">-</td>'
    now = datetime.utcnow()
    age_months = (now - last_updated).days / 30.4
    date_str = last_updated.strftime("%Y-%m-%d")
    if age_months <= 3:
        return f'<td><span class="stale-fresh">{date_str}</span></td>'
    elif age_months <= 6:
        return f'<td><span class="stale-warn">&#9888; {date_str}</span></td>'
    else:
        return f'<td><span class="stale-old">&#9888; {date_str}</span></td>'


"""return "<h1>Hello! Flask is working!</h1><p>If you see this, the server works.</p>" """
@app.route('/')
def index():
    """Home page - shows all products with pagination"""
    try:
        # Get sort and pagination parameters
        sort_by = request.args.get('sort', 'price')
        sort_order = request.args.get('order', 'asc')
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # Only load what we need for dropdowns
        vendors = Vendor.query.filter_by(active=True).all()
        categories = Category.query.all()
        # Get all formats with their categories for filtering
        formats_by_category = {}
        for cat in categories:
            cat_formats = db.session.query(Format).join(Product).filter(
                Product.category_id == cat.category_id,
                Product.format_id.isnot(None)
            ).distinct().order_by(Format.name).all()
            formats_by_category[cat.category_id] = cat_formats
        species_list = Species.query.order_by(Species.commercial_name).limit(100).all()
        
        # Build query with sorting
        query = Product.query
        
        # Apply sorting based on column
        if sort_by == 'species':
            query = query.join(Species).order_by(Species.commercial_name.asc() if sort_order == 'asc' else Species.commercial_name.desc())
        elif sort_by == 'vendor':
            query = query.join(Vendor).order_by(Vendor.name.asc() if sort_order == 'asc' else Vendor.name.desc())
        elif sort_by == 'category':
            query = query.join(Category).order_by(Category.name.asc() if sort_order == 'asc' else Category.name.desc())
        elif sort_by == 'price':
            query = query.order_by(Product.price.asc() if sort_order == 'asc' else Product.price.desc())
        elif sort_by == 'grade':
            query = query.outerjoin(Grade).order_by(Grade.name.asc() if sort_order == 'asc' else Grade.name.desc())
        elif sort_by == 'format':
            query = query.outerjoin(Format).order_by(Format.name.asc() if sort_order == 'asc' else Format.name.desc())
        else:
            query = query.order_by(Product.price.asc())
        
        # Get total count
        total_count = query.count()
        total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
        
        # Apply pagination
        offset = (page - 1) * per_page
        products = query.offset(offset).limit(per_page).all()
        
        # Calculate pagination range
        start_item = offset + 1
        end_item = min(offset + per_page, total_count)
        
        # Function to generate sort URL with pagination
        def sort_url(column):
            if sort_by == column:
                new_order = 'desc' if sort_order == 'asc' else 'asc'
                arrow = ' â–²' if sort_order == 'asc' else ' â–¼'
            else:
                new_order = 'asc'
                arrow = ''
            return f'/?sort={column}&order={new_order}&page=1', arrow
        
        species_url, species_arrow = sort_url('species')
        vendor_url, vendor_arrow = sort_url('vendor')
        category_url, category_arrow = sort_url('category')
        price_url, price_arrow = sort_url('price')
        grade_url, grade_arrow = sort_url('grade')
        format_url, format_arrow = sort_url('format')
        
        # Generate pagination HTML
        def pagination_html():
            html = '<div class="pagination">'
            
            # Previous button
            if page > 1:
                html += f'<a href="/?sort={sort_by}&order={sort_order}&page={page-1}" class="page-btn">â† Previous</a>'
            else:
                html += '<span class="page-btn disabled">â† Previous</span>'
            
            # Page numbers
            # Show: First page, pages around current, last page
            pages_to_show = []
            
            # Always show first page
            pages_to_show.append(1)
            
            # Show pages around current page
            for p in range(max(2, page - 2), min(total_pages, page + 3)):
                if p not in pages_to_show:
                    pages_to_show.append(p)
            
            # Always show last page
            if total_pages > 1 and total_pages not in pages_to_show:
                pages_to_show.append(total_pages)
            
            pages_to_show.sort()
            
            # Generate page links
            prev_page = 0
            for p in pages_to_show:
                # Add ellipsis if there's a gap
                if p > prev_page + 1:
                    html += '<span class="page-ellipsis">...</span>'
                
                if p == page:
                    html += f'<span class="page-num active">{p}</span>'
                else:
                    html += f'<a href="/?sort={sort_by}&order={sort_order}&page={p}" class="page-num">{p}</a>'
                
                prev_page = p
            
            # Next button
            if page < total_pages:
                html += f'<a href="/?sort={sort_by}&order={sort_order}&page={page+1}" class="page-btn">Next â†’</a>'
            else:
                html += '<span class="page-btn disabled">Next â†’</span>'
            
            html += '</div>'
            return html
        
        html = """
        <html>
        <head>
            <title>Tonewood Price Comparison</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                h1 { color: #333; }
                .stats { background: #e8f5e9; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
                .filters { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .filters label { display: inline-block; width: 150px; font-weight: bold; }
                .filters select, .filters input { padding: 8px; margin: 10px 0; width: 300px; }
                .filters button { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
                .filters button:hover { background: #45a049; }
                table { width: 100%; background: white; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                th { background: #4CAF50; color: white; padding: 12px; text-align: left; cursor: pointer; user-select: none; }
                th:hover { background: #45a049; }
                th a { color: white; text-decoration: none; display: block; }
                td { padding: 12px; border-bottom: 1px solid #ddd; font-size: 14px; }
                tr:hover { background: #f5f5f5; }
                a { color: #4CAF50; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .sort-info { background: #fff3cd; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 14px; }
                
                /* Pagination styles */
                .pagination { 
                    display: flex; 
                    justify-content: center; 
                    align-items: center; 
                    gap: 8px; 
                    margin: 20px 0; 
                    padding: 20px;
                    background: white;
                    border-radius: 8px;
                }
                .page-btn, .page-num { 
                    padding: 8px 12px; 
                    border: 1px solid #ddd; 
                    border-radius: 4px; 
                    background: white;
                    color: #333;
                    text-decoration: none;
                    transition: all 0.2s;
                }
                .page-btn:hover, .page-num:hover { 
                    background: #4CAF50; 
                    color: white; 
                    border-color: #4CAF50;
                }
                .page-num.active { 
                    background: #4CAF50; 
                    color: white; 
                    border-color: #4CAF50;
                    font-weight: bold;
                }
                .page-btn.disabled { 
                    color: #ccc; 
                    cursor: not-allowed;
                    border-color: #eee;
                }
                .page-btn.disabled:hover {
                    background: white;
                    color: #ccc;
                }
                .page-ellipsis { 
                    padding: 8px 4px; 
                    color: #666; 
                }
                /* Staleness indicator styles */
                .stale-fresh  { color: #2e7d32; font-size: 12px; }
                .stale-warn   { color: #e65100; font-size: 12px; }
                .stale-old    { color: #c62828; font-size: 12px; font-weight: bold; }
                .showing-info {
                    text-align: center;
                    color: #666;
                    margin: 10px 0;
                    font-size: 14px;
                }
                .collapse-btn {
                    background: #2196F3;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 12px;
                    margin-left: 10px;
                }
                .collapse-btn:hover {
                    background: #1976D2;
                }
            </style>
        </head>
        <body>
            <h1>ðŸŽ¸ Tonewood Price Comparison</h1>
            
            <div class="stats">
                <strong>Database:</strong> """ + str(total_count) + """ products from """ + str(len(vendors)) + """ vendors
            </div>
            
            <div class="filters">
                <h3>Search Products <button type="button" class="collapse-btn" onclick="toggleFilters()">â–¼ Hide Filters</button></h3>
                <form action="/search" method="get">
                    <label>Species:</label>
                    <select name="species_id">
                        <option value="">All Species</option>
        """
        
        for s in species_list:
            commercial = s.commercial_name if s.commercial_name else s.scientific_name
            html += f'<option value="{s.species_id}">{commercial}</option>\n'
        
        html += """
                    </select><br>
                    
                    <label>Vendor:</label>
                    <select name="vendor_id">
                        <option value="">All Vendors</option>
        """
        
        for v in vendors:
            html += f'<option value="{v.vendor_id}">{v.name} ({v.country})</option>\n'
        
        html += """
                    </select><br>
                    
                    <label>Category:</label>
                    <select name="category_id" id="category_select" onchange="updateFormatFilter()">
                        <option value="">All Categories</option>
        """
        
        for c in categories:
            html += f'<option value="{c.category_id}">{c.name}</option>\n'
        
        html += """
                    </select><br>
                    
                    <div id="format_filter_container" style="display: none;">
                        <label>Format:</label>
                        <select name="format_id" id="format_select">
                            <option value="">All Formats</option>
                        </select><br>
                    </div>
                    
                    <label>Max Price:</label>
                    <input type="number" name="max_price" placeholder="e.g., 500"><br>
                    
                    <button type="submit">ðŸ” Search</button>
                </form>
            </div>
            
            <script>
                // Format data by category
                const formatsByCategory = {
        """
        
        # Add format data as JavaScript object
        for cat_id, formats in formats_by_category.items():
            format_list = []
            for f in formats:
                # Escape quotes in format name for JavaScript
                safe_name = f.name.replace('"', '\\"').replace("'", "\\'")
                format_list.append(f'{{"id": {f.format_id}, "name": "{safe_name}"}}')
            html += f'        "{cat_id}": [{", ".join(format_list)}],\n'
        
        html += """
                };
                
                function toggleFilters() {
                    const form = document.querySelector('.filters form');
                    const btn = document.querySelector('.collapse-btn');
                    if (form.style.display === 'none') {
                        form.style.display = 'block';
                        btn.textContent = 'â–¼ Hide Filters';
                    } else {
                        form.style.display = 'none';
                        btn.textContent = 'â–¶ Show Filters';
                    }
                }
                
                function updateFormatFilter() {
                    console.log('updateFormatFilter called');
                    const categorySelect = document.getElementById('category_select');
                    const formatContainer = document.getElementById('format_filter_container');
                    const formatSelect = document.getElementById('format_select');
                    
                    const categoryId = categorySelect.value;
                    
                    if (!categoryId) {
                        formatContainer.style.display = 'none';
                        return;
                    }
                    
                    // Show format filter
                    formatContainer.style.display = 'block';
                    
                    // Clear existing options
                    formatSelect.innerHTML = '<option value="">All Formats</option>';
                    
                    // Get formats for this category
                    const formats = formatsByCategory[categoryId] || [];
                    
                    // Add format options
                    formats.forEach(format => {
                        const option = document.createElement('option');
                        option.value = format.id;
                        option.textContent = format.name;
                        formatSelect.appendChild(option);
                    });
                }
            </script>
        """
        
        # Add pagination at top
        html += pagination_html()
        
        html += f"""
            <div class="sort-info">
                ðŸ’¡ <strong>Tip:</strong> Click any column header to sort by that column
            </div>

            <div class="showing-info">
                Showing products {start_item} to {end_item} of {total_count}
            </div>
            
            <table>
                <tr>
                    <th><a href='""" + species_url + """'>Species""" + species_arrow + """</a></th>
                    <th><a href='""" + vendor_url + """'>Vendor""" + vendor_arrow + """</a></th>
                    <th><a href='""" + category_url + """'>Category""" + category_arrow + """</a></th>
                    <th><a href='""" + format_url + """'>Format""" + format_arrow + """</a></th>
                    <th><a href='""" + grade_url + """'>Grade""" + grade_arrow + """</a></th>
                    <th><a href='""" + price_url + """'>Price""" + price_arrow + """</a></th>
                    <th>Updated</th>
                    <th>Link</th>
                </tr>
        """
        
        for p in products:
            commercial = p.species.commercial_name if p.species.commercial_name else p.species.scientific_name
            grade = p.grade.name if p.grade else "-"
            format_name = p.format.name if p.format else "-"
            
            html += f"""
                <tr>
                    <td><strong>{commercial}</strong></td>
                    <td>{p.vendor.name}</td>
                    <td>{p.category.name}</td>
                    <td>{format_name}</td>
                    <td>{grade}</td>
                    <td><strong>{p.price:.2f} SEK</strong></td>
                    """ + staleness_cell(p.last_updated) + f"""
                    <td><a href="{p.product_url}" target="_blank">View â†’</a></td>
                </tr>
            """
        
        html += """
            </table>
        """
        
        # Add pagination at bottom
        html += pagination_html()
        
        html += """
        </body>
        </html>
        """
        
        return html
        
    except Exception as e:
        return f"<h1>Error loading page</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>"
""" HOMEPAGE END """

""" SEARCH START """
@app.route('/search')
def search():
    """Search products with filters"""
    species_id = request.args.get('species_id', type=int)
    vendor_id = request.args.get('vendor_id', type=int)
    category_id = request.args.get('category_id', type=int)
    format_id = request.args.get('format_id', type=int)
    max_price = request.args.get('max_price', type=float)
    sort_by = request.args.get('sort', 'price')
    sort_order = request.args.get('order', 'asc')
    
    # Build query with filters
    query = Product.query
    
    if species_id:
        query = query.filter_by(species_id=species_id)
    if vendor_id:
        query = query.filter_by(vendor_id=vendor_id)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if format_id:
        query = query.filter_by(format_id=format_id)
    if max_price:
        query = query.filter(Product.price <= max_price)
    
    # Apply sorting
    if sort_by == 'species':
        query = query.join(Species).order_by(Species.commercial_name.asc() if sort_order == 'asc' else Species.commercial_name.desc())
    elif sort_by == 'vendor':
        query = query.join(Vendor).order_by(Vendor.name.asc() if sort_order == 'asc' else Vendor.name.desc())
    elif sort_by == 'category':
        query = query.join(Category).order_by(Category.name.asc() if sort_order == 'asc' else Category.name.desc())
    elif sort_by == 'price':
        query = query.order_by(Product.price.asc() if sort_order == 'asc' else Product.price.desc())
    elif sort_by == 'grade':
        query = query.outerjoin(Grade).order_by(Grade.name.asc() if sort_order == 'asc' else Grade.name.desc())
    elif sort_by == 'format':
            query = query.outerjoin(Format).order_by(Format.name.asc() if sort_order == 'asc' else Format.name.desc())
    else:
        query = query.order_by(Product.price.asc())
    
    products = query.all()
    
    # Function to generate sort URL with current filters
    def sort_url(column):
        if sort_by == column:
            new_order = 'desc' if sort_order == 'asc' else 'asc'
            arrow = ' â–²' if sort_order == 'asc' else ' â–¼'
        else:
            new_order = 'asc'
            arrow = ''
        
        # Build URL with filters preserved
        params = []
        if species_id:
            params.append(f'species_id={species_id}')
        if vendor_id:
            params.append(f'vendor_id={vendor_id}')
        if category_id:
            params.append(f'category_id={category_id}')
        if max_price:
            params.append(f'max_price={max_price}')
        params.append(f'sort={column}')
        params.append(f'order={new_order}')
        
        return f'/search?{"&".join(params)}', arrow
    
    species_url, species_arrow = sort_url('species')
    vendor_url, vendor_arrow = sort_url('vendor')
    category_url, category_arrow = sort_url('category')
    price_url, price_arrow = sort_url('price')
    grade_url, grade_arrow = sort_url('grade')
    format_url, format_arrow = sort_url('format')

    
    # Build filter description
    filters_applied = []
    if species_id:
        sp = Species.query.get(species_id)
        if sp:
            filters_applied.append(f"Species: {sp.commercial_name or sp.scientific_name}")
    if vendor_id:
        v = Vendor.query.get(vendor_id)
        if v:
            filters_applied.append(f"Vendor: {v.name}")
    if category_id:
        c = Category.query.get(category_id)
        if c:
            filters_applied.append(f"Category: {c.name}")
    if format_id:
        f = Format.query.get(format_id)
        if f:
            filters_applied.append(f"Format: {f.name}")
    if max_price:
        filters_applied.append(f"Max Price: {max_price}")
    
    filter_text = " | ".join(filters_applied) if filters_applied else "No filters"
    
    html = f"""
    <html>
    <head>
        <title>Search Results - Tonewood</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            h1 {{ color: #333; }}
            .back {{ margin-bottom: 20px; }}
            .back a {{ color: #4CAF50; text-decoration: none; font-size: 18px; }}
            .back a:hover {{ text-decoration: underline; }}
            .filters-applied {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            .sort-info {{ background: #fff3cd; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 14px; }}
            table {{ width: 100%; background: white; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            th {{ background: #4CAF50; color: white; padding: 12px; text-align: left; cursor: pointer; user-select: none; }}
            th:hover {{ background: #45a049; }}
            th a {{ color: white; text-decoration: none; display: block; }}
            td {{ padding: 12px; border-bottom: 1px solid #ddd; font-size: 14px; }}
            tr:hover {{ background: #f5f5f5; }}
            a {{ color: #4CAF50; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .no-results {{ background: white; padding: 40px; text-align: center; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <div class="back"><a href="/">â† Back to All Products</a></div>
        <h1>ðŸ” Search Results</h1>
        
        <div class="filters-applied">
            <strong>Filters:</strong> {filter_text}
        </div>
        
        <div class="sort-info">
            ðŸ’¡ <strong>Tip:</strong> Click any column header to sort results
        </div>
    """
    
    if len(products) == 0:
        html += """
        <div class="no-results">
            <h2>ðŸ˜• No products found</h2>
            <p>Try adjusting your filters or <a href="/">view all products</a></p>
        </div>
        """
    else:
        html += f"""
        <h3>Found {len(products)} product{"s" if len(products) != 1 else ""}</h3>
        <table>
            <tr>
                <th><a href='{species_url}'>Species{species_arrow}</a></th>
                <th><a href='{vendor_url}'>Vendor{vendor_arrow}</a></th>
                <th><a href='{category_url}'>Category{category_arrow}</a></th>
                <th><a href='""" + format_url + """'>Format""" + format_arrow + """</a></th>
                <th><a href='{grade_url}'>Grade{grade_arrow}</a></th>
                <th><a href='{price_url}'>Price{price_arrow}</a></th>
                <th>Updated</th>
                <th>Link</th>
            </tr>
        """
        
        for p in products:
            commercial = p.species.commercial_name if p.species.commercial_name else p.species.scientific_name
            grade = p.grade.name if p.grade else "-"
            format_name = p.format.name if p.format else "-"
            
            html += f"""
                <tr>
                    <td><strong>{commercial}</strong></td>
                    <td>{p.vendor.name}</td>
                    <td>{p.category.name}</td>
                    <td>{format_name}</td>
                    <td>{grade}</td>
                    <td><strong>{p.price:.2f} {p.currency}</strong></td>
                    """ + staleness_cell(p.last_updated) + f"""
                    <td><a href="{p.product_url}" target="_blank">View â†’</a></td>
                </tr>
            """
        
        html += """
        </table>
        """
    
    html += """
    </body>
    </html>
    """
    
    return html
""" SEARCH END """

if __name__ == '__main__':
    print("\n" + "="*50)
    print("ðŸŽ¸ Tonewood Price Comparison is starting...")
    print("Open your browser and go to: http://localhost:5000")
    print("Press CTRL+C to stop the server")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)