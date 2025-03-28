"""Test the Pterodactyl config flow."""

from pydactyl import PterodactylClient
from pydactyl.exceptions import ClientConfigError, PterodactylApiError
import pytest

from homeassistant.components.pterodactyl.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import TEST_URL, TEST_USER_INPUT

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("mock_pterodactyl", "mock_setup_entry")
async def test_full_flow(hass: HomeAssistant) -> None:
    """Test full flow without errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        flow_id=result["flow_id"],
        user_input=TEST_USER_INPUT,
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_URL
    assert result["data"] == TEST_USER_INPUT


@pytest.mark.usefixtures("mock_setup_entry")
@pytest.mark.parametrize(
    "exception_type",
    [
        ClientConfigError,
        PterodactylApiError,
    ],
)
async def test_recovery_after_api_error(
    hass: HomeAssistant,
    exception_type,
    mock_pterodactyl: PterodactylClient,
) -> None:
    """Test recovery after an API error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    mock_pterodactyl.client.servers.list_servers.side_effect = exception_type

    result = await hass.config_entries.flow.async_configure(
        flow_id=result["flow_id"],
        user_input=TEST_USER_INPUT,
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    mock_pterodactyl.reset_mock(side_effect=True)

    result = await hass.config_entries.flow.async_configure(
        flow_id=result["flow_id"], user_input=TEST_USER_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_URL
    assert result["data"] == TEST_USER_INPUT


@pytest.mark.usefixtures("mock_setup_entry")
async def test_recovery_after_unknown_error(
    hass: HomeAssistant,
    mock_pterodactyl: PterodactylClient,
) -> None:
    """Test recovery after an API error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    mock_pterodactyl.client.servers.list_servers.side_effect = Exception

    result = await hass.config_entries.flow.async_configure(
        flow_id=result["flow_id"],
        user_input=TEST_USER_INPUT,
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}

    mock_pterodactyl.reset_mock(side_effect=True)

    result = await hass.config_entries.flow.async_configure(
        flow_id=result["flow_id"], user_input=TEST_USER_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_URL
    assert result["data"] == TEST_USER_INPUT


@pytest.mark.usefixtures("mock_setup_entry")
async def test_service_already_configured(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_pterodactyl: PterodactylClient,
) -> None:
    """Test config flow abort if the Pterodactyl server is already configured."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=TEST_USER_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
