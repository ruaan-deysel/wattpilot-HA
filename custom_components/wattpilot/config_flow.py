"""Config flow for Fronius Wattpilot."""

from __future__ import annotations

import logging
from typing import Any, Final

from homeassistant import config_entries
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import (
    CONF_FRIENDLY_NAME,
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
)
from homeassistant.core import callback

from . import options_update_listener
from .configuration_schema import (
    CLOUD_SCHEMA,
    CONNECTION_SCHEMA,
    LOCAL_SCHEMA,
    async_get_OPTIONS_CLOUD_SCHEMA,
    async_get_OPTIONS_LOCAL_SCHEMA,
)
from .const import (
    CONF_CLOUD,
    CONF_CONNECTION,
    CONF_LOCAL,
    DEFAULT_NAME,
    DOMAIN,
)

REDACT_CONFIG = {CONF_PASSWORD}

_LOGGER: Final = logging.getLogger(__name__)


class ConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Custom config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH
    data: dict[str, Any]
    loaded_platforms: list[str] = []

    def __init__(self) -> None:
        """Initialize."""
        _LOGGER.debug("%s - ConfigFlowHandler: __init__", DOMAIN)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Invoked when a user initiates a flow via the user interface."""
        _LOGGER.debug(
            "%s - ConfigFlowHandler: async_step_user: %s",
            DOMAIN,
            async_redact_data(user_input, REDACT_CONFIG),
        )
        try:
            if not hasattr(self, "data"):
                self.data = {}
            return await self.async_step_connection()
        except Exception as e:
            _LOGGER.error(
                "%s - ConfigFlowHandler: async_step_user failed: %s (%s.%s)",
                DOMAIN,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
            return self.async_abort(reason="exception")

    async def async_step_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Config flow to define a charger connection via user interface."""
        _LOGGER.debug(
            "%s - ConfigFlowHandler: async_step_connection: %s",
            DOMAIN,
            async_redact_data(user_input, REDACT_CONFIG),
        )
        try:
            errors: dict[str, str] = {}
            if user_input is not None:
                _LOGGER.debug(
                    "%s - ConfigFlowHandler: async_step_connection add user_input to data: %s",
                    DOMAIN,
                    async_redact_data(user_input, REDACT_CONFIG),
                )
                if user_input[CONF_CONNECTION] == CONF_LOCAL:
                    return await self.async_step_local()
                if user_input[CONF_CONNECTION] == CONF_CLOUD:
                    return await self.async_step_cloud()
            return self.async_show_form(
                step_id=CONF_CONNECTION, data_schema=CONNECTION_SCHEMA, errors=errors
            )
        except Exception as e:
            _LOGGER.error(
                "%s - ConfigFlowHandler: async_step_connection failed: %s (%s.%s)",
                DOMAIN,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
            return self.async_abort(reason="exception")

    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Config flow to define a local charger connection via user interface."""
        _LOGGER.debug(
            "%s - ConfigFlowHandler: async_step_local: %s",
            DOMAIN,
            async_redact_data(user_input, REDACT_CONFIG),
        )
        try:
            errors: dict[str, str] = {}
            if user_input is not None:
                _LOGGER.debug(
                    "%s - ConfigFlowHandler: async_step_local add user_input to data: %s",
                    DOMAIN,
                    async_redact_data(user_input, REDACT_CONFIG),
                )
                user_input[CONF_CONNECTION] = CONF_LOCAL
                self.data = user_input
                return await self.async_step_final()
            return self.async_show_form(
                step_id=CONF_LOCAL, data_schema=LOCAL_SCHEMA, errors=errors
            )
        except Exception as e:
            _LOGGER.error(
                "%s - ConfigFlowHandler: async_step_local failed: %s (%s.%s)",
                DOMAIN,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
            return self.async_abort(reason="exception")

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Config flow to define a cloud charger connection via user interface."""
        _LOGGER.debug(
            "%s - ConfigFlowHandler: async_step_cloud: %s",
            DOMAIN,
            async_redact_data(user_input, REDACT_CONFIG),
        )
        try:
            errors: dict[str, str] = {}
            if user_input is not None:
                _LOGGER.debug(
                    "%s - ConfigFlowHandler: async_step_cloud add user_input to data: %s",
                    DOMAIN,
                    async_redact_data(user_input, REDACT_CONFIG),
                )
                user_input[CONF_CONNECTION] = CONF_CLOUD
                self.data = user_input
                return await self.async_step_final()
            return self.async_show_form(
                step_id=CONF_CLOUD, data_schema=CLOUD_SCHEMA, errors=errors
            )
        except Exception as e:
            _LOGGER.error(
                "%s - ConfigFlowHandler: async_step_cloud failed: %s (%s.%s)",
                DOMAIN,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
            return self.async_abort(reason="exception")

    async def async_step_final(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Complete the config flow and create the entry."""
        _LOGGER.debug(
            "%s - ConfigFlowHandler: async_step_final: %s",
            DOMAIN,
            async_redact_data(user_input, REDACT_CONFIG),
        )

        # Set unique_id based on IP address or friendly name to prevent duplicates
        unique_id = self.data.get(CONF_IP_ADDRESS) or self.data.get(
            CONF_FRIENDLY_NAME, DEFAULT_NAME
        )
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        title = self.data.get(
            CONF_FRIENDLY_NAME, self.data.get(CONF_IP_ADDRESS, DEFAULT_NAME)
        )
        return self.async_create_entry(title=title, data=self.data)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow handler."""
        _LOGGER.debug("%s: ConfigFlowHandler - async_get_options_flow", DOMAIN)
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        _LOGGER.debug("%s - OptionsFlowHandler: __init__: %s", DOMAIN, config_entry)
        self._config_entry = config_entry
        self.data: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options for the custom component."""
        _LOGGER.debug(
            "%s - OptionsFlowHandler: async_step_init: %s", DOMAIN, user_input
        )
        try:
            if self._config_entry.source == config_entries.SOURCE_USER:
                return await self.async_step_config_connection()
            _LOGGER.warning(
                "%s - OptionsFlowHandler: async_step_init: source not supported: %s",
                DOMAIN,
                self._config_entry.source,
            )
            return self.async_abort(reason="not_supported")
        except Exception as e:
            _LOGGER.error(
                "%s - OptionsFlowHandler: async_step_init failed: %s (%s.%s)",
                DOMAIN,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
            return self.async_abort(reason="exception")

    async def async_step_config_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle connection type selection."""
        _LOGGER.debug(
            "%s - OptionsFlowHandler: async_step_config_connection: %s",
            DOMAIN,
            async_redact_data(user_input, REDACT_CONFIG),
        )
        try:
            if not user_input:
                return self.async_show_form(
                    step_id="config_connection", data_schema=CONNECTION_SCHEMA
                )
            _LOGGER.debug(
                "%s - OptionsFlowHandler: async_step_config_connection - user_input: %s",
                DOMAIN,
                async_redact_data(user_input, REDACT_CONFIG),
            )
            if user_input[CONF_CONNECTION] == CONF_LOCAL:
                return await self.async_step_config_local()
            if user_input[CONF_CONNECTION] == CONF_CLOUD:
                return await self.async_step_config_cloud()
            return self.async_abort(reason="invalid_connection")
        except Exception as e:
            _LOGGER.error(
                "%s - OptionsFlowHandler: async_step_config_connection failed: %s (%s.%s)",
                DOMAIN,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
            return self.async_abort(reason="exception")

    async def async_step_config_local(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle local connection configuration."""
        _LOGGER.debug(
            "%s - OptionsFlowHandler: async_step_config_local: %s",
            DOMAIN,
            async_redact_data(user_input, REDACT_CONFIG),
        )
        try:
            options_local_schema = await async_get_OPTIONS_LOCAL_SCHEMA(
                self._config_entry.data
            )
            if not user_input:
                return self.async_show_form(
                    step_id="config_local", data_schema=options_local_schema
                )
            _LOGGER.debug(
                "%s - OptionsFlowHandler: async_step_config_local - user_input",
                DOMAIN,
            )
            user_input[CONF_CONNECTION] = CONF_LOCAL
            self.data.update(user_input)
            _LOGGER.debug(
                "%s - OptionsFlowHandler: async_step_config_local complete: %s",
                DOMAIN,
                async_redact_data(user_input, REDACT_CONFIG),
            )
            return await self.async_step_final()
        except Exception as e:
            _LOGGER.error(
                "%s - OptionsFlowHandler: async_step_config_local failed: %s (%s.%s)",
                DOMAIN,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
            return self.async_abort(reason="exception")

    async def async_step_config_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle cloud connection configuration."""
        _LOGGER.debug(
            "%s - OptionsFlowHandler: async_step_config_cloud: %s",
            DOMAIN,
            async_redact_data(user_input, REDACT_CONFIG),
        )
        try:
            options_cloud_schema = await async_get_OPTIONS_CLOUD_SCHEMA(
                self._config_entry.data
            )
            if not user_input:
                return self.async_show_form(
                    step_id="config_cloud", data_schema=options_cloud_schema
                )
            _LOGGER.debug(
                "%s - OptionsFlowHandler: async_step_config_cloud - user_input: %s",
                DOMAIN,
                async_redact_data(user_input, REDACT_CONFIG),
            )
            user_input[CONF_CONNECTION] = CONF_CLOUD
            self.data.update(user_input)
            _LOGGER.debug(
                "%s - OptionsFlowHandler: async_step_config_cloud complete: %s",
                DOMAIN,
                async_redact_data(user_input, REDACT_CONFIG),
            )
            return await self.async_step_final()
        except Exception as e:
            _LOGGER.error(
                "%s - OptionsFlowHandler: async_step_config_cloud failed: %s (%s.%s)",
                DOMAIN,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
            return self.async_abort(reason="exception")

    async def async_step_final(self) -> config_entries.ConfigFlowResult:
        """Complete the options flow."""
        try:
            _LOGGER.debug("%s - OptionsFlowHandler: async_step_final", DOMAIN)
            title = self.data.get(
                CONF_FRIENDLY_NAME, self.data.get(CONF_IP_ADDRESS, DEFAULT_NAME)
            )
            if self._config_entry.state is config_entries.ConfigEntryState.SETUP_ERROR:
                _LOGGER.debug(
                    "%s - OptionsFlowHandler: in errorstate - trigger execution of options_update_listener",
                    DOMAIN,
                )
                await options_update_listener(self.hass, self._config_entry)
            return self.async_create_entry(title=title, data=self.data)
        except Exception as e:
            _LOGGER.error(
                "%s - OptionsFlowHandler: async_step_final failed: %s (%s.%s)",
                DOMAIN,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
            return self.async_abort(reason="exception")
