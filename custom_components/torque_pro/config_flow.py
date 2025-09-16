# -*- coding: utf-8 -*-
"""Adds config flow for Torque Pro."""
from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .const import (
    NAME,
    DOMAIN,
    CONF_EMAIL,
    CONF_IMPERIAL,
    CONF_LANGUAGE,
    CONF_SESSION_TTL,
    CONF_MAX_SESSIONS,
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGS,
    SESSION_TTL_SECONDS,
    MAX_SESSIONS,
)


def _codes_from_supported_langs(supported) -> list[str]:
    """Return a list of language codes from SUPPORTED_LANGS whatever its type."""
    if isinstance(supported, (list, tuple, set)):
        return list(supported)
    if isinstance(supported, dict):
        return list(supported.keys())
    return [str(supported)]


_LANG_LABELS = {
    "en": "English",
    "fr": "Français",
}


class TorqueFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Torque Pro."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """Handle the initial step."""
        codes = _codes_from_supported_langs(SUPPORTED_LANGS)
        lang_options = [{"label": _LANG_LABELS.get(c, c), "value": c} for c in codes]

        errors: dict[str, str] = {}

        if user_input is not None:
            email = str(user_input.get(CONF_EMAIL, "")).strip().lower()
            imperial = bool(user_input.get(CONF_IMPERIAL, False))
            language = user_input.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)

            if not email:
                errors[CONF_EMAIL] = "email_required"
            elif "@" not in email or "." not in email:
                errors[CONF_EMAIL] = "invalid_email"

            if not errors:
                # Unique ID par e-mail pour permettre plusieurs comptes/configs.
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_configured()

                data = {
                    CONF_EMAIL: email,
                    CONF_IMPERIAL: imperial,
                    CONF_LANGUAGE: language if language in codes else DEFAULT_LANGUAGE,
                }
                title = f"{NAME} ({email})"
                return self.async_create_entry(title=title, data=data)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.EMAIL)
                ),
                vol.Optional(CONF_IMPERIAL, default=False): bool,
                vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): SelectSelector(
                    SelectSelectorConfig(
                        options=lang_options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_import(self, user_input: dict):
        """Support YAML → UI import if legacy YAML existed."""
        return await self.async_step_user(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow.

        Ne PAS passer config_entry au constructeur : le framework l’injecte.
        """
        return TorqueOptionsFlowHandler()


class TorqueOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow handler for Torque Pro.

    Ne pas définir __init__(self, config_entry) ni self.config_entry = config_entry.
    Home Assistant fournit self.config_entry automatiquement.
    """

    async def async_step_init(self, user_input: dict | None = None):
        codes = _codes_from_supported_langs(SUPPORTED_LANGS)
        lang_options = [{"label": _LANG_LABELS.get(c, c), "value": c} for c in codes]

        if user_input is not None:
            lang = user_input.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
            user_input[CONF_LANGUAGE] = lang if lang in codes else DEFAULT_LANGUAGE
            return self.async_create_entry(title="", data=user_input)

        # Lire valeurs actuelles depuis options (fallback sur data)
        current_imperial = self.config_entry.options.get(
            CONF_IMPERIAL, self.config_entry.data.get(CONF_IMPERIAL, False)
        )
        current_language = self.config_entry.options.get(
            CONF_LANGUAGE, self.config_entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
        )
        if current_language not in codes:
            current_language = DEFAULT_LANGUAGE

        current_ttl = int(self.config_entry.options.get(CONF_SESSION_TTL, SESSION_TTL_SECONDS))
        current_max = int(self.config_entry.options.get(CONF_MAX_SESSIONS, MAX_SESSIONS))

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_IMPERIAL, default=current_imperial): bool,
                vol.Optional(CONF_LANGUAGE, default=current_language): SelectSelector(
                    SelectSelectorConfig(
                        options=lang_options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                # TTL: 1 minute à 24 h
                vol.Optional(CONF_SESSION_TTL, default=current_ttl): vol.All(
                    vol.Coerce(int), vol.Range(min=60, max=86400)
                ),
                # Taille: 10 à 1000 sessions
                vol.Optional(CONF_MAX_SESSIONS, default=current_max): vol.All(
                    vol.Coerce(int), vol.Range(min=10, max=1000)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)
