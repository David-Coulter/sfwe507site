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

- **Backend:** Django 4.2+
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
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Create a superuser:**
   ```bash
   python manage.py createsuperuser
   ```

5. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

6. **Access the application:**
   - Main site: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

---

## Project Structure

```
507site/
├── 507site/              # Project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── main/                 # Main application
│   ├── models.py         # Task, Sprint models
│   ├── views.py          # View functions
│   ├── forms.py          # Task creation forms
│   ├── urls.py           # URL routing
│   ├── admin.py          # Admin configuration
│   ├── templatetags/     # Custom template filters
│   │   └── markdown_extras.py
│   └── templates/        # HTML templates
│       ├── base.html
│       └── main/
│           ├── dashboard.html
│           ├── task_form.html
│           └── task_detail.html
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