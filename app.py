"""
Student Marks Calculator - Main Application
Complete backend with database, API routes, and business logic
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
import csv
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from pathlib import Path

# Initialize Flask App
app = Flask(__name__)
CORS(app)

# Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "students.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== DATABASE MODELS ====================

class Student(db.Model):
    """Student model for database"""
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    marks = db.relationship('Mark', backref='student', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'roll_number': self.roll_number,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'created_at': self.created_at.isoformat()
        }


class Subject(db.Model):
    """Subject model for database"""
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    max_marks = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    marks = db.relationship('Mark', backref='subject', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'max_marks': self.max_marks,
            'created_at': self.created_at.isoformat()
        }


class Mark(db.Model):
    """Mark model linking Student and Subject"""
    __tablename__ = 'marks'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    obtained_marks = db.Column(db.Float, nullable=False)
    grade = db.Column(db.String(2), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def calculate_grade(self, max_marks):
        """Calculate grade based on percentage"""
        percentage = (self.obtained_marks / max_marks) * 100
        if percentage >= 90:
            return 'A'
        elif percentage >= 80:
            return 'B'
        elif percentage >= 70:
            return 'C'
        elif percentage >= 60:
            return 'D'
        else:
            return 'F'
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'subject_id': self.subject_id,
            'student_name': self.student.name,
            'subject_name': self.subject.name,
            'obtained_marks': self.obtained_marks,
            'max_marks': self.subject.max_marks,
            'grade': self.grade,
            'percentage': round((self.obtained_marks / self.subject.max_marks) * 100, 2),
            'created_at': self.created_at.isoformat()
        }


# ==================== STUDENT API ROUTES ====================

@app.route('/api/students', methods=['GET'])
def get_all_students():
    """Get all students"""
    try:
        students = Student.query.all()
        return jsonify({
            'success': True,
            'data': [student.to_dict() for student in students],
            'count': len(students)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/students', methods=['POST'])
def add_student():
    """Add a new student"""
    try:
        data = request.get_json()
        
        # Validation
        if not data or not all(k in data for k in ['roll_number', 'name']):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Check if roll number already exists
        existing = Student.query.filter_by(roll_number=data['roll_number']).first()
        if existing:
            return jsonify({'success': False, 'error': 'Roll number already exists'}), 400
        
        student = Student(
            roll_number=data['roll_number'],
            name=data['name'],
            email=data.get('email'),
            phone=data.get('phone')
        )
        
        db.session.add(student)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Student added successfully',
            'data': student.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/students/<int:student_id>', methods=['GET'])
def get_student(student_id):
    """Get a specific student with marks"""
    try:
        student = Student.query.get_or_404(student_id)
        student_data = student.to_dict()
        
        # Add marks information
        marks = Mark.query.filter_by(student_id=student_id).all()
        student_data['marks'] = [mark.to_dict() for mark in marks]
        
        return jsonify({'success': True, 'data': student_data}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    """Update student information"""
    try:
        student = Student.query.get_or_404(student_id)
        data = request.get_json()
        
        student.name = data.get('name', student.name)
        student.email = data.get('email', student.email)
        student.phone = data.get('phone', student.phone)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Student updated successfully',
            'data': student.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    """Delete a student"""
    try:
        student = Student.query.get_or_404(student_id)
        db.session.delete(student)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Student deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== SUBJECT API ROUTES ====================

@app.route('/api/subjects', methods=['GET'])
def get_all_subjects():
    """Get all subjects"""
    try:
        subjects = Subject.query.all()
        return jsonify({
            'success': True,
            'data': [subject.to_dict() for subject in subjects],
            'count': len(subjects)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/subjects', methods=['POST'])
def add_subject():
    """Add a new subject"""
    try:
        data = request.get_json()
        
        # Validation
        if not data or not all(k in data for k in ['name', 'code']):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Check if subject already exists
        existing = Subject.query.filter_by(code=data['code']).first()
        if existing:
            return jsonify({'success': False, 'error': 'Subject code already exists'}), 400
        
        subject = Subject(
            name=data['name'],
            code=data['code'],
            max_marks=data.get('max_marks', 100)
        )
        
        db.session.add(subject)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Subject added successfully',
            'data': subject.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/subjects/<int:subject_id>', methods=['DELETE'])
def delete_subject(subject_id):
    """Delete a subject"""
    try:
        subject = Subject.query.get_or_404(subject_id)
        db.session.delete(subject)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Subject deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== MARKS API ROUTES ====================

@app.route('/api/marks', methods=['GET'])
def get_all_marks():
    """Get all marks with filters"""
    try:
        student_id = request.args.get('student_id')
        subject_id = request.args.get('subject_id')
        
        query = Mark.query
        
        if student_id:
            query = query.filter_by(student_id=int(student_id))
        if subject_id:
            query = query.filter_by(subject_id=int(subject_id))
        
        marks = query.all()
        
        return jsonify({
            'success': True,
            'data': [mark.to_dict() for mark in marks],
            'count': len(marks)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/marks', methods=['POST'])
def add_mark():
    """Add marks for a student in a subject"""
    try:
        data = request.get_json()
        
        # Validation
        required_fields = ['student_id', 'subject_id', 'obtained_marks']
        if not data or not all(k in data for k in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        student_id = data['student_id']
        subject_id = data['subject_id']
        obtained_marks = float(data['obtained_marks'])
        
        # Check if student and subject exist
        student = Student.query.get_or_404(student_id)
        subject = Subject.query.get_or_404(subject_id)
        
        # Validate marks
        if obtained_marks < 0 or obtained_marks > subject.max_marks:
            return jsonify({
                'success': False,
                'error': f'Marks must be between 0 and {subject.max_marks}'
            }), 400
        
        # Check if marks already exist
        existing_mark = Mark.query.filter_by(
            student_id=student_id,
            subject_id=subject_id
        ).first()
        
        if existing_mark:
            existing_mark.obtained_marks = obtained_marks
            existing_mark.grade = existing_mark.calculate_grade(subject.max_marks)
        else:
            mark = Mark(
                student_id=student_id,
                subject_id=subject_id,
                obtained_marks=obtained_marks
            )
            mark.grade = mark.calculate_grade(subject.max_marks)
            db.session.add(mark)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Marks added/updated successfully',
            'data': existing_mark.to_dict() if existing_mark else mark.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/marks/<int:mark_id>', methods=['DELETE'])
def delete_mark(mark_id):
    """Delete marks"""
    try:
        mark = Mark.query.get_or_404(mark_id)
        db.session.delete(mark)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Marks deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== ANALYTICS & REPORTS ====================

@app.route('/api/analytics/student/<int:student_id>', methods=['GET'])
def student_analytics(student_id):
    """Get analytics for a student"""
    try:
        student = Student.query.get_or_404(student_id)
        marks = Mark.query.filter_by(student_id=student_id).all()
        
        if not marks:
            return jsonify({
                'success': True,
                'data': {
                    'student_name': student.name,
                    'total_marks': 0,
                    'obtained_marks': 0,
                    'percentage': 0,
                    'average_grade': 'N/A',
                    'subjects_count': 0
                }
            }), 200
        
        total_marks = sum(mark.subject.max_marks for mark in marks)
        obtained_marks = sum(mark.obtained_marks for mark in marks)
        percentage = (obtained_marks / total_marks) * 100 if total_marks > 0 else 0
        
        grades = [mark.grade for mark in marks if mark.grade]
        
        return jsonify({
            'success': True,
            'data': {
                'student_name': student.name,
                'total_marks': total_marks,
                'obtained_marks': obtained_marks,
                'percentage': round(percentage, 2),
                'average_grade': grades[len(grades)//2] if grades else 'N/A',
                'subjects_count': len(marks),
                'subject_wise_marks': [mark.to_dict() for mark in marks]
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analytics/class', methods=['GET'])
def class_analytics():
    """Get class-wide analytics"""
    try:
        students = Student.query.all()
        marks = Mark.query.all()
        
        if not students or not marks:
            return jsonify({
                'success': True,
                'data': {
                    'total_students': len(students),
                    'total_subjects': 0,
                    'class_average': 0,
                    'highest_scorer': None,
                    'lowest_scorer': None
                }
            }), 200
        
        # Calculate class average
        total_obtained = sum(mark.obtained_marks for mark in marks)
        total_marks_possible = sum(mark.subject.max_marks for mark in marks)
        class_average = (total_obtained / total_marks_possible) * 100 if total_marks_possible > 0 else 0
        
        # Find highest and lowest scorer
        student_totals = {}
        for mark in marks:
            if mark.student_id not in student_totals:
                student_totals[mark.student_id] = {'obtained': 0, 'total': 0, 'name': mark.student.name}
            student_totals[mark.student_id]['obtained'] += mark.obtained_marks
            student_totals[mark.student_id]['total'] += mark.subject.max_marks
        
        if student_totals:
            highest = max(student_totals.items(),
                        key=lambda x: (x[1]['obtained'] / x[1]['total']) * 100)
            lowest = min(student_totals.items(),
                       key=lambda x: (x[1]['obtained'] / x[1]['total']) * 100)
        else:
            highest = lowest = None
        
        return jsonify({
            'success': True,
            'data': {
                'total_students': len(students),
                'total_subjects': len(set(mark.subject_id for mark in marks)),
                'class_average': round(class_average, 2),
                'highest_scorer': {
                    'name': highest[1]['name'],
                    'percentage': round((highest[1]['obtained'] / highest[1]['total']) * 100, 2)
                } if highest else None,
                'lowest_scorer': {
                    'name': lowest[1]['name'],
                    'percentage': round((lowest[1]['obtained'] / lowest[1]['total']) * 100, 2)
                } if lowest else None,
                'total_marks_recorded': len(marks)
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== FILE EXPORT ====================

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """Export all marks to CSV"""
    try:
        marks = Mark.query.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Roll Number', 'Student Name', 'Subject', 'Obtained Marks', 'Max Marks', 'Percentage', 'Grade'])
        
        # Data
        for mark in marks:
            percentage = (mark.obtained_marks / mark.subject.max_marks) * 100
            writer.writerow([
                mark.student.roll_number,
                mark.student.name,
                mark.subject.name,
                mark.obtained_marks,
                mark.subject.max_marks,
                f'{percentage:.2f}%',
                mark.grade
            ])
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'marks_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/pdf', methods=['GET'])
def export_pdf():
    """Export marks to PDF"""
    try:
        marks = Mark.query.all()
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Title
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph('Student Marks Report', title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Table data
        table_data = [['Roll No', 'Student Name', 'Subject', 'Obtained', 'Max', 'Percentage', 'Grade']]
        
        for mark in marks:
            percentage = (mark.obtained_marks / mark.subject.max_marks) * 100
            table_data.append([
                mark.student.roll_number,
                mark.student.name,
                mark.subject.name,
                str(mark.obtained_marks),
                str(mark.subject.max_marks),
                f'{percentage:.1f}%',
                mark.grade or 'N/A'
            ])
        
        # Create table
        table = Table(table_data, colWidths=[1*inch, 1.8*inch, 1.5*inch, 0.8*inch, 0.6*inch, 0.9*inch, 0.6*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
        ]))
        
        story.append(table)
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'marks_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== WEB ROUTES ====================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html')


@app.route('/students-page')
def students_page():
    """Students management page"""
    return render_template('students.html')


@app.route('/subjects-page')
def subjects_page():
    """Subjects management page"""
    return render_template('subjects.html')


@app.route('/marks-page')
def marks_page():
    """Marks management page"""
    return render_template('marks.html')


@app.route('/reports')
def reports():
    """Reports page"""
    return render_template('reports.html')


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'success': False, 'error': 'Resource not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return jsonify({'success': False, 'error': 'Internal server error'}), 500


# ==================== INITIALIZATION ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database initialized successfully!")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
