# Campus Connect — Integrated Student Enrollment and Information System

A complete university system that combines **Laboratory 3** (Student Course Management API)
and **Laboratory 4** (Campus Connect Student Information Portal) into one project:

* **Frontend** — the Campus Connect dashboard (React web app) that talks to the API over HTTP.
* **Backend** — Python + Flask REST API in this folder.
* **Database** — SQLite file created automatically on first run.

Everything is fictional sample data for classroom use.

---

## 1. What is inside this folder

| File | Purpose |
| --- | --- |
| **app.py** | The whole Flask backend: app setup, database helpers, all REST endpoints, validation, error handling, and automatic sample data. |
| **requirements.txt** | Python packages the project needs (Flask, flask-cors, Werkzeug, gunicorn). |
| **database.db** | The SQLite database. Created automatically the first time app.py runs. Never commit it to GitHub. |
| **run.bat** | Windows one-click starter: creates a virtual environment, installs requirements, runs the server. |
| **start.bat** | Starts run.bat in its own window and opens the API explorer in your browser. |
| **templates/index.html** | Small page Flask serves at http://127.0.0.1:5000 so you can see the API working on its own. |
| **static/css/style.css** | Styling for that page. |
| **static/javascript/script.js** | Fetches /api/stats and /api/students and renders them on the page. |
| **static/images/** | Optional images for your presentation. |
| **screenshots/** | Place your laboratory screenshots here. |
| **render.yaml** | Deployment blueprint for Render. |
| **.gitignore** | Keeps the database, virtual environment and secrets out of Git. |

The main Campus Connect interface is the separate React frontend. This folder is only the
backend it calls.

---

## 2. Folder structure

~~~
Campus-Connect/
├── app.py
├── requirements.txt
├── README.md
├── run.bat
├── start.bat
├── render.yaml
├── .gitignore
├── database.db              (created automatically)
├── templates/
│   └── index.html
├── static/
│   ├── css/style.css
│   ├── javascript/script.js
│   └── images/
└── screenshots/
    └── README.md
~~~

---

## 3. Run it on Windows (easiest)

1. Install Python 3.10 or newer from python.org — tick **Add Python to PATH** during setup.
2. Put the Campus-Connect folder anywhere, for example on your Desktop.
3. Double-click **run.bat**.
4. Wait until you see:

~~~
Running on http://127.0.0.1:5000
~~~

5. Open http://127.0.0.1:5000 in your browser to confirm the API is alive.
6. Keep that window open while you use the Campus Connect frontend.
7. To stop the server press **CTRL + C** in the window, or close it.

**start.bat** does the same thing and opens the browser for you.

## 4. Run it on macOS or Linux

~~~
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
~~~

---

## 5. REST API endpoints

Base URL while developing: **http://127.0.0.1:5000/api**

All requests and responses use JSON.

### Students
| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /api/students | List students. Optional **?search=maria** |
| GET | /api/students/1 | One student plus their enrollment history |
| POST | /api/students | Create a student |
| PUT | /api/students/1 | Update a student |
| DELETE | /api/students/1 | Delete a student (their enrollments go too) |

### Courses (Laboratory 3)
| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /api/courses | List courses. Optional **?search=CS** |
| GET | /api/courses/1 | One course plus its enrolled students |
| POST | /api/courses | Create a course |
| PUT | /api/courses/1 | Update a course |
| DELETE | /api/courses/1 | Delete a course |

### Enrollments (combined feature)
| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /api/enrollments | Enrollment records joined with student and course names |
| GET | /api/enrollments/1 | One enrollment |
| POST | /api/enrollments | Enroll a student (rejects duplicates with 409) |
| PUT | /api/enrollments/1 | Change status: Pending, Approved, Rejected, Cancelled |
| DELETE | /api/enrollments/1 | Remove the record |

### Announcements (Laboratory 4)
| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /api/announcements | List announcements |
| POST | /api/announcements | Create an announcement |
| PUT | /api/announcements/1 | Edit an announcement |
| DELETE | /api/announcements/1 | Delete an announcement |

### Support
| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /api/health | Connection check: service name, database path, table list |
| GET | /api/stats | Dashboard counters and the 7-day enrollment trend |
| GET | /api/users | App users (passwords are never returned) |

Example request:

~~~
POST http://127.0.0.1:5000/api/students
Content-Type: application/json

{
  "student_number": "2024-00107",
  "first_name": "Liza",
  "last_name": "Ramos",
  "email": "liza.ramos@campusconnect.edu",
  "program": "BS Computer Science",
  "year_level": 2,
  "contact_number": "0917 555 0101"
}
~~~

Success returns **201 Created** with the saved row. Validation problems return **400**,
duplicates return **409**, and missing records return **404** — always with an
**{"error": "message"}** body.

---

## 6. Database tables

SQLite file: **database.db**

* **students** — student_id (PK), student_number (unique), first_name, last_name, email (unique), program, year_level, contact_number, created_at
* **courses** — course_id (PK), course_code (unique), course_name, department, units, created_at
* **enrollments** — enrollment_id (PK), student_id (FK → students), course_id (FK → courses), enrollment_date, status
* **announcements** — announcement_id (PK), title, content, author, date_posted
* **users** — user_id (PK), username (unique), password_hash, full_name, role

Foreign keys are enabled, and deleting a student or a course removes their enrollments.
A unique index stops the same student from holding two active enrollments in one course.

To inspect the data, open **database.db** with DB Browser for SQLite and browse the
*Browse Data* tab.

---

## 7. How Laboratory 3 and Laboratory 4 are integrated

~~~
Browser (Campus Connect frontend)
        |  HTTP + JSON
        v
Flask REST API  (app.py)
        |  SQL (sqlite3)
        v
SQLite database (database.db)
~~~

* **Laboratory 3** gave us the course management API: course_code, course_name, department,
  and the GET/POST/PUT/DELETE endpoints. Those endpoints still live under /api/courses and
  still use the same field names.
* **Laboratory 4** gave us the portal: students, announcements, and the dashboard view.
* **The integration** is the enrollments module. An enrollment row stores a student_id and a
  course_id — two foreign keys that connect the Laboratory 4 students table with the
  Laboratory 3 courses table. The GET /api/enrollments query joins all three tables so the
  frontend can show the student name and the course code in one row.

Nothing is duplicated: there is one Flask app, one database, and one set of endpoints.

---

## 8. Connecting the frontend

1. Start this backend (run.bat).
2. Open the Campus Connect frontend.
3. Go to **API Connection** in the sidebar.
4. Keep **http://127.0.0.1:5000/api** and press **Save & test**.
5. The sidebar badge turns green and every screen now reads and writes real database records.

If the API is unreachable the frontend clearly labels the data as sample data and disables
saving, so a failed request is never shown as a success.

---

## 9. Testing checklist

| # | Action | Expected result |
| --- | --- | --- |
| 1 | Open the dashboard | Counters match the rows in SQLite |
| 2 | Add a student | 201 Created, the new row appears in the table |
| 3 | Add a course | 201 Created, the course appears in the catalog |
| 4 | View the course list | Every course code and department is shown |
| 5 | Edit a course | 200 OK, the change is visible immediately |
| 6 | Delete a course | 200 OK, the row disappears |
| 7 | Enroll a student | 201 Created with status Pending |
| 8 | Enroll the same pair again | 409 Conflict — "already enrolled" |
| 9 | Update enrollment status | 200 OK, the badge changes to Approved |
| 10 | Cancel an enrollment | Status becomes Cancelled |
| 11 | Create an announcement | It appears on the dashboard |
| 12 | Open a student profile | Personal details plus enrollment history |
| 13 | Reopen the app | The data is still there (it lives in SQLite, not the browser) |

You can also test the API alone with the browser page at http://127.0.0.1:5000 or with
Postman / Thunder Client.

---

## 10. Upload to GitHub

1. Create a new repository on github.com named **campus-connect** (no README, no .gitignore).
2. Open a terminal in the Campus-Connect folder and run:

~~~
git init
git add .
git commit -m "Campus Connect: Flask REST API with SQLite"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/campus-connect.git
git push -u origin main
~~~

3. Later updates:

~~~
git add .
git commit -m "Describe what you changed"
git push
~~~

**Never commit** database.db, venv/, or a .env file — .gitignore already excludes them.
Never put real passwords or secret keys in the repository.

---

## 11. Deploy the backend to Render

1. Push the project to GitHub (section 10).
2. Sign in at render.com and choose **New → Web Service**.
3. Connect your GitHub account and pick the **campus-connect** repository.
4. Fill in:
   * **Runtime**: Python 3
   * **Build Command**: **pip install -r requirements.txt**
   * **Start Command**: **gunicorn app:app**
   * **Instance type**: Free is fine for a class demo.
5. Add environment variables:
   * **PYTHON_VERSION** = 3.11.9
   * **DATABASE_PATH** = /var/data/database.db
6. (Recommended) Add a **Disk**: name campus-connect-data, mount path **/var/data**, 1 GB.
   Persistent disks are a paid feature; on the free plan SQLite is rebuilt with the sample
   data whenever the service redeploys or restarts.
7. Press **Create Web Service** and wait for the build to finish.
8. Your API now lives at **https://YOUR-SERVICE.onrender.com/api**. Open
   https://YOUR-SERVICE.onrender.com/api/health to confirm it responds.
9. In the Campus Connect frontend open **API Connection**, paste that URL (with /api at the
   end) and press **Save & test**.

Localhost URLs never work after deployment: on the internet your backend has its own address.

---

## 12. Troubleshooting

| Problem | Fix |
| --- | --- |
| **'python' is not recognized** | Reinstall Python and tick "Add Python to PATH", or run **py app.py**. |
| **Port 5000 already in use** | Stop the other program, or run **set PORT=5001 && python app.py** and use that port in the frontend. |
| **Frontend says it cannot reach the API** | The Flask window must stay open; check the address ends with /api. |
| **CORS error in the browser console** | flask-cors is enabled in app.py — make sure you installed requirements.txt. |
| **Data disappeared after redeploying on Render** | The free plan has no persistent disk; attach one (section 11, step 6). |
| **database.db is locked** | Close DB Browser for SQLite before writing from the app. |

---

Campus Connect · Integrated Student Enrollment and Information System · fictional sample data
