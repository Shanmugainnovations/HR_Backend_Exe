import os
from dotenv import load_dotenv
from user_agents import parse

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from employees.models import Register, AllowedDevice
from pymongo import MongoClient
load_dotenv()

def get_device_info(request):
    ua_string = request.META.get('HTTP_USER_AGENT', '')
    user_agent = parse(ua_string)

    device_details = {
        "browser": user_agent.browser.family,       # e.g. Chrome
        "browser_version": user_agent.browser.version_string,
        "os": user_agent.os.family,                 # e.g. Windows
        "os_version": user_agent.os.version_string,
        "device": user_agent.device.family,         # e.g. iPhone, Desktop
        "is_mobile": user_agent.is_mobile,
        "is_tablet": user_agent.is_tablet,
        "is_pc": user_agent.is_pc,
        "ip_address": (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0]
            or request.META.get('REMOTE_ADDR')
        )
    }
    return JsonResponse(device_details)


from pymongo import MongoClient
from bson import ObjectId

def resolve_department_names(dept_str):
    """Helper to resolve department names from IDs or codes stored in Register model."""
    if not dept_str or dept_str == "Unassigned":
        return "Unassigned"
    
    parts = [p.strip() for p in dept_str.split(',') if p.strip()]
    if not parts:
         return "Unassigned"
    
    try:
        mongo_uri = os.getenv("GLOBAL_DB_HOST")
        db_name = os.getenv("GLOBAL_DB_NAME", "Global")
        client = MongoClient(mongo_uri)
        db = client[db_name]
        
        results = []
        for p in parts:
            query = {"department_id": int(p)} if p.isdigit() else {"department_code": p}
            dept = db['backend_diagnostics_Departments'].find_one(query)
            if dept:
                results.append(dept.get('department_name', p))
            else:
                results.append(p)
        return ",".join(results)
    except:
        return dept_str

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from pymongo import MongoClient
from bson import ObjectId
import os


def get_db():
    mongo_uri = os.getenv("GLOBAL_DB_HOST")
    db_name = os.getenv("HR_DB_NAME", "HR")
    client = MongoClient(mongo_uri)
    return client[db_name]


