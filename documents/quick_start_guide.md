# Quick Start Guide - Tonewood Price Comparison

Get your tonewood database up and running in under 10 minutes!

---

## Prerequisites

✅ **macOS** (10.15 or later)  
✅ **Python 3.9+** installed  
✅ **Your Excel file** with tonewood data  

Check Python version:
```bash
python3 --version
```

---

## Installation (5 Minutes)

### Step 1: Install Required Packages

Open Terminal and run:

```bash
pip3 install flask flask-sqlalchemy pandas openpyxl
```

**What this installs:**
- `flask` - Web framework
- `flask-sqlalchemy` - Database toolkit
- `pandas` - Excel file reader
- `openpyxl` - Excel format support

⏱️ Takes about 1-2 minutes

---

### Step 2: Create Project Folder

```bash
mkdir ~/tonewood-app
cd ~/tonewood-app
```

This creates a folder on your Desktop and moves into it.

---

### Step 3: Add Your Files

You need **4 files** in your `tonewood-app` folder:

1. **models.py** - Database structure (from documentation)
2. **app.py** - Web application (from documentation)
3. **import_data.py** - Data importer (from documentation)
4. **Tonewood_Species__With_Sources_v2_2.xlsx** - Your Excel file

**Pro Tip:** Open the folder in Visual Studio Code to easily manage files!

---

### Step 4: Import Your Data

In Terminal, from your `tonewood-app` folder:

```bash
python3 import_data.py
```

**Follow the prompts:**
1. Choose option **2** (file in tonewood-app folder)
2. Enter: `Tonewood_Species__With_Sources_v2_2.xlsx`
3. Wait ~30 seconds

**Expected output:**
```
✅ IMPORT COMPLETE!

Total species: 103
Total vendors: 4
Total products: 969
```

If you see this, you're golden! ✨

---

### Step 5: Launch the Application

```bash
python3 app.py
```

**You should see:**
```
==================================================
🎸 Tonewood Price Comparison is starting...
Open your browser and go to: http://localhost:5000
Press CTRL+C to stop the server
==================================================
```

---

### Step 6: Open in Browser

Open your favorite browser and navigate to:

```
http://localhost:5000
```

**You should see:**
- Search filters at the top
- Green "Search" button
- Table with 50 products
- Pagination at the bottom

🎉 **Congratulations! Your system is live!**

---

## Quick Tour

### Using Search Filters

1. **Click "Species" dropdown** - Select "Mahogany" or another wood
2. **Click "🔍 Search"** - See only those products
3. **Notice the format filter appears** after selecting a category!

### Sorting Columns

- **Click any column header** (Species, Vendor, Price, etc.)
- Arrow shows sort direction (▲ ascending, ▼ descending)
- Click again to reverse

### Browsing Pages

- **Use page numbers** at bottom to jump to specific pages
- **Previous/Next buttons** for sequential browsing
- Shows "X to Y of 969" products

### Collapsing Filters

- **Click "▼ Hide Filters"** to maximize table space
- **Click "▶ Show Filters"** to restore

---

## Daily Use

### Starting the Application

```bash
cd ~/tonewood-app
python3 app.py
```

Open browser to `http://localhost:5000`

### Stopping the Application

In Terminal, press **Ctrl+C**

### Updating Prices

1. **Update your Excel file** with new prices
2. **Delete the database:**
   ```bash
   rm tonewood.db
   ```
3. **Re-import:**
   ```bash
   python3 import_data.py
   ```
4. **Restart the app:**
   ```bash
   python3 app.py
   ```

---

## Common First-Time Issues

### "Port 5000 already in use"

**Problem:** Another app is using port 5000  
**Solution:**
```bash
lsof -ti:5000 | xargs kill -9
python3 app.py
```

### "No module named 'flask'"

**Problem:** Packages not installed  
**Solution:**
```bash
pip3 install flask flask-sqlalchemy pandas openpyxl
```

### "File not found" during import

**Problem:** Excel file not in correct location  
**Solution:** Make sure Excel file is in `tonewood-app` folder

### Blank page in browser

**Problem:** Database not created or empty  
**Solution:**
```bash
python3 -c "from app import app, db; from models import Product; app.app_context().push(); print(Product.query.count())"
```

Should show `969`. If it shows `0`, re-run import.

---

## Next Steps

Once your system is running:

1. **Try different searches** - Get familiar with filters
2. **Sort by price** - Find best deals
3. **Browse by vendor** - Compare suppliers
4. **Check the Implementation Guide** - Learn advanced features

---

## Quick Reference Card

```
┌─────────────────────────────────────────┐
│  TONEWOOD APP - QUICK COMMANDS         │
├─────────────────────────────────────────┤
│  Start:     python3 app.py              │
│  Stop:      Ctrl+C                      │
│  Import:    python3 import_data.py      │
│  Reset DB:  rm tonewood.db              │
│  URL:       http://localhost:5000       │
└─────────────────────────────────────────┘
```

---

## Getting Help

If something doesn't work:

1. ✅ Check this guide's troubleshooting section
2. ✅ Look at terminal output for error messages
3. ✅ Open browser console (F12) for JavaScript errors
4. ✅ Review Implementation Guide for detailed explanations

---

## What You've Built

In just 10 minutes, you've created:

- **Normalized database** with 969 products
- **Web application** with search and filtering
- **Dynamic interface** with sorting and pagination
- **Smart format filtering** based on category
- **Professional tool** for price comparison

**That's impressive!** 🎸

---

## Pro Tips

💡 **Use Visual Studio Code** for easier file management  
💡 **Bookmark localhost:5000** for quick access  
💡 **Keep Excel file backed up** - it's your source of truth  
💡 **Try keyboard shortcuts** in VS Code (see Implementation Guide)  
💡 **Explore features** - click everything to see what it does!

---

## Ready for More?

Check out:
- **README.md** - Complete system overview
- **Implementation Guide** - Deep technical details
- **Database Schema Diagram** - Visual table relationships

Happy price comparing! 🚀
