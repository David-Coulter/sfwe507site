# Product Development Management System (PDMS)

A Django-based Agile project management system for tracking tasks through a complete development workflow.

**Course:** SFWE507 - Software Engineering  
**Team:** Team 6 
**Instructor:** Dr. Saldana

---

## Features

- ✅ Product Backlog management
- ✅ Sprint planning and tracking
- ✅ Testing workflow (Ready for Test → Pass/Fail)
- ✅ Task prioritization (Critical, High, Medium, Low)
- ✅ Markdown support for task descriptions
- ✅ Story points and time estimation
- ✅ User assignment and tracking

---

## Tech Stack

- **Backend:** Django 5.2+
- **Database:** SQLite (development)
- **Frontend:** Bootstrap 5, Bootstrap Icons
- **Styling:** University of Arizona brand colors

---

## Setup Instructions

### Prerequisites

- Python 3.11+
- pip

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/David-Coulter/sfwe507site.git
   cd 507site
   ```

2. **Install dependencies:**

   **System dependencies:**
      **macOS:**
      ```bash
         brew install cairo pango gdk-pixbuf libffi
      ```

      **Ubuntu/Debian:**
      ```bash
         sudo apt-get install build-essential python3-dev python3-pip \
         libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev
      ```
      **Windows:**
      - Download and install GTK3 runtime from [here](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer)

   **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Configure email (optional - for sprint report emails):**
   
   Edit `507site/settings.py`:
   ```python
      # For development/testing (emails print to console):
      EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
      
      # For production (requires SMTP):
      # EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
      # EMAIL_HOST = 'smtp.gmail.com'
      # EMAIL_PORT = 587
      # EMAIL_USE_TLS = True
      # EMAIL_HOST_USER = 'your-email@gmail.com'
      # EMAIL_HOST_PASSWORD = 'your-app-password'
      # DEFAULT_FROM_EMAIL = 'your-email@gmail.com'
   ```

5. **Create a superuser:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

7. **Access the application:**
   - Main site: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

---

## Project Structure

```
507site/
├── 507site/              # Project settings
│   ├── settings.py       # Django configuration
│   ├── urls.py           # Root URL routing
│   └── wsgi.py           # WSGI configuration
├── main/                 # Main application
│   ├── models.py         # Task, Sprint, TaskHistory models
│   ├── views.py          # View functions and business logic
│   ├── forms.py          # Task and Sprint forms
│   ├── urls.py           # URL routing
│   ├── admin.py          # Admin panel configuration
│   ├── templatetags/     # Custom template filters
│   │   └── markdown_extras.py
│   ├── templates/        # HTML templates
│   │   ├── base.html     # Base template with UA branding
│   │   ├── main/
│   │       ├── complete_sprint.html
│   │       ├── completed_tasks.html
│   │       ├── dashboard.html
│   │       ├── fail_testing.html
│   │       ├── product_backlog.html
│   │       ├── reopen_sprint_confirm.html
│   │       ├── sprint_backlog.html
│   │       ├── sprint_board.html
│   │       ├── sprint_burndown.html
│   │       ├── sprint_form.html
│   │       ├── sprint_report_pdf.html
│   │       ├── sprint_report.html
│   │       ├── task_detail.html
│   │       ├── task_form.html
│   │       ├── task_list.html
│   │       ├── testing_queue.html
│   |   └── registration/
│   │       ├── login.html
│   │       └── register.html
│   └── tests/            # Automated tests
│       ├── test_epic_3.py 
│       ├── test_us_19.py 
│       ├── test_us_22.py 
│       ├── test_us_23.py 
│       ├── test_us_23.py 
│       └── tests.py
├── manage.py
└── requirements.txt
```

---

## Workflow

```
Product Backlog → Sprint Backlog → Ready for Test → Complete
                                         ↓
                                  Failed (Re-work)
```

---

## Development

### Running Tests
```bash
python manage.py test
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Accessing Admin Panel
1. Create superuser (if not already done)
2. Go to http://127.0.0.1:8000/admin/
3. Log in with superuser credentials

---

## Team Members

- Angela Miller 
- Dallas Prewitt
- David Coulter

---

## Contributing

1. Create a feature branch: `git checkout -b feature/US-XX-description`
2. Make your changes
3. Commit: `git commit -m "Implement US-XX: Description"`
4. Push: `git push origin feature/US-XX-description`
5. Create Pull Request
6. Request review from team members

---

## Acknowledgments

- University of Arizona Brand Guidelines
- Django Documentation
- Bootstrap Framework
