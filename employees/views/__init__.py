from .employee_management.employee import (
    get_all_employees_with_images,
    get_employee_by_md5,
    serve_employee_image_by_md5,
    get_all_employee_from_global,
    enable_facial_recognition,
    disable_facial_recognition,
    register_employee,
    preview_face_frames,
    encode_employee_face,
    get_employee_detail,
    serve_file as serve_employee_file,
    export_employees_xls
)
from .attendance_management.attendance import (
    mark_attendance,
    verify_face,
    attendance_report_with_employee_details,
    get_spoofing_attempts,
    delete_spoofing_attempts
)
from .attendance_management.shifts import (
    shift_list_create,
    shift_detail,
    department_list_create,
    department_detail,
    get_monthly_roster,
    assign_shift
)
from .authentication.auth import (
    get_device_info,
    registration,
    login,
    ip_login,
    my_ip,
    allowed_devices,
    get_global_departments,
    register_device_api,
    set_employee_password,
)
from .global_management import (
    get_data_entitlements,
    get_data_departments,
    get_data_designation,
    getprimaryandadditionalrole,
    get_next_department_code,
    get_next_designation_code,
    addnew_department,
    addnew_designation,
    get_todays_birthdays,
    check_employee_id,
    create_employee,
    update_employee,
    get_employee_by_id,
    get_employees_with_labels,
    upload_file,
    serve_file,
)

from .canteen_management.canteen import (
    issue_canteen_token,
    get_canteen_today_summary,
    get_canteen_token_history,
    manage_canteen_rules
)
from .common.utils import save_or_update_encoding