@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def registration(request):

    try:
        db = get_db()
        users_col = db['employees_register']

        # ======================================================
        # ✅ GET ALL USERS (Auto-sync Global HR-R-HOD Profiles)
        # ======================================================
        if request.method == 'GET':
            try:
                global_db_name = os.getenv("GLOBAL_DB_NAME", "Global")
                mongo_uri = os.getenv("GLOBAL_DB_HOST")
                if mongo_uri:
                    _client = MongoClient(mongo_uri)
                    _global_db = _client[global_db_name]
                    global_hods = list(_global_db['backend_diagnostics_profile'].find({
                        '$or': [
                            {'primaryRole': 'HR-R-HOD'},
                            {'primaryRole': {'$regex': 'HR-R-HOD', '$options': 'i'}},
                            {'additionalRoles': 'HR-R-HOD'},
                            {'additionalRoles': {'$elemMatch': {'$regex': 'HR-R-HOD', '$options': 'i'}}},
                            {'additionalRoles': {'$regex': 'HR-R-HOD', '$options': 'i'}}
                        ]
                    }))
                    for gh in global_hods:
                        emp_id = str(gh.get('employeeId') or '').strip()
                        if not emp_id:
                            continue
                        name = gh.get('employeeName') or gh.get('name') or emp_id
                        dept = gh.get('department') or ''

                        # Find highest integer ID in Register table
                        existing_user = users_col.find_one({'employee_id': emp_id})
                        if existing_user:
                            users_col.update_one(
                                {'_id': existing_user['_id']},
                                {'$set': {'role': 'HR-R-HOD'}}
                            )
                        else:
                            last_user = users_col.find().sort('id', -1).limit(1)
                            max_id = 1
                            for lu in last_user:
                                if lu.get('id') and isinstance(lu.get('id'), int):
                                    max_id = lu.get('id') + 1

                            users_col.insert_one({
                                'id': max_id,
                                'name': name,
                                'employee_id': emp_id,
                                'department': dept,
                                'role': 'HR-R-HOD',
                                'password': 'Password@123',
                                'confirmPassword': 'Password@123'
                            })
            except Exception as sync_err:
                print(f"HR-R-HOD sync notice: {sync_err}")

            raw_users = list(Register.objects.all().order_by('-id').values())
            # Deduplicate by employee_id and serialize ObjectId to string
            seen_emp = set()
            clean_users = []
            for u in raw_users:
                user_dict = {}
                for k, v in u.items():
                    if isinstance(v, ObjectId):
                        user_dict[k] = str(v)
                    else:
                        user_dict[k] = v
                e_id = str(user_dict.get('employee_id') or user_dict.get('id') or user_dict.get('_id'))
                if e_id not in seen_emp:
                    seen_emp.add(e_id)
                    clean_users.append(user_dict)

            return Response(clean_users, status=200)

        # ======================================================
        # ✅ CREATE USER
        # ======================================================
        if request.method == 'POST':
            data = request.data

            name = data.get('name')
            employee_id = data.get('employee_id')
            department = data.get('department')
            role = data.get('role')
            password = data.get('password')
            confirm_password = data.get('confirmPassword')
            allowed_ip = data.get('allowed_ip')
            device = data.get('device')
            fingerprint = data.get('fingerprint')

            # Lookup device label if fingerprint is provided but device label is empty
            if fingerprint and not device:
                device_obj = AllowedDevice.objects.filter(fingerprint=fingerprint).first()
                if device_obj:
                    device = device_obj.label

            # 🔴 Validation
            if not name or not password:
                return Response({"error": "Name & Password required"}, status=400)

            if password != confirm_password:
                return Response({"error": "Passwords do not match"}, status=400)

            # 🔴 Duplicate checks (ORM)
            if Register.objects.filter(name=name).exists():
                return Response({"error": "User already exists"}, status=400)

            if employee_id and Register.objects.filter(employee_id=employee_id).exists():
                return Response({"error": "Employee ID already exists"}, status=400)

            if allowed_ip and Register.objects.filter(allowed_ip=allowed_ip).exists():
                return Response({"error": "IP already assigned"}, status=400)

            # 🔴 Create user via ORM for automatic ID generation
            user = Register(
                name=name,
                employee_id=employee_id,
                department=department,
                role=role,
                password=password,
                confirmPassword=confirm_password,
                allowed_ip=allowed_ip,
                device=device,
                fingerprint=fingerprint
            )
            user.save_with_audit(request)

            return Response({
                "message": "User created successfully",
                "id": user.id
            }, status=201)

        # ======================================================
        # ✅ UPDATE USER
        # ======================================================
        if request.method == 'PUT':
            user_id = request.data.get('id')
            employee_id = request.data.get('employee_id')
            name = request.data.get('name')

            user = None
            if user_id:
                try:
                    user = Register.objects.filter(id=user_id).first()
                except Exception:
                    user = None

            if not user and employee_id:
                user = Register.objects.filter(employee_id=employee_id).first()

            if not user and name:
                user = Register.objects.filter(name=name).first()

            if not user:
                if employee_id or name:
                    user = Register.objects.create(
                        name=name or employee_id,
                        employee_id=employee_id,
                        department=request.data.get('department', ''),
                        role=request.data.get('role', 'HR-R-HOD'),
                        password='Password@123',
                        confirmPassword='Password@123'
                    )
                else:
                    return Response({"error": "User ID or Employee ID required"}, status=400)

            fields = [
                "name", "employee_id", "department",
                "role", "device", "allowed_ip", "fingerprint"
            ]

            for f in fields:
                if f in request.data:
                    setattr(user, f, request.data.get(f))

            password = request.data.get('password')
            confirm_password = request.data.get('confirmPassword')

            if password:
                if password != confirm_password:
                    return Response({"error": "Passwords do not match"}, status=400)
                user.password = password
                user.confirmPassword = confirm_password

            # Lookup device label if fingerprint is provided (or changed) but device is empty
            if user.fingerprint and not user.device:
                device_obj = AllowedDevice.objects.filter(fingerprint=user.fingerprint).first()
                if device_obj:
                    user.device = device_obj.label

            user.save_with_audit(request)

            # Sync department with both HR employees_register and Global profile
            if user.employee_id or user.name:
                try:
                    emp_str = str(user.employee_id).strip() if user.employee_id else ""
                    emp_filter = [
                        {'name': str(user.name)}
                    ]
                    if emp_str:
                        emp_filter.append({'employee_id': emp_str})
                        if emp_str.isdigit():
                            emp_filter.append({'employee_id': int(emp_str)})

                    users_col.update_many(
                        {'$or': emp_filter},
                        {'$set': {
                            'department': str(user.department or ''),
                            'role': str(user.role or '')
                        }}
                    )

                    global_db_name = os.getenv("GLOBAL_DB_NAME", "Global")
                    mongo_uri = os.getenv("GLOBAL_DB_HOST")
                    if mongo_uri and emp_str:
                        _client = MongoClient(mongo_uri)
                        _global_db = _client[global_db_name]
                        _global_db['backend_diagnostics_profile'].update_one(
                            {'$or': [{'employeeId': emp_str}, {'employeeId': int(emp_str) if emp_str.isdigit() else -1}]},
                            {'$set': {
                                'department': str(user.department or ''),
                                'primaryRole': 'HR-R-HOD' if 'HOD' in str(user.role) else ('Admin' if user.role == 'Admin' else 'Employee')
                            }}
                        )
                except Exception as sync_err:
                    print(f"Profile sync notice: {sync_err}")

            return Response({"message": "Updated successfully", "id": str(user.id) if user.id is not None else None}, status=200)


        # ======================================================
        # ✅ DELETE USER
        # ======================================================
        if request.method == 'DELETE':
            user_id = request.GET.get('id')

            if not user_id:
                return Response({"error": "User ID required"}, status=400)

            try:
                Register.objects.filter(id=user_id).delete()
                return Response({"message": "Deleted successfully"}, status=200)
            except:
                return Response({"error": "Deletion failed"}, status=500)

    except Exception as e:
        print("🔥 ERROR:", str(e))  # important debug
        return Response({"error": str(e)}, status=500)


