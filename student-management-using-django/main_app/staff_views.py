import json

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.db import IntegrityError
from django.forms import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import *
from .models import *


def staff_home(request):
    staff = get_object_or_404(Staff, admin=request.user)
    total_students = Student.objects.filter(course=staff.course).count()
    total_leave = LeaveReportStaff.objects.filter(staff=staff).count()
    subjects = Subject.objects.filter(staff=staff)
    total_subject = subjects.count()
    attendance_list = Attendance.objects.filter(course=staff.course)  
    total_attendance = attendance_list.count()
    attendance_list = []
    subject_list = []
    
    for subject in subjects:
        
        attendance_count = Attendance.objects.filter(course=staff.course).count()  
        subject_list.append(subject.name)
        attendance_list.append(attendance_count)
    
    
    context = {
        'page_title': f'Staff Panel - {staff.admin.last_name} ({staff.course})',
        'total_students': total_students,
        'total_attendance': total_attendance,
        'total_leave': total_leave,
        'total_subject': total_subject,
        'subject_list': subject_list,
        'attendance_list': attendance_list
    }
    

    return render(request, 'staff_template/home_content.html', context)

def staff_take_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    courses = Course.objects.filter(staff=staff) 
    sessions = Session.objects.all()
    context = {
        'courses': courses,
        'sessions': sessions,
        'page_title': 'Take Attendance'
    }

    return render(request, 'staff_template/staff_take_attendance.html', context)


@csrf_exempt
def get_students(request):
    course_id = request.POST.get('course') 
    session_id = request.POST.get('session')
    try:
        course = get_object_or_404(Course, id=course_id)
        session = get_object_or_404(Session, id=session_id)
        students = Student.objects.filter(
            course=course, session=session)
        student_data = []
        for student in students:
            data = {
                    "id": student.id,
                    "name": student.admin.last_name + " " + student.admin.first_name
                    }
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), content_type='application/json', safe=False)
    except Exception as e:
        return e



@csrf_exempt
def save_attendance(request):
    student_data = request.POST.get('student_ids')
    date = request.POST.get('date')
    course_id = request.POST.get('course')
    session_id = request.POST.get('session')
    students = json.loads(student_data)

    try:
 
        session = get_object_or_404(Session, id=session_id)
        course = get_object_or_404(Course, id=course_id)

   
        attendance, created = Attendance.objects.get_or_create(session=session, course=course, date=date)

        for student_dict in students:
            student = get_object_or_404(Student, id=student_dict.get('id'))

          
            attendance_report, report_created = AttendanceReport.objects.get_or_create(student=student, attendance=attendance)

            if report_created:
                attendance_report.status = student_dict.get('status')
                attendance_report.save()

        return HttpResponse("OK")  
    except Exception as e:
       
        print(f"Error: {str(e)}")

        
        return HttpResponse(f"Error: {str(e)}", status=500) 


def staff_update_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    courses = Course.objects.filter(staff=staff)
    sessions = Session.objects.all()
    context = {
        'courses': courses,
        'sessions': sessions,
        'page_title': 'Update Attendance'
    }

    return render(request, 'staff_template/staff_update_attendance.html', context)


@csrf_exempt
def get_student_attendance(request):
    attendance_date_id = request.POST.get('attendance_date_id')
    try:
        date = get_object_or_404(Attendance, id=attendance_date_id)
        attendance_data = AttendanceReport.objects.filter(attendance=date)
        student_data = []
        for attendance in attendance_data:
            data = {"id": attendance.student.admin.id,
                    "name": attendance.student.admin.last_name + " " + attendance.student.admin.first_name,
                    "status": attendance.status}
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), content_type='application/json', safe=False)
    except Exception as e:
        return e


@csrf_exempt
def update_attendance(request):
    student_data = request.POST.get('student_ids')
    date = request.POST.get('date')
    students = json.loads(student_data)
    try:
        attendance = get_object_or_404(Attendance, id=date)

        for student_dict in students:
            student = get_object_or_404(
                Student, admin_id=student_dict.get('id'))
            attendance_report = get_object_or_404(AttendanceReport, student=student, attendance=attendance)
            attendance_report.status = student_dict.get('status')
            attendance_report.save()
    except Exception as e:
        return None

    return HttpResponse("OK")


