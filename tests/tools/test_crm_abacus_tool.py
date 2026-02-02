"""Tests for CrmAbacusTool."""
import pytest
from guarantee_email_agent.tools.crm_abacus_tool import CrmAbacusTool
from guarantee_email_agent.utils.errors import IntegrationError


@pytest.fixture
def ticket_defaults():
    """Default ticket configuration."""
    return {
        "dzial_id": 2,
        "typ_zadania_id": 156,
        "typ_wykonania_id": 184,
        "organizacja_id": 1,
        "unrecognized_klient_id": 702
    }


@pytest.fixture
def crm_tool(ticket_defaults):
    """Create CrmAbacusTool instance."""
    return CrmAbacusTool(
        base_url="http://crmabacus.suntar.pl:43451",
        username="testowy",
        password="test-pass",
        token_endpoint="/token",
        warranty_endpoint="/klienci/znajdz_po_numerze_seryjnym/",
        ticketing_endpoint="/zadania/dodaj_zadanie/",
        ticket_info_endpoint="/zadania/{zadanie_id}/info/",
        task_info_endpoint="/zadania/{zadanie_id}",
        task_feature_check_endpoint="/zadania/{zadanie_id}/cechy/check",
        ticket_defaults=ticket_defaults,
        agent_disable_feature_name="Wyłącz agenta AI",
        timeout=10
    )


@pytest.mark.asyncio
async def test_token_acquisition(httpx_mock, crm_tool):
    """Test token acquisition flow."""
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "test-token-123", "expires_in": 3600}
    )

    token = await crm_tool._acquire_token()
    assert token == "test-token-123"
    assert crm_tool._access_token == "test-token-123"
    assert crm_tool._token_expires_at is not None

    await crm_tool.close()


@pytest.mark.asyncio
async def test_check_warranty_valid_service_contract(httpx_mock, crm_tool):
    """Test warranty check with valid service contract."""
    # Mock token acquisition
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "test-token-123", "expires_in": 3600}
    )

    # Mock warranty check
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/klienci/znajdz_po_numerze_seryjnym/?serial=ABC123",
        json={
            "urzadzenie_id": 100,
            "klient_id": 456,
            "nazwa": "Test Device",
            "serial": "ABC123",
            "data_stop": "2026-12-31",  # Valid service contract
            "producent_gwarancja_stop": None,
            "typ_gwarancji": "service"
        }
    )

    result = await crm_tool.check_warranty("ABC123")

    assert result["status"] == "valid"
    assert result["warranty_type"] == "service_contract"
    assert result["expires"] == "2026-12-31"
    assert result["device_name"] == "Test Device"
    assert result["serial"] == "ABC123"
    assert result["klient_id"] == 456

    await crm_tool.close()


@pytest.mark.asyncio
async def test_check_warranty_valid_manufacturer(httpx_mock, crm_tool):
    """Test warranty check with valid manufacturer warranty."""
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "test-token-123", "expires_in": 3600}
    )

    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/klienci/znajdz_po_numerze_seryjnym/?serial=XYZ789",
        json={
            "urzadzenie_id": 101,
            "klient_id": 457,
            "nazwa": "Another Device",
            "serial": "XYZ789",
            "data_stop": None,
            "producent_gwarancja_stop": "2026-06-30",  # Valid manufacturer warranty
            "typ_gwarancji": "manufacturer"
        }
    )

    result = await crm_tool.check_warranty("XYZ789")

    assert result["status"] == "valid"
    assert result["warranty_type"] == "manufacturer"
    assert result["expires"] == "2026-06-30"
    assert result["device_name"] == "Another Device"

    await crm_tool.close()


@pytest.mark.asyncio
async def test_check_warranty_expired(httpx_mock, crm_tool):
    """Test warranty check with expired warranty."""
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "test-token-123", "expires_in": 3600}
    )

    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/klienci/znajdz_po_numerze_seryjnym/?serial=OLD123",
        json={
            "urzadzenie_id": 102,
            "klient_id": 458,
            "nazwa": "Old Device",
            "serial": "OLD123",
            "data_stop": "2020-01-01",  # Expired
            "producent_gwarancja_stop": "2020-06-01",  # Expired
            "typ_gwarancji": "expired"
        }
    )

    result = await crm_tool.check_warranty("OLD123")

    assert result["status"] == "expired"
    assert result["warranty_type"] is None

    await crm_tool.close()


@pytest.mark.asyncio
async def test_check_warranty_not_found(httpx_mock, crm_tool):
    """Test warranty check for device not found."""
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "test-token-123", "expires_in": 3600}
    )

    # Mock 404 - check_warranty catches this and returns not_found result (no retry)
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/klienci/znajdz_po_numerze_seryjnym/?serial=NOTFOUND",
        status_code=404
    )

    result = await crm_tool.check_warranty("NOTFOUND")

    assert result["status"] == "not_found"
    assert result["warranty_type"] is None
    assert result["klient_id"] is None

    await crm_tool.close()