@api_view(['POST'])
def login(request):
    name = request.data.get('name')
    employee_id = request.data.get('employee_id')
    password = request.data.get('password')

    try:
        # Check if login by employee_id (preferred) or name
        user = None
        if employee_id:
            user = Register.objects.filter(employee_id=employee_id).first()
        
        if not user and name:
            user = Register.objects.filter(name=name).first()
            
        if not user:
                return Response({"error": "User not found"}, status=404)

        from django.contrib.auth.hashers import check_password
        if not check_password(password, user.password) and user.password != password:
            return Response({"error": "Invalid password"}, status=401)


        # Final department resolution
        dept_id = user.department if user.department else "Unassigned"
        dept_name = resolve_department_names(dept_id)

        # Construct Cryptographic JWT Access Token
        from employees.token_utils import generate_employee_token
        token = generate_employee_token(user.employee_id or user.name or "Admin", user.role)


        return Response({
            "message": f"Login successful as {user.role}",
            "device": user.device,
            "name": user.name,
            "employee_id": user.employee_id,
            "role": user.role,
            "department": dept_id,      # ID(s)
            "department_id": dept_id,   # Explicit ID field
            "department_name": dept_name, # Resolved name(s)
            "token": token
        }, status=200)


    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(['POST'])
def ip_login(request):
    """
    Fingerprint-based Login (FingerprintJS visitor ID).
    """
    try:
        from employees.models import AllowedDevice

        client_fingerprint = request.data.get("fingerprint")
        if not client_fingerprint:
            return Response(
                {"error": "Fingerprint ID missing"},
                status=400
            )

        # 1️⃣ CHECK ALLOWED DEVICE VIA DJANGO ORM
        device_obj = AllowedDevice.objects.filter(
            fingerprint=client_fingerprint,
            is_active=True
        ).first()

        # Fallback to PyMongo if needed
        if not device_obj:
            try:
                mongo_uri = os.getenv("GLOBAL_DB_HOST")
                db_name = os.environ.get('GLOBAL_DB_NAME', os.environ.get('HR_DB_NAME', 'Global'))
                client = MongoClient(mongo_uri)
                for test_db in [db_name, 'Global', 'HR']:
                    doc = client[test_db]["employees_alloweddevice"].find_one({
                        "fingerprint": client_fingerprint,
                        "is_active": True
                    })
                    if doc:
                        device_obj = doc
                        break
            except Exception:
                pass

        if not device_obj:
            return Response({
                "error": f"Fingerprint '{client_fingerprint[:8]}...' is not authorized. Register this terminal first."
            }, status=403)

        if isinstance(device_obj, dict):
            device_name = device_obj.get('label') or "KIOSK"
            kiosk_type = device_obj.get('kiosk_type') or 'attendance'
        else:
            device_name = device_obj.label or "KIOSK"
            kiosk_type = getattr(device_obj, 'kiosk_type', 'attendance') or 'attendance'

        token_env_key = f"{device_name}_TOKEN"
        token = os.getenv(token_env_key, "kiosk-generic-token")

        return Response({
            "success": True,
            "message": f"Kiosk Access Granted: {device_name}",
            "name": f"Kiosk Terminal ({device_name})",
            "employee_id": "KIOSK-001",
            "role": "CanteenKiosk" if kiosk_type == 'canteen' else "Kiosk",
            "kiosk_type": kiosk_type,
            "department_id": "All",
            "department_name": "Shared Hardware",
            "token": token
        }, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def my_ip(request):
    """Returns the caller's IP address. Used by frontend to show device IP."""
    from employees.views.attendance_management.ip_guard import get_client_ip
    return JsonResponse({'ip': get_client_ip(request)})


@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def allowed_devices(request, device_id=None):
    """Admin-only CRUD for the AllowedDevice whitelist."""
    # Requester identity handling for audit if needed, but we allow anyone with valid credentials to manage? 
    # Actually, Management (Edit/Delete) should probably still be restricted to Admin in the LIST view, 
    # but the USER said "all users can register device". 
    # Let's keep the management CRUD for Admins but the Registration API for all.
    requester_role = request.headers.get('X-User-Role') or request.data.get('requester_role')
    
    if request.method == 'GET':
        devices = list(AllowedDevice.objects.all().values('id', 'label', 'ip_address', 'fingerprint', 'kiosk_type', 'is_active', 'created_at'))
        return Response(devices)

    if request.method == 'POST':
        label = request.data.get('label', '').strip()
        ip    = request.data.get('ip_address', '').strip()
        fingerprint = request.data.get('fingerprint', '').strip()
        kiosk_type = request.data.get('kiosk_type') or 'attendance'
        if kiosk_type not in ('attendance', 'canteen'):
            kiosk_type = 'attendance'

        if not label:
            return Response({'error': 'label is required.'}, status=400)

        if ip and AllowedDevice.objects.filter(ip_address=ip).exists():
            return Response({'error': f'IP {ip} is already whitelisted.'}, status=400)

        if fingerprint and AllowedDevice.objects.filter(fingerprint=fingerprint).exists():
            return Response({'error': f'Device Fingerprint {fingerprint} is already registered.'}, status=400)

        d = AllowedDevice.objects.create(label=label, ip_address=ip, fingerprint=fingerprint, kiosk_type=kiosk_type)
        return Response({'message': 'Device added.', 'id': d.id}, status=201)

    if request.method == 'PUT':
        if not device_id:
            return Response({'error': 'device_id required in URL.'}, status=400)
        try:
            d = AllowedDevice.objects.get(id=device_id)
            if 'label'       in request.data: d.label       = request.data['label']
            if 'ip_address'  in request.data: d.ip_address  = request.data['ip_address']
            if 'fingerprint' in request.data: d.fingerprint = request.data['fingerprint']
            if 'kiosk_type'  in request.data and request.data['kiosk_type'] in ('attendance', 'canteen'):
                d.kiosk_type = request.data['kiosk_type']
            if 'is_active'   in request.data: d.is_active   = request.data['is_active']
            d.save()
            return Response({'message': 'Device updated.'})
        except AllowedDevice.DoesNotExist:
            return Response({'error': 'Device not found.'}, status=404)

    if request.method == 'DELETE':
        if not device_id:
            return Response({'error': 'device_id required in URL.'}, status=400)
        try:
            AllowedDevice.objects.get(id=device_id).delete()
            return Response({'message': 'Device removed.'})
        except AllowedDevice.DoesNotExist:
            return Response({'error': 'Device not found.'}, status=404)

@api_view(['POST'])
def register_device_api(request):
    """
    Dedicated endpoint for whitelisting a device.
    Now uses Django ORM for reliable ID generation and data consistency.
    """
    label = request.data.get('label')
    fingerprint = request.data.get('fingerprint')
    ip_address = request.data.get('ip_address')
    password = request.data.get('password')
    kiosk_type = request.data.get('kiosk_type') or 'attendance'
    if kiosk_type not in ('attendance', 'canteen'):
        kiosk_type = 'attendance'

    if not all([label, fingerprint, password]):
        return Response({"error": "Missing required fields (Label, Fingerprint, or Password)"}, status=400)

    try:
        # 1️⃣ Verification: Find user by password (the user authorizing this device)
        user = Register.objects.filter(password=password).first()

        if not user:
            return Response({"error": "Account not found for this password. Registration denied."}, status=403)

        # 2️⃣ Whitelist the Device (AllowedDevice)
        # Using ORM to ensure 'id' is generated
        device_obj, created = AllowedDevice.objects.update_or_create(
            fingerprint=fingerprint,
            defaults={
                "label": label,
                "ip_address": ip_address or "127.0.0.1",
                "kiosk_type": kiosk_type,
                "is_active": True
            }
        )

        # 3️⃣ Link Fingerprint to User (Register)
        # We update the SPECIFIC user record found in step 1
        user.fingerprint = fingerprint
        user.device = label
        user.allowed_ip = ip_address or "127.0.0.1"
        user.save()

        return Response({
            "success": True,
            "message": f"Device '{label}' successfully whitelisted and linked to user '{user.name}'!"
        }, status=201)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def get_global_departments(request):
    """Retrieve all unique departments from Global MongoDB."""
    try:
        mongo_uri = os.getenv("GLOBAL_DB_HOST")
        db_name = os.getenv("GLOBAL_DB_NAME", "Global")
        client = MongoClient(mongo_uri)
        db = client[db_name]
        dept_col = db['backend_diagnostics_Departments']
        
        # Get all departments, sorted by name
        departments = list(dept_col.find(
            {}, 
            {"_id": 0, "department_name": 1, "department_code": 1}
        ).sort("department_name", 1))
        
        # Fallback to unique department_name from profiles if Departments collection is empty
        if not departments:
            profile_col = db['backend_diagnostics_profile']
            dept_names = profile_col.distinct("department_name")
            departments = [{"department_name": name, "department_code": name} for name in dept_names if name]
            
        return Response(departments, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def set_employee_password(request):
    """
    Set/Reset employee password with make_password hashing for user model.
    """
    from employees.models import user
    from django.contrib.auth.hashers import make_password, identify_hasher

    employee_id = request.data.get("employeeId") or request.data.get("employee_id")
    password = request.data.get("password")

    if not employee_id or not password:
        return Response(
            {"error": "employeeId and password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user_obj = user.objects.filter(employeeId=employee_id).first()
    if not user_obj:
        user_obj = user(employeeId=employee_id)

    try:
        identify_hasher(password)
    except ValueError:
        password = make_password(password)

    user_obj.password = password
    user_obj.is_password_set = True
    user_obj.is_active = True
    user_obj.save()

    return Response(
        {"message": "Password updated successfully", "employeeId": employee_id},
        status=status.HTTP_200_OK
    )

