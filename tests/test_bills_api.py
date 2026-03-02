import pytest
from datetime import datetime, timezone, timedelta


def make_bill_data(**kwargs):
    now = datetime.now(timezone.utc)
    defaults = {
        "title": "Electricity Bill",
        "amount": "150.00",
        "bill_date": now.isoformat(),
        "due_date": (now + timedelta(days=7)).isoformat(),
        "vendor": "Power Corp",
        "category": "Utilities",
        "frequency": "monthly",
    }
    defaults.update(kwargs)
    return defaults


class TestCreateBill:
    def test_create_bill_success(self, client, registered_user, auth_headers):
        response = client.post("/api/v1/bills/", json=make_bill_data(), headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Electricity Bill"
        assert data["status"] == "pending"
        assert float(data["amount"]) == 150.00

    def test_create_bill_unauthenticated(self, client):
        response = client.post("/api/v1/bills/", json=make_bill_data())
        assert response.status_code == 401

    def test_create_bill_negative_amount(self, client, registered_user, auth_headers):
        response = client.post(
            "/api/v1/bills/", json=make_bill_data(amount="-50"), headers=auth_headers
        )
        assert response.status_code == 422


class TestGetBills:
    def test_get_bills_empty(self, client, registered_user, auth_headers):
        response = client.get("/api/v1/bills/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["bills"] == []
        assert data["total"] == 0

    def test_get_bills_with_data(self, client, registered_user, auth_headers):
        client.post("/api/v1/bills/", json=make_bill_data(), headers=auth_headers)
        client.post("/api/v1/bills/", json=make_bill_data(title="Water Bill"), headers=auth_headers)
        response = client.get("/api/v1/bills/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 2

    def test_get_bills_pagination(self, client, registered_user, auth_headers):
        for i in range(5):
            client.post("/api/v1/bills/", json=make_bill_data(title=f"Bill {i}"), headers=auth_headers)
        response = client.get("/api/v1/bills/?page=1&per_page=3", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["bills"]) == 3
        assert data["per_page"] == 3


class TestGetBillById:
    def test_get_bill_by_id(self, client, registered_user, auth_headers):
        create_resp = client.post("/api/v1/bills/", json=make_bill_data(), headers=auth_headers)
        bill_id = create_resp.json()["id"]
        response = client.get(f"/api/v1/bills/{bill_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == bill_id

    def test_get_nonexistent_bill(self, client, registered_user, auth_headers):
        import uuid
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/bills/{fake_id}", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateBill:
    def test_update_bill(self, client, registered_user, auth_headers):
        create_resp = client.post("/api/v1/bills/", json=make_bill_data(), headers=auth_headers)
        bill_id = create_resp.json()["id"]
        response = client.put(
            f"/api/v1/bills/{bill_id}",
            json={"title": "Updated Bill", "amount": "200.00"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Bill"


class TestDeleteBill:
    def test_delete_bill(self, client, registered_user, auth_headers):
        create_resp = client.post("/api/v1/bills/", json=make_bill_data(), headers=auth_headers)
        bill_id = create_resp.json()["id"]
        response = client.delete(f"/api/v1/bills/{bill_id}", headers=auth_headers)
        assert response.status_code == 204

        get_resp = client.get(f"/api/v1/bills/{bill_id}", headers=auth_headers)
        assert get_resp.status_code == 404


class TestMarkBillPaid:
    def test_mark_bill_as_paid(self, client, registered_user, auth_headers):
        create_resp = client.post("/api/v1/bills/", json=make_bill_data(), headers=auth_headers)
        bill_id = create_resp.json()["id"]
        response = client.post(
            f"/api/v1/bills/{bill_id}/mark-paid",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "paid"

    def test_mark_already_paid_bill(self, client, registered_user, auth_headers):
        create_resp = client.post("/api/v1/bills/", json=make_bill_data(), headers=auth_headers)
        bill_id = create_resp.json()["id"]
        client.post(f"/api/v1/bills/{bill_id}/mark-paid", json={}, headers=auth_headers)
        response = client.post(
            f"/api/v1/bills/{bill_id}/mark-paid", json={}, headers=auth_headers
        )
        assert response.status_code == 400
