import os
import sys
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_backend.settings')
django.setup()

from employees.models import Employee, AllowedDevice, EmployeeAttendance, CanteenTokenIssue

print("=" * 60)
print("🔍 FACEHR KIOSK PRODUCTION READINESS AUDIT")
print("=" * 60)

results = []

def run_test(name, fn):
    try:
        fn()
        results.append((name, "PASS", "OK"))
        print(f"  ✅ [PASS] {name}")
    except Exception as e:
        results.append((name, "FAIL", str(e)))
        print(f"  ❌ [FAIL] {name}: {e}")

# 1. Test Device Whitelisting API on facehr_backend (5680)
def test_allowed_devices_api():
    r = requests.get('http://localhost:5680/_b_a_c_k_e_n_d/HR/allowed-devices/')
    assert r.status_code == 200, f"Status {r.status_code}: {r.text}"
    data = r.json()
    assert isinstance(data, list), "Expected list of devices"
    if data:
        dev = data[0]
        # Test PUT
        r_put = requests.put(
            f"http://localhost:5680/_b_a_c_k_e_n_d/HR/allowed-devices/{dev['id']}/",
            json={'label': dev['label'], 'is_active': dev['is_active'], 'kiosk_type': dev.get('kiosk_type', 'attendance')}
        )
        assert r_put.status_code == 200, f"PUT failed: {r_put.status_code}"
run_test("Allowed Devices GET & PUT (Port 5680)", test_allowed_devices_api)

# 2. Test Allowed Devices API on hr_backend (5678)
def test_allowed_devices_hr():
    r = requests.get('http://localhost:5678/_b_a_c_k_e_n_d/HR/allowed-devices/')
    assert r.status_code == 200, f"Status {r.status_code}"
run_test("Allowed Devices GET (Port 5678)", test_allowed_devices_hr)

# 3. Test Global Departments Endpoint (Used by EmployeeManagement)
def test_global_departments():
    r_dept = requests.get('http://localhost:5680/_b_a_c_k_e_n_d/HR/global-departments/')
    assert r_dept.status_code == 200, f"Dept status {r_dept.status_code}: {r_dept.text}"
    data = r_dept.json()
    assert isinstance(data, (list, dict)), "Expected list or dict of departments"
    print(f"      Departments fetched: {len(data)}")
run_test("Global Departments API", test_global_departments)

# 4. Test Employee Data Listing (For All Employees page)
def test_employee_list():
    r = requests.get('http://localhost:5680/_b_a_c_k_e_n_d/HR/employees/')
    assert r.status_code == 200, f"Status {r.status_code}"
    data = r.json()
    assert isinstance(data, list), "Expected list of employees"
    print(f"      Found {len(data)} total employee records for Kiosk All Employees")
run_test("Employee Data Table API (employees/)", test_employee_list)

# 5. Test Face Verification Endpoint
def test_face_verification_endpoint():
    r = requests.post('http://localhost:5680/_b_a_c_k_e_n_d/HR/verify-face/', json={})
    assert r.status_code in [200, 400], f"Expected 200 or 400, got {r.status_code}: {r.text}"
run_test("Attendance Kiosk Face Verification Endpoint (verify-face/)", test_face_verification_endpoint)

# 6. Test Mark Attendance Endpoint
def test_mark_attendance_endpoint():
    r = requests.post('http://localhost:5680/_b_a_c_k_e_n_d/HR/mark/', json={})
    assert r.status_code in [200, 400], f"Expected 200 or 400, got {r.status_code}: {r.text}"
run_test("Attendance Kiosk Mark Endpoint (mark/)", test_mark_attendance_endpoint)

# 7. Test Canteen Issue Token Endpoint
def test_canteen_endpoint():
    r = requests.post('http://localhost:5680/_b_a_c_k_e_n_d/HR/canteen/issue-token/', json={})
    assert r.status_code in [200, 400], f"Expected 200 or 400, got {r.status_code}: {r.text}"
run_test("Canteen Kiosk Token Issue Endpoint (canteen/issue-token/)", test_canteen_endpoint)

# 8. Check MongoDB Collections Integrity
def test_db_collections():
    emp_count = Employee.objects.count()
    dev_count = AllowedDevice.objects.count()
    att_count = EmployeeAttendance.objects.count()
    canteen_count = CanteenTokenIssue.objects.count()
    print(f"      DB Counts -> Employees: {emp_count}, Devices: {dev_count}, Attendance Logs: {att_count}, Canteen Tokens: {canteen_count}")
    assert emp_count > 0, "No employees found in DB"
run_test("MongoDB Models & Data Integrity", test_db_collections)

print("\n" + "=" * 60)
passed = sum(1 for _, s, _ in results if s == "PASS")
total = len(results)
print(f"📊 SUMMARY: {passed}/{total} KIOSK AUDIT CHECKS PASSED ({int(passed/total*100)}%)")
print("=" * 60)
