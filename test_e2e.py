import unittest
from app import create_app
from app.database import get_db

class JobPortalTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        # Use an in-memory db or test db
        import os
        if os.path.exists('test_db.sqlite'):
            os.remove('test_db.sqlite')
        self.app.config['DATABASE'] = 'test_db.sqlite'
        self.client = self.app.test_client()

        with self.app.app_context():
            from app.database import init_db
            init_db(self.app)

    def test_full_workflow(self):
        # 1. Register Company
        res = self.client.post('/auth/register/company', data={
            'name': 'Test Corp',
            'email': 'company@test.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'industry': 'Tech'
        }, follow_redirects=True)
        self.assertIn(b'Company registered', res.data)

        # 2. Login Admin & Approve Company
        self.client.post('/auth/login', data={
            'email': 'admin@jobportal.com',
            'password': 'admin123',
            'role': 'admin'
        })
        with self.app.app_context():
            db = get_db()
            company = db.execute("SELECT id FROM companies WHERE email='company@test.com'").fetchone()
            cid = company['id']
        self.client.post(f'/admin/companies/{cid}/approve')
        self.client.get('/auth/logout')

        # 3. Login Company & Post Job
        self.client.post('/auth/login', data={
            'email': 'company@test.com',
            'password': 'password123',
            'role': 'company'
        })
        self.client.post('/company/post-job', data={
            'title': 'Software Engineer',
            'description': 'Develop things.',
            'requirements': 'Code',
            'skills_required': 'python, flask',
            'location': 'Remote',
            'job_type': 'Full-Time',
            'salary': '100k'
        })
        self.client.get('/auth/logout')

        # 4. Login Admin & Approve Job
        self.client.post('/auth/login', data={
            'email': 'admin@jobportal.com',
            'password': 'admin123',
            'role': 'admin'
        })
        with self.app.app_context():
            db = get_db()
            job = db.execute("SELECT id FROM jobs WHERE title='Software Engineer'").fetchone()
            jid = job['id']
        self.client.post(f'/admin/jobs/{jid}/approve')
        self.client.get('/auth/logout')

        # 5. Register Student & Apply
        self.client.post('/auth/register/student', data={
            'name': 'John Doe',
            'email': 'student@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        self.client.post('/auth/login', data={
            'email': 'student@test.com',
            'password': 'password123',
            'role': 'student'
        })
        # Apply for job
        res = self.client.post(f'/student/apply/{jid}', data={
            'cover_letter': 'Hire me please.'
        }, follow_redirects=True)
        self.assertIn(b'Application submitted successfully', res.data)
        self.client.get('/auth/logout')

        # 6. Company shortlists student
        self.client.post('/auth/login', data={
            'email': 'company@test.com',
            'password': 'password123',
            'role': 'company'
        })
        with self.app.app_context():
            db = get_db()
            app = db.execute("SELECT id FROM applications WHERE student_id=1 AND job_id=1").fetchone()
            aid = app['id']
        
        res = self.client.post(f'/company/applicants/{aid}/status', data={
            'status': 'Shortlisted'
        }, follow_redirects=True)
        self.assertIn(b'Status updated', res.data)
        
        print("ALL TESTS PASSED SUCCESSFULLY.")

if __name__ == '__main__':
    unittest.main()
