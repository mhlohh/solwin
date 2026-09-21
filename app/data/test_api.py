import sys
import time
import requests

BASE_URL = "http://localhost:8000"

def run_tests():
    print("==================================================")
    print("       STARTING API VALIDATION & TESTING         ")
    print("==================================================\n")

    # Check connection
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        r.raise_for_status()
        print(" [HEALTH CHECK] Connected to API server successfully.\n")
    except Exception as e:
        print(f" [ERROR] Could not connect to API server at {BASE_URL}: {e}")
        sys.exit(1)

    # ----------------------------------------------------
    # Test 1: Verify Data Seeding
    # ----------------------------------------------------
    print("--- Test 1: Verify Data Seeding ---")
    res = requests.get(f"{BASE_URL}/tickets?skip=0&limit=10")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    total_records = data.get("total", 0)
    items = data.get("items", [])
    print(f"Status Code: {res.status_code}")
    print(f"Total Tickets Seeded: {total_records}")
    print(f"Sample Items Retrieved: {len(items)}")
    assert total_records > 0, "Error: No seeded tickets found in database!"
    assert len(items) > 0, "Error: Empty items array returned!"
    print(" [PASSED] Test 1: Data Seeding verified successfully.\n")

    # ----------------------------------------------------
    # Test 2: CRUD Operations - Create & Read
    # ----------------------------------------------------
    print("--- Test 2: CRUD Operations - Create & Read ---")
    new_ticket_payload = {
        "subject": "Automated Test Ticket - Phishing Alert",
        "message": "Suspicious email received with unknown external attachment.",
        "intent": "Fraudulent User",
        "issue": "Phishing Attempt"
    }
    create_res = requests.post(f"{BASE_URL}/tickets", json=new_ticket_payload)
    assert create_res.status_code == 201, f"Expected 201, got {create_res.status_code}: {create_res.text}"
    created_ticket = create_res.json()
    ticket_id = created_ticket["id"]
    print(f"Created Ticket ID: {ticket_id}")

    # Read ticket by ID
    get_res = requests.get(f"{BASE_URL}/tickets/{ticket_id}")
    assert get_res.status_code == 200, f"Expected 200, got {get_res.status_code}: {get_res.text}"
    fetched_ticket = get_res.json()
    print(f"Fetched Ticket Subject: {fetched_ticket['subject']}")
    assert fetched_ticket["subject"] == new_ticket_payload["subject"], "Subject mismatch!"
    print(" [PASSED] Test 2: Create & Read verified successfully.\n")

    # ----------------------------------------------------
    # Test 3: CRUD Operations - Update
    # ----------------------------------------------------
    print("--- Test 3: CRUD Operations - Update ---")
    update_payload = {
        "issue": "Verified Phishing Attempt - Escalated to SOC"
    }
    update_res = requests.put(f"{BASE_URL}/tickets/{ticket_id}", json=update_payload)
    assert update_res.status_code == 200, f"Expected 200, got {update_res.status_code}: {update_res.text}"
    
    # Verify update persisted
    get_updated = requests.get(f"{BASE_URL}/tickets/{ticket_id}")
    assert get_updated.status_code == 200, f"Expected 200, got {get_updated.status_code}: {get_updated.text}"
    updated_ticket = get_updated.json()
    print(f"Updated Issue Field: {updated_ticket['issue']}")
    assert updated_ticket["issue"] == update_payload["issue"], "Issue field was not updated!"
    print(" [PASSED] Test 3: Update verified successfully.\n")

    # ----------------------------------------------------
    # Test 4: File Upload & Retrieval (PDF & Image)
    # ----------------------------------------------------
    print("--- Test 4: File Upload & Retrieval ---")
    # Valid 1x1 PNG image byte array
    dummy_png_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc`\x00\x00'
        b'\x00\x02\x00\x01\xe2\x21\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    # Minimal PDF structure byte array
    dummy_pdf_bytes = (
        b'%PDF-1.4\n'
        b'1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n'
        b'2 0 obj << /Type /Pages /Kids [] /Count 0 >> endobj\n'
        b'xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000062 00000 n \n'
        b'trailer << /Size 3 /Root 1 0 R >>\n'
        b'startxref\n118\n%%EOF\n'
    )

    # Upload Image
    upload_img_res = requests.post(
        f"{BASE_URL}/tickets/{ticket_id}/attachments",
        files={"file": ("sample_screenshot.png", dummy_png_bytes, "image/png")}
    )
    assert upload_img_res.status_code == 201, f"Expected 201, got {upload_img_res.status_code}: {upload_img_res.text}"
    img_attachment = upload_img_res.json()
    img_attachment_id = img_attachment["id"]
    print(f" Uploaded Image Attachment ID: {img_attachment_id} ({img_attachment['file_name']})")

    # Upload PDF
    upload_pdf_res = requests.post(
        f"{BASE_URL}/tickets/{ticket_id}/attachments",
        files={"file": ("sample_report.pdf", dummy_pdf_bytes, "application/pdf")}
    )
    assert upload_pdf_res.status_code == 201, f"Expected 201, got {upload_pdf_res.status_code}: {upload_pdf_res.text}"
    pdf_attachment = upload_pdf_res.json()
    pdf_attachment_id = pdf_attachment["id"]
    print(f" Uploaded PDF Attachment ID: {pdf_attachment_id} ({pdf_attachment['file_name']})")

    # List attachments for ticket
    list_attach_res = requests.get(f"{BASE_URL}/tickets/{ticket_id}/attachments")
    assert list_attach_res.status_code == 200, f"Expected 200, got {list_attach_res.status_code}: {list_attach_res.text}"
    attachments_list = list_attach_res.json()
    print(f" Retrieved Attachments Count: {len(attachments_list)}")
    assert len(attachments_list) == 2, "Expected 2 attachments for ticket!"

    # Download one attachment
    download_res = requests.get(f"{BASE_URL}/attachments/{pdf_attachment_id}")
    assert download_res.status_code == 200, f"Expected 200, got {download_res.status_code}"
    print(f" Downloaded Attachment {pdf_attachment_id} Status Code: {download_res.status_code}")
    assert len(download_res.content) == len(dummy_pdf_bytes), "Downloaded byte size mismatch!"
    print(" [PASSED] Test 4: File Upload & Retrieval verified successfully.\n")

    # ----------------------------------------------------
    # Test 5: MIME-Type Validation (Error Handling)
    # ----------------------------------------------------
    print("--- Test 5: MIME-Type Validation (Error Handling) ---")
    dummy_txt_bytes = b"Hello, this is a plain text file."
    bad_upload_res = requests.post(
        f"{BASE_URL}/tickets/{ticket_id}/attachments",
        files={"file": ("unauthorized.txt", dummy_txt_bytes, "text/plain")}
    )
    print(f" Upload response status code for text/plain: {bad_upload_res.status_code}")
    print(f" Server response error message: {bad_upload_res.json().get('detail')}")
    assert bad_upload_res.status_code == 400, f"Expected 400 Bad Request, got {bad_upload_res.status_code}"
    print(" [PASSED] Test 5: MIME-Type Validation verified successfully.\n")

    # ----------------------------------------------------
    # Test 6: CRUD Operations - Delete
    # ----------------------------------------------------
    print("--- Test 6: CRUD Operations - Delete ---")
    del_res = requests.delete(f"{BASE_URL}/tickets/{ticket_id}")
    assert del_res.status_code == 200, f"Expected 200, got {del_res.status_code}: {del_res.text}"
    print(f" Deleted Ticket ID {ticket_id}. Message: {del_res.json().get('message')}")

    # Verify 404 on fetch
    get_deleted = requests.get(f"{BASE_URL}/tickets/{ticket_id}")
    assert get_deleted.status_code == 404, f"Expected 404 Not Found, got {get_deleted.status_code}"
    print(f" Confirming ticket retrieval returns 404 Not Found: Status {get_deleted.status_code}")
    print(" [PASSED] Test 6: Delete verified successfully.\n")

    print("==================================================")
    print("    ALL API VALIDATION TESTS PASSED (6/6)         ")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
