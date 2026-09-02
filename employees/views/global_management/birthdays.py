import os
from datetime import datetime, timezone, timedelta
from employees.permissions import HasRoleAndDataPermission
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from employees.models import Profile
from employees.views.common.utils import get_mongo_client

try:
    import zoneinfo
    IST = zoneinfo.ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))


@api_view(['GET'])
@permission_classes([HasRoleAndDataPermission])
def get_todays_birthdays(request):
    """Fetch all employees celebrating their birthday today."""
    try:
        today = datetime.now(IST).date()
        birthday_list = []

        try:
            client = get_mongo_client()
            db_name = os.environ.get('GLOBAL_DB_NAME', 'Global')
            db = client[db_name]
            profiles = list(db['backend_diagnostics_profile'].find({}, {
                'employeeId': 1, 'employeeName': 1, 'department': 1,
                'designation': 1, 'email': 1, 'mobileNumber': 1,
                'profileImage': 1, 'dateOfBirth': 1, '_id': 0
            }))
        except Exception:
            profiles = Profile.objects.all().values(
                'employeeId', 'employeeName', 'department',
                'designation', 'email', 'mobileNumber',
                'profileImage', 'dateOfBirth'
            )

        for prof in profiles:
            dob_raw = prof.get('dateOfBirth') if isinstance(prof, dict) else getattr(prof, 'dateOfBirth', None)
            if not dob_raw:
                continue

            dob_date = None
            if isinstance(dob_raw, datetime):
                dob_date = dob_raw.date()
            elif hasattr(dob_raw, 'date'):
                dob_date = dob_raw.date()
            elif isinstance(dob_raw, str):
                try:
                    dob_date = datetime.fromisoformat(dob_raw.replace('Z', '+00:00')).date()
                except Exception:
                    try:
                        dob_date = datetime.strptime(dob_raw[:10], '%Y-%m-%d').date()
                    except Exception:
                        pass

            if dob_date and dob_date.month == today.month and dob_date.day == today.day:
                birthday_list.append({
                    "employeeId": prof.get('employeeId') if isinstance(prof, dict) else prof.employeeId,
                    "employeeName": prof.get('employeeName') if isinstance(prof, dict) else prof.employeeName,
                    "department": prof.get('department') if isinstance(prof, dict) else prof.department,
                    "designation": prof.get('designation') if isinstance(prof, dict) else prof.designation,
                    "email": prof.get('email') if isinstance(prof, dict) else prof.email,
                    "mobileNumber": prof.get('mobileNumber') if isinstance(prof, dict) else prof.mobileNumber,
                    "profileImage": prof.get('profileImage') if isinstance(prof, dict) else prof.profileImage,
                    "dateOfBirth": dob_raw.isoformat() if isinstance(dob_raw, datetime) else str(dob_raw),
                })

        return JsonResponse({"employees": birthday_list}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
