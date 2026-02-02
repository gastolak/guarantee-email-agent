# CRM Abacus API Specification (Validated from OpenAPI Docs)

**Source**: `http://crmabacus.suntar.pl:43451/docs` (FastAPI/Swagger OpenAPI 3.1.0)
**Validation Date**: 2026-02-02
**API Version**: 1.0.0 alfa

---

## Authentication

### POST `/token`

**Purpose**: Acquire JWT access token for Bearer authentication

**Request Format**: `application/x-www-form-urlencoded` (NOT JSON!)

**Request Parameters**:
- `username` (string, required): User login name
- `password` (string, required): User password

**Response** (200 OK):
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Usage in Subsequent Requests**:
```
Authorization: Bearer {access_token}
```

**Example**:
```bash
curl -X POST "http://crmabacus.suntar.pl:43451/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testowy&password=kCDOn4JQhkfHBOl"
```

---

## Device/Client Lookup

### GET `/klienci/znajdz_po_numerze_seryjnym/`

**Purpose**: Find client and warranty information by device serial number

**Authentication**: Required (Bearer token)

**Query Parameters**:
- `serial` (string, required): Device serial number
  - Example: `"C074AD3D3102 22480L9010542"`

**Response** (200 OK) - Schema: `SerialKlient`:
```json
{
  "urzadzenie_id": 123,
  "serial": "C074AD3D3102 22480L9010542",
  "symbol": "DEVICE-001",
  "nazwa": "RICOH MP 2555",

  // Manufacturer warranty info
  "producent_gwarancja_start": "2024-01-15",
  "producent_okres_gwarancji": 36,
  "producent_gwarancja_stop": "2027-01-15",
  "producent_gwarancja_typ_gwarancji": "ON-SITE",
  "producent_gwarancja_czas_reakcji": 8,
  "producent_gwarancja_czas_naprawy": 24,
  "producent_gwarancja_uwagi": "Gwarancja producenta 3 lata",

  // Service contract info (if applicable)
  "umowa_id": 456,
  "nr_umowy": "SLA-2024-001",
  "data_start": "2024-01-01",
  "data_stop": "2026-12-31",
  "okres_gwarancji": 36,
  "typ_gwarancji": "FULL SERVICE",
  "gwarancja_uwagi": "Pełny serwis z wymianą części",

  // SLA response times
  "czas_reakcji_typ": 1,
  "czas_reakcji": 4,
  "typ_reakcji_nazwa": "4h w godzinach pracy",
  "czas_reakcji_godzina_do": "17:00",
  "czas_reakcji_opis": "Reakcja w ciągu 4h w godz. 8-17",

  // SLA repair times
  "czas_naprawy_typ": 1,
  "czas_naprawy": 24,
  "typ_naprawy_nazwa": "24h robocze",
  "czas_naprawy_godzina_do": "17:00",
  "czas_naprawy_opis": "Naprawa w ciągu 24h roboczych",

  // Client info
  "klient_id": 789,
  "adres_id": 101
}
```

**Required Fields**:
- `urzadzenie_id` (integer)
- `serial` (string)
- `symbol` (string)
- `nazwa` (string)

**All other fields are optional** (nullable) - may be `null` if no warranty/contract exists

**Response** (404 Not Found):
- Device not found in database

**Warranty Status Logic**:
1. Check `data_stop` (service contract end date) - if exists and future → valid service contract
2. Check `producent_gwarancja_stop` (manufacturer warranty end) - if exists and future → valid manufacturer warranty
3. If both null or past → no active warranty

---

## Task/Ticket Management

### POST `/zadania/dodaj_zadanie/`

**Purpose**: Create new service task/ticket

**Authentication**: Required (Bearer token)

**Request Format**: `application/json`

**Request Body** - Schema: `ZadanieZPortaluCreate`:
```json
{
  "klient_id": 789,              // Required if known, default: 702 (unrecognized client)
  "dzial_id": 2,                 // Default: 2 (Customer Service Department)
  "typ_zadania_id": 156,         // Default: 156 (!Service Request)
  "typ_wykonania_id": 184,       // Default: 184 (Awaiting Request Review)
  "organizacja_id": 1,           // Default: 1 (Suntar), 2=Acnet, 4=SPS
  "temat": "RICOH MP 2555:C074AD3D3102 22480L9010542",  // Required, max 255 chars
  "opis": "Customer reports paper jam error E401. Device under warranty."  // Required
}
```