def staff_apply_leave(request):
    form = LeaveReportStaffForm(request.POST or None)
    staff = get_object_or_404(Staff, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStaff.objects.filter(staff=staff),
        'page_title': 'Apply for Leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.staff = staff
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('staff_apply_leave'))
            except Exception:
                messages.error(request, "Could not apply!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "staff_template/staff_apply_leave.html", context)


def staff_feedback(request):
    form = FeedbackStaffForm(request.POST or None)
    staff = get_object_or_404(Staff, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStaff.objects.filter(staff=staff),
        'page_title': 'Add Feedback'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.staff = staff
                obj.save()
                messages.success(request, "Feedback submitted for review")
                return redirect(reverse('staff_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "staff_template/staff_feedback.html", context)


def staff_view_profile(request):
    staff = get_object_or_404(Staff, admin=request.user)
    form = StaffEditForm(request.POST or None, request.FILES or None,instance=staff)
    context = {'form': form, 'page_title': 'View/Update Profile'}
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = staff.admin
                if password != None:
                    admin.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                staff.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('staff_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
                return render(request, "staff_template/staff_view_profile.html", context)
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
            return render(request, "staff_template/staff_view_profile.html", context)

    return render(request, "staff_template/staff_view_profile.html", context)


@csrf_exempt
def staff_fcmtoken(request):
    token = request.POST.get('token')
    try:
        staff_user = get_object_or_404(CustomUser, id=request.user.id)
        staff_user.fcm_token = token
        staff_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def staff_view_notification(request):
    staff = get_object_or_404(Staff, admin=request.user)
    notifications = NotificationStaff.objects.filter(staff=staff)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "staff_template/staff_view_notification.html", context)



def staff_add_result(request):
    staff = get_object_or_404(Staff, admin=request.user)
    courses = Course.objects.filter(staff=staff)
    sessions = Session.objects.all()

    context = {
        'page_title': 'Result Upload',
        'courses': courses,
        'sessions': sessions
    }
    
    if request.method == 'POST':
        try:
            # Get form data
            student_id = request.POST.get('student_list')
            course_id = request.POST.get('course')
            test = request.POST.get('test')
            exam = request.POST.get('exam')

            # Validate if all fields are provided
            if not student_id or not course_id or not test or not exam:
                messages.warning(request, "Error: Missing required fields (student, course, test score, or exam score).")
                return render(request, "staff_template/staff_add_result.html", context)

            # Ensure that test and exam are valid integers
            try:
                test = int(test)  # Convert test score to integer
                exam = int(exam)  # Convert exam score to integer
            except ValueError:
                messages.warning(request, "Error: Test and Exam scores must be valid numbers.")
                return render(request, "staff_template/staff_add_result.html", context)

            # Get the student and course objects
            student = get_object_or_404(Student, id=student_id)
            course = get_object_or_404(Course, id=course_id)

            # Try to get or create the StudentResult
            try:
                # Try to update existing result
                result = StudentResult.objects.get(student=student, course=course)
                result.test = test
                result.exam = exam
                result.save()
                messages.success(request, "Scores updated successfully!")
            except StudentResult.DoesNotExist:
                # If the result doesn't exist, create a new one
                result = StudentResult(student=student, course=course, test=test, exam=exam)
                result.save()
                messages.success(request, "Scores saved successfully!")

        except IntegrityError:
            messages.warning(request, "Database integrity error. Please try again.")
        except ValidationError as ve:
            messages.warning(request, f"Validation error: {ve}")
        except Exception as e:
            # Catch any other unexpected errors
            messages.warning(request, f"Error occurred while processing the form: {str(e)}")
        
    return render(request, "staff_template/staff_add_result.html", context)

@csrf_exempt
def fetch_student_result(request):
    try:
        course_id = request.POST.get('course')
        student_id = request.POST.get('student')
        student = get_object_or_404(Student, id=student_id)
        course = get_object_or_404(Course, id=course_id)
        result = StudentResult.objects.get(student=student, course=course)
        result_data = {
            'exam': result.exam,
            'test': result.test
        }
        return HttpResponse(json.dumps(result_data))
    except Exception as e:
        return HttpResponse('False')