@pytest.mark.asyncio
async def test_create_ticket_success(httpx_mock, crm_tool):
    """Test successful ticket creation."""
    # Mock token acquisition
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "test-token-123", "expires_in": 3600}
    )

    # Mock device lookup
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/klienci/znajdz_po_numerze_seryjnym/?serial=ABC123",
        json={
            "urzadzenie_id": 100,
            "klient_id": 456,
            "nazwa": "Test Device",
            "serial": "ABC123"
        }
    )

    # Mock ticket creation
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/zadania/dodaj_zadanie/",
        json={"nowe_zadanie_id": 999, "zadanie_id": 999}
    )

    ticket_id = await crm_tool.create_ticket(
        subject="Test Device:ABC123",
        description="Test description",
        customer_email="test@example.com",
        priority="high"
    )

    assert ticket_id == "999"
    await crm_tool.close()


@pytest.mark.asyncio
async def test_create_ticket_unknown_device(httpx_mock, crm_tool):
    """Test ticket creation with unknown device (uses default klient_id)."""
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "test-token-123", "expires_in": 3600}
    )

    # Mock device not found - create_ticket catches and uses default klient_id
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/klienci/znajdz_po_numerze_seryjnym/?serial=UNKNOWN",
        status_code=404
    )

    # Mock ticket creation with default klient_id
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/zadania/dodaj_zadanie/",
        json={"nowe_zadanie_id": 888}
    )

    ticket_id = await crm_tool.create_ticket(
        subject="Unknown Device:UNKNOWN",
        description="Test",
        customer_email=None,
        priority=None
    )

    assert ticket_id == "888"
    await crm_tool.close()


@pytest.mark.asyncio
async def test_token_refresh_on_401(httpx_mock, crm_tool):
    """Test automatic token refresh on 401 response."""
    # Initial token
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "expired-token", "expires_in": 3600}
    )

    # First request returns 401
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/klienci/znajdz_po_numerze_seryjnym/?serial=ABC123",
        status_code=401
    )

    # Token refresh
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "new-token", "expires_in": 3600}
    )

    # Retry with new token succeeds
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/klienci/znajdz_po_numerze_seryjnym/?serial=ABC123",
        json={
            "urzadzenie_id": 100,
            "klient_id": 456,
            "nazwa": "Test Device",
            "serial": "ABC123"
        }
    )

    device = await crm_tool.find_device_by_serial("ABC123")
    assert device["serial"] == "ABC123"

    await crm_tool.close()


@pytest.mark.asyncio
async def test_get_task_info_success(httpx_mock, crm_tool):
    """Test get task info."""
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "test-token-123", "expires_in": 3600}
    )

    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/zadania/123",
        json={
            "zadanie_id": 123,
            "temat": "Test Task",
            "opis": "Task description",
            "data_dodania": "2025-01-01"
        }
    )

    task_info = await crm_tool.get_task_info(123)
    assert task_info["zadanie_id"] == 123
    assert task_info["temat"] == "Test Task"

    await crm_tool.close()


@pytest.mark.asyncio
async def test_check_agent_disabled_true(httpx_mock, crm_tool):
    """Test agent disabled check returns True."""
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "test-token-123", "expires_in": 3600}
    )

    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/zadania/123/cechy/check?nazwa_cechy=Wy%C5%82%C4%85cz+agenta+AI",
        json={"posiada_ceche": True}
    )

    is_disabled = await crm_tool.check_agent_disabled(123)
    assert is_disabled is True

    await crm_tool.close()


@pytest.mark.asyncio
async def test_check_agent_disabled_false(httpx_mock, crm_tool):
    """Test agent disabled check returns False."""
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "test-token-123", "expires_in": 3600}
    )

    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/zadania/456/cechy/check?nazwa_cechy=Wy%C5%82%C4%85cz+agenta+AI",
        json={"posiada_ceche": False}
    )

    is_disabled = await crm_tool.check_agent_disabled(456)
    assert is_disabled is False

    await crm_tool.close()


@pytest.mark.asyncio
async def test_check_agent_disabled_task_not_found(httpx_mock, crm_tool):
    """Test agent disabled check when task not found (returns False)."""
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "test-token-123", "expires_in": 3600}
    )

    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/zadania/999/cechy/check?nazwa_cechy=Wy%C5%82%C4%85cz+agenta+AI",
        status_code=404
    )

    is_disabled = await crm_tool.check_agent_disabled(999)
    assert is_disabled is False  # Safe default

    await crm_tool.close()


@pytest.mark.asyncio
async def test_add_ticket_info_success(httpx_mock, crm_tool):
    """Test add ticket info."""
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "test-token-123", "expires_in": 3600}
    )

    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/zadania/123/info/",
        json={"success": True}
    )

    await crm_tool.add_ticket_info(123, "Additional info")
    await crm_tool.close()
