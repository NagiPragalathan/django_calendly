# Acuity Scheduling Integration for Zoho CRM (Django Project)

This Django-based integration allows seamless synchronization and management of **Acuity Scheduling** appointments within your **Zoho CRM** account. Enhance productivity by managing appointments, contacts, and leads from a unified interface.

---

## Key Features

### 1. **Manage Appointments Directly from Zoho CRM**
   - Book, reschedule, and cancel appointments with customers directly from Zoho CRM.
   - Any changes in appointments made by customers in Acuity Scheduling are automatically updated in Zoho CRM.

### 2. **Seamless Contact and Lead Association**
   - Appointments booked on Acuity Scheduling by existing Zoho CRM Contacts/Leads are:
     - Automatically associated with those Contacts/Leads.
     - Added as events under the Activities module in Zoho CRM.

### 3. **Automatic Contact Creation**
   - New users booking appointments in Acuity Scheduling are:
     - Automatically added as Contacts in Zoho CRM.
     - Associated with the event in Zoho CRM.

### 4. **Send Your Availability in One Click**
   - Share your availability calendar with Zoho CRM Contacts and Leads via a single click.

---

## Project Structure

```plaintext
├── project_root/
│   ├── manage.py              # Django's management script
│   ├── settings/
│   │   ├── base.py            # Base settings
│   │   ├── development.py     # Development-specific settings
│   │   └── production.py      # Production-specific settings
│   ├── templates/             # HTML templates for the project
│   ├── static/                # Static files (CSS, JS, images)
│   ├── zoho_integration/      # Main app handling Zoho CRM and Acuity integration
│   │   ├── models.py          # Database models for Zoho Tokens, etc.
│   │   ├── views.py           # Views to handle Zoho API and OAuth
│   │   ├── urls.py            # URL routing for the integration app
│   │   ├── serializers.py     # Serializers for API communication
│   │   ├── forms.py           # Forms for user interaction
│   │   └── tests.py           # Unit tests
│   ├── requirements.txt       # Python dependencies
│   └── README.md              # Project documentation
```

## Installation

Follow these steps to set up the project locally:

### 1\. Clone the Repository

```bash
git clone https://github.com/your-username/acuity-zoho-integration.git cd acuity-zoho-integration
```

### 2\. Set Up a Virtual Environment

```bash
python3 -m venv venv source venv/bin/activate
```

### 3\. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4\. Configure Environment Variables

Create a `.env` file in the root directory and configure the following variables:


```bash
ZOHO_CLIENT_ID=your_client_id 
ZOHO_CLIENT_SECRET=your_client_secret 
ZOHO_REDIRECT_URI=http://127.0.0.1:8000/callback/ 
ACUITY_API_KEY=your_acuity_api_key
```

### 5\. Run Migrations

```bash 
python manage.py makemigrations python manage.py migrate
```

### 6\. Run the Development Server

```bash
python manage.py runserver
```

---

## Usage

1. **Authenticate Zoho CRM**:
    
    - Navigate to `http://127.0.0.1:8000/`.
    - Click the **Connect to Zoho CRM** button to authenticate your Zoho account.
    - On successful authentication, the app stores access and refresh tokens in the database.
2. **Sync Acuity Appointments**:
    
    - The app listens for changes in Acuity Scheduling and updates Zoho CRM Contacts/Leads and Activities accordingly.
3. **View and Manage Data**:
    
    - Use Zoho CRM to book, reschedule, or cancel appointments. Changes will sync automatically.

---

## Tech Stack

- **Backend**: Django
- **Frontend**: TailwindCSS, DaisyUI for templates
- **APIs**:
    - Zoho CRM API for managing Contacts, Leads, and Activities
    - Acuity Scheduling API for booking and appointment management
- **Database**: SQLite (development) / PostgreSQL (production)

---

## Resources

### Documentation

- Zoho CRM API Documentation
- Acuity Scheduling API Documentation

### Guides

- [Django Official Documentation](https://docs.djangoproject.com/)
- OAuth 2.0 Overview

---

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository.
2. Create a feature branch:
    
    ``` bash
    git checkout -b feature-name
    ```
    
3. Commit your changes:
    
    ``` bash
    git commit -m "Description of changes"
    ```
    
4. Push to the branch:
    
    ``` bash
    git push origin feature-name
    ```
    
5. Create a Pull Request.