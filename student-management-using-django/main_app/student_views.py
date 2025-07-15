import json
import math
from datetime import datetime

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,
                              redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import *
from .models import *


def student_home(request):
    # Get the logged-in student
    student = get_object_or_404(Student, admin=request.user)

    # Get the course the student is enrolled in
    course = student.course  # directly accessing student's course

    # Get the total number of attendance reports for the student
    total_attendance = AttendanceReport.objects.filter(student=student).count()
    total_present = AttendanceReport.objects.filter(student=student, status=True).count()

    # Handle division by zero for percentages
    if total_attendance == 0:
        percent_present = percent_absent = 0
    else:
        percent_present = math.floor((total_present / total_attendance) * 100)
        percent_absent = 100 - percent_present  # Percent absent can be calculated directly

    # Data lists to store information
    course_name = []
    data_present = []
    data_absent = []

    # Get all attendance records for this student's course
    attendance = Attendance.objects.filter(course=course)

    for record in attendance:
        # Get attendance report for each attendance record
        present_count = AttendanceReport.objects.filter(
            attendance=record, status=True, student=student).count()
        absent_count = AttendanceReport.objects.filter(
            attendance=record, status=False, student=student).count()

        # Store data for rendering
        course_name.append(course.name)
        data_present.append(present_count)
        data_absent.append(absent_count)

    # Prepare context to pass to the template
    context = {
        'total_attendance': total_attendance,
        'percent_present': percent_present,
        'percent_absent': percent_absent,
        'course': course,  # Passing the student's course
        'data_present': data_present,
        'data_absent': data_absent,
        'data_name': course_name,
        'page_title': 'Student Homepage'
    }

    return render(request, 'student_template/home_content.html', context)

@csrf_exempt
def student_view_attendance(request):
    student = get_object_or_404(Student, admin=request.user)  # Get the student instance

    if request.method != 'POST':
        # Get the course the student is enrolled in
        course = student.course  # Directly use the student's course
        # Fetch attendance data for the course
        attendance = Attendance.objects.filter(course=course)

        context = {
            'course': course,
            'attendance': attendance,
            'page_title': 'View Attendance',
        }
        return render(request, 'student_template/student_view_attendance.html', context)

    else:
        # Handle POST request (for fetching attendance within a specific date range)
        start = request.POST.get('start_date')
        end = request.POST.get('end_date')

        try:
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")

            # Filter attendance based on course and date range
            attendance = Attendance.objects.filter(
                date__range=(start_date, end_date), 
                course=student.course
            )

            json_data = []
            for record in attendance:
                data = {
                    "date": str(record.date),
                    "session": str(record.session),  # Optional: If you want to display the session as well
                }
                json_data.append(data)

            return JsonResponse(json.dumps(json_data), safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


def student_apply_leave(request):
    form = LeaveReportStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStudent.objects.filter(student=student),
        'page_title': 'Apply for leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('student_apply_leave'))
            except Exception:
                messages.error(request, "Could not submit")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_apply_leave.html", context)


def student_feedback(request):
    form = FeedbackStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStudent.objects.filter(student=student),
        'page_title': 'Student Feedback'

    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Feedback submitted for review")
                return redirect(reverse('student_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_feedback.html", context)


def student_view_profile(request):
    student = get_object_or_404(Student, admin=request.user)
    form = StudentEditForm(request.POST or None, request.FILES or None,
                           instance=student)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = student.admin
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
                student.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('student_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(request, "Error Occured While Updating Profile " + str(e))

    return render(request, "student_template/student_view_profile.html", context)


@csrf_exempt
def student_fcmtoken(request):
    token = request.POST.get('token')
    student_user = get_object_or_404(CustomUser, id=request.user.id)
    try:
        student_user.fcm_token = token
        student_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def student_view_notification(request):
    student = get_object_or_404(Student, admin=request.user)
    notifications = NotificationStudent.objects.filter(student=student)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "student_template/student_view_notification.html", context)


def student_view_result(request):
    student = get_object_or_404(Student, admin=request.user)
    results = StudentResult.objects.filter(student=student)
    context = {
        'results': results,
        'page_title': "View Results"
    }
    return render(request, "student_template/student_view_result.html", context)
