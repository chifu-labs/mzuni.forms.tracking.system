# Mzuzu University Digital Document Tracking System

## Default Admin Login
- **Employee ID:** `ADMIN001`
- **Password:** `Admin@1234`

---

## DEPLOYING ON PYTHONANYWHERE (Step-by-Step)

### 1. Upload your files
- Zip the project folder and upload it via the PythonAnywhere **Files** tab
- Unzip it: open a **Bash console** and run:
  ```
  cd ~
  unzip UPCOMMING_FIXED.zip
  ```
  Your files will be at `/home/yourusername/still/`

### 2. Install dependencies
In the Bash console:
```
pip3.10 install --user -r ~/still/requirements.txt
```

### 3. Configure the Web App
- Go to the **Web** tab → **Add a new web app**
- Choose **Manual configuration** → **Python 3.10**
- Set **Source code** to: `/home/yourusername/still`
- Set **Working directory** to: `/home/yourusername/still`

### 4. Edit the WSGI file
- In the Web tab, click the **WSGI configuration file** link
- Delete everything in it and replace with:
```python
import sys, os
project_home = '/home/yourusername/still'
if project_home not in sys.path:
    sys.path.insert(0, project_home)
from app import create_app
application = create_app()
```
*(Replace `yourusername` with your actual PythonAnywhere username)*

### 5. Set up Static Files
In the Web tab under **Static files**, add:
- **URL:** `/static/`
- **Directory:** `/home/yourusername/still/static`

### 6. Configure Email (optional but recommended)
Edit `/home/yourusername/still/.env` and set your Gmail credentials:
```
MAIL_USERNAME=your-gmail@gmail.com
MAIL_PASSWORD=your-app-password
```
To get a Gmail App Password: https://myaccount.google.com/apppasswords

### 7. Reload and go
- Click **Reload** in the Web tab
- Visit `https://yourusername.pythonanywhere.com`

---

## FORMS INCLUDED
| Form | Ref Number | Workflow Steps |
|------|-----------|----------------|
| Request for Use of Funds for Internal Travel and Subsistence | ADM/02/11/13 | 6 |
| Request for Use of Funds for Procurement | ADM/08/11/13 | 7 |
| Staff Booking Transport Form | TRANS/01/08/13 | 3 |
| Fuel Requisition | FUEL/01 | 4 |

## USER ROLES
Sender, Department Officer, Head of Department, Registry Officer, Finance Officer,
Human Resource Officer, ICT Administrator, System Administrator, Vice Chancellor,
Director of Finance, Dean/Principal Officer, Transport Officer, Chief Procurement Officer

## PROJECT STRUCTURE
```
still/
├── app.py              # Application factory + WSGI entry
├── wsgi.py             # PythonAnywhere WSGI reference file
├── .env                # Email credentials and secret key
├── extensions.py       # Flask extensions (db, login, mail)
├── requirements.txt
├── models/models.py    # All database models
├── routes/
│   ├── auth.py         # Login, register, password reset
│   ├── dashboard.py    # Sender dashboard
│   ├── forms.py        # Form submission, officer review, approval
│   └── admin.py        # Admin panel
├── utils/
│   ├── officers.py     # Hardcoded officer list (fallback)
│   └── seed.py         # Initial roles, departments, form types
├── templates/
│   ├── base.html
│   ├── auth/
│   ├── dashboard/
│   ├── forms/          # All 4 digital forms
│   └── admin/
└── static/
    ├── css/main.css
    ├── js/main.js
    └── signatures/     # Signature images stored here
```
