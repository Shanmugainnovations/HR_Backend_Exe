from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login, name='login'),
    path('ip-login/', views.ip_login, name='ip-login'),
    path('my-ip/', views.my_ip, name='my-ip'),
    path('get_device_info/', views.get_device_info, name="get_device_info"),

    # Employee registration + face enrollment
    path('hrregistration/', views.registration, name='registration'),
    path('register/', views.register_employee, name='register-employee'),
    path('preview-face-frames/', views.preview_face_frames, name='preview-face-frames'),
    path('employees/<str:employee_id>/encode_face/', views.encode_employee_face),
    path('employees/<str:employee_id>/enable_face/', views.enable_facial_recognition),
    path('employees/<str:employee_id>/disable_face/', views.disable_facial_recognition),
    path('employees_from_global/', views.get_all_employee_from_global, name='global-employees'),
    path('global-departments/', views.get_global_departments, name='global-departments'),

    # All Employees page
    path('employees/', views.get_all_employees_with_images, name='employee-list'),
    path('get_employees_with_labels/', views.get_employees_with_labels, name='get-employees-with-labels'),
    path('employees/export-xls/', views.export_employees_xls, name='export-employees-xls'),
    path('employees/<str:employee_id>/', views.get_employee_detail, name='employee-detail'),
    path('update_employee/<str:employee_id>/', views.update_employee, name='update-employee'),
    path('get_employee_by_id/<str:employee_id>/', views.get_employee_by_id, name='get-employee-by-id'),
    path('create_employee/', views.create_employee, name='create-employee'),
    path('check_employee_id/', views.check_employee_id, name='check-employee-id'),
    path('set-employee-password/', views.set_employee_password, name='set-employee-password'),
    path('employees/md5/<str:image_md5>/', views.get_employee_by_md5, name='get_employee_by_md5'),
    path('employees/image-by-md5/<str:image_md5>/', views.serve_employee_image_by_md5, name='serve_employee_image_by_md5'),

    # Device management
    path('register-device/', views.register_device_api, name='register-device'),
    path('allowed-devices/', views.allowed_devices, name='allowed-devices'),
    path('allowed-devices/<int:device_id>/', views.allowed_devices, name='allowed-devices-detail'),

    # Kiosk mode 1: Attendance (check-in/out auto)
    path('mark/', views.mark_attendance, name='mark_attendance'),
    path('verify-face/', views.verify_face, name='verify_face'),
    path('attendance-report/', views.attendance_report_with_employee_details, name='attendance_report'),
    path('spoofing-reports/', views.get_spoofing_attempts, name='get_spoofing_attempts'),
    path('spoofing-reports/delete/', views.delete_spoofing_attempts, name='delete_spoofing_attempts'),

    # Kiosk mode 2: Canteen
    path('canteen/issue-token/', views.issue_canteen_token, name='canteen-issue-token'),
    path('canteen/today-summary/', views.get_canteen_today_summary, name='canteen-today-summary'),
    path('canteen/history/', views.get_canteen_token_history, name='canteen-history'),
    path('canteen/rules/', views.manage_canteen_rules, name='canteen-rules'),

    # File storage (employee photos / face samples)
    path('serve-file/<str:file_id>/', views.serve_file, name="serve_file"),
    path('upload-gridfs/', views.upload_file, name='upload-gridfs'),
    path('gridfs/<str:file_id>/', views.serve_file, name='serve-gridfs-file'),
]
