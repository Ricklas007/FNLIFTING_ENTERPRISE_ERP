from datetime import date, timedelta

from tests.enterprise_test_utils import client, first_truck_id, login_headers


def test_report_exports_gps_geojson_and_backup_verify_workflows():
    api = client()
    headers = login_headers(api)
    date_from = (date.today() - timedelta(days=30)).isoformat()
    date_to = date.today().isoformat()

    report = api.get(f"/api/v1/system/reports/advanced?report_type=operations&date_from={date_from}&date_to={date_to}", headers=headers)
    assert report.status_code == 200, report.text
    assert report.json()["report_type"] == "operations"

    for fmt, expected_type in [("csv", "text/csv"), ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("pdf", "application/pdf")]:
      exported = api.get(f"/api/v1/system/reports/export?format={fmt}&report_type=operations&date_from={date_from}&date_to={date_to}", headers=headers)
      assert exported.status_code == 200, exported.text
      assert exported.headers["content-type"].startswith(expected_type)
      assert exported.content

    geojson = api.get(f"/api/v1/fleet/gps/export.geojson?truck_id={first_truck_id()}", headers=headers)
    assert geojson.status_code == 200, geojson.text
    assert geojson.json()["type"] == "FeatureCollection"

    backup = api.post("/api/v1/system/backups", headers=headers, json={"password": "BackupQA@12345", "include_files": False, "notes": "QA import/export"})
    assert backup.status_code == 201, backup.text
    verified = api.post(f"/api/v1/system/backups/{backup.json()['id']}/verify", headers=headers, json={"password": "BackupQA@12345", "confirm": False})
    assert verified.status_code == 200, verified.text
    assert verified.json()["valid"] is True
    api.close()