**Required Fields**:
- `temat` (string, max 255 chars): Brief subject line
- `opis` (string): Detailed description

**Default Values** (per API docs):
- `klient_id`: 702 (use when client not recognized)
- `dzial_id`: 2 (Customer Service Department / Biuro obsługi klienta)
- `typ_zadania_id`: 156 (!Service Request / !Zgłoszenie serwisowe)
- `typ_wykonania_id`: 184 (Awaiting Review / Oczekuje na rozpatrzenie zgłoszenia)
- `organizacja_id`: 1 (Suntar)

**Response** (201 Created):
```json
{
  "nowe_zadanie_id": 12345,
  // Additional fields may be present
}
```

**Response** (404 Not Found):
- Invalid klient_id or other referenced ID not found

---

### POST `/zadania/{zadanie_id}/info/`

**Purpose**: Add informational note/comment to existing task

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `zadanie_id` (integer, required): Task ID

**Request Format**: `application/json`

**Request Body** - Schema: `ZadanieInfoCreate`:
```json
{
  "opis": "Contacted customer, scheduled technician visit for 2026-02-05",  // Required, max 1024 chars
  "publiczne": false,            // Default: false (not visible to client in portal)
  "operacja_id": 0               // Default: 0 (no specific operation type)
}
```

**Required Fields**:
- `opis` (string, max 1024 chars): Note content

**Default Values**:
- `publiczne`: false (private note)
- `operacja_id`: 0 (no operation)

**Response** (201 Created) - Schema: `ZadanieInfo`:
```json
{
  "zadanie_info_id": 67890,
  "zadanie_id": 12345,
  "opis": "Contacted customer...",
  "publiczne": false,
  "operacja_id": 0,
  "data_dodania": "2026-02-02T17:50:19",
  // Additional fields
}
```

**Response** (404 Not Found):
- Task with `zadanie_id` not found

---

## Additional Endpoints (Not Currently Used)

### GET `/klienci/znajdz_po_emailu/`

**Purpose**: Find client by email address

**Query Parameters**:
- `email` (string, required): Email address to search

**Response**: `KlientKontakt` schema with `nadawca_kontakt_id` and `klient_id`

---

### GET `/zadania/{zadanie_id}/cechy/check`

**Purpose**: Check if task has specific feature/attribute

**Query Parameters**:
- `nazwa_cechy` (string, required): Exact feature name (e.g., "Wyłącz agenta AI")

**Response**: `CechaCheckResponse` - boolean indicating if feature exists

**Potential Use**: Could check for "Wyłącz agenta AI" flag to disable automated responses

---

## Implementation Notes for Story 4.6

### ✅ **COMPLIANT**: Token Acquisition
- Story correctly specifies `application/x-www-form-urlencoded`
- Field names match: `username`, `password`
- Response field: `access_token` (correct)
- Bearer token authentication (correct)

### ✅ **COMPLIANT**: Device Lookup Endpoint
- Endpoint: `/klienci/znajdz_po_numerze_seryjnym/` ✅
- Query param: `serial` ✅
- Response has `klient_id`, `nazwa`, `serial` ✅

### ⚠️ **NEEDS UPDATE**: Warranty Logic
**Current Story Issue**: Story mentions `find_device_by_serial` returning `cecha_nazwa` field for warranty status
**Reality**: No `cecha_nazwa` field in `SerialKlient` schema. Warranty info comes from:
- `data_stop` (service contract end date)
- `producent_gwarancja_stop` (manufacturer warranty end date)

**Recommended Warranty Check Logic**:
```python
def determine_warranty_status(device_data: dict) -> str:
    """Determine warranty status from SerialKlient response."""
    from datetime import date

    today = date.today()

    # Check service contract first (higher priority)
    if device_data.get("data_stop"):
        contract_end = date.fromisoformat(device_data["data_stop"])
        if contract_end >= today:
            return "valid"  # Active service contract

    # Check manufacturer warranty
    if device_data.get("producent_gwarancja_stop"):
        warranty_end = date.fromisoformat(device_data["producent_gwarancja_stop"])
        if warranty_end >= today:
            return "valid"  # Active manufacturer warranty

    # Check if device was found but no warranty data at all
    if not device_data.get("data_stop") and not device_data.get("producent_gwarancja_stop"):
        return "not_found"  # No warranty info available

    return "expired"  # All warranties expired
```

### ✅ **COMPLIANT**: Ticket Creation
- Endpoint: `/zadania/dodaj_zadanie/` ✅
- Required fields: `temat`, `opis` ✅
- Optional with defaults: `klient_id` (702), `dzial_id` (2), `typ_zadania_id` (156), `typ_wykonania_id` (184), `organizacja_id` (1) ✅
- Response field: `nowe_zadanie_id` ✅

### ⚠️ **MINOR UPDATE**: Ticket Creation Field Names
**Story says**: Extract `dzial_id`, `typ_zadania_id`, etc. from config "defaults"
**Reality**: These have API-level defaults, but should still be configurable

**Recommended Config Structure**:
```yaml
tools:
  crm_abacus:
    base_url: "http://crmabacus.suntar.pl:43451"
    token_endpoint: "/token"
    warranty_endpoint: "/klienci/znajdz_po_numerze_seryjnym/"
    ticketing_endpoint: "/zadania/dodaj_zadanie/"
    ticket_info_endpoint: "/zadania/{zadanie_id}/info/"
    timeout_seconds: 10
    # Ticket defaults (match API defaults)
    ticket_defaults:
      dzial_id: 2                    # Customer Service
      typ_zadania_id: 156            # Service Request
      typ_wykonania_id: 184          # Awaiting Review
      organizacja_id: 1              # Suntar
      unrecognized_klient_id: 702    # Default for unknown clients
```

### ✅ **COMPLIANT**: Ticket Info Endpoint
- Endpoint: `/zadania/{zadanie_id}/info/` ✅
- Path parameter: `zadanie_id` ✅
- Required field: `opis` ✅
- Defaults: `publiczne: false`, `operacja_id: 0` ✅

### ⚠️ **CORRECTION**: Ticket Info Endpoint URL
**Story says**: `/zadania/{zadanie_id}/info`
**Reality**: `/zadania/{zadanie_id}/info/` (with trailing slash)

**Impact**: Minor - httpx may handle redirects, but better to use correct URL

---

## Critical Corrections Needed in Story 4.6

1. **Warranty Status Logic** (HIGH PRIORITY)
   - Remove `cecha_nazwa` parsing logic (field doesn't exist)
   - Add date-based warranty validation logic using `data_stop` and `producent_gwarancja_stop`
   - Update `check_warranty()` return schema to include warranty dates and type

2. **Add Trailing Slash to Ticket Info Endpoint** (MEDIUM PRIORITY)
   - Change: `/zadania/{zadanie_id}/info` → `/zadania/{zadanie_id}/info/`

3. **Clarify Ticket Defaults Configuration** (LOW PRIORITY)
   - Add `ticket_defaults` section to config
   - Document default IDs (702, 2, 156, 184, 1)

4. **Add SerialKlient Response Fields** (MEDIUM PRIORITY)
   - Update response schema documentation to include full field list
   - Clarify which fields are required vs optional

---

## Testing Recommendations

1. **Token Acquisition Test**:
   ```python
   # Test form-encoded POST (not JSON!)
   response = await client.post("/token", data={"username": "test", "password": "pass"})
   assert "access_token" in response.json()
   ```

2. **Device Lookup Test**:
   ```python
   # Test serial number lookup
   response = await client.get("/klienci/znajdz_po_numerze_seryjnym/", params={"serial": "TEST123"})
   assert response.json()["klient_id"] is not None
   ```

3. **Warranty Logic Test**:
   ```python
   # Test date-based warranty validation
   device_data = {"data_stop": "2027-12-31"}
   status = determine_warranty_status(device_data)
   assert status == "valid"
   ```

4. **Ticket Creation Test**:
   ```python
   # Test with defaults
   response = await client.post("/zadania/dodaj_zadanie/", json={"temat": "Test", "opis": "Test desc"})
   assert "nowe_zadanie_id" in response.json()
   ```

---

## References

- OpenAPI Spec: `http://crmabacus.suntar.pl:43451/openapi.json`
- Swagger UI: `http://crmabacus.suntar.pl:43451/docs`
- API Version: 1.0.0 alfa
- Framework: FastAPI with OAuth2 Password Bearer authentication
