"""
Get data from trafiklab.se / resrobot.se
"""

import logging
import json

from collections import namedtuple
from datetime import timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.components.rest.sensor import RestData
from homeassistant.const import (CONF_NAME)
from dateutil import parser
from datetime import datetime

_LOGGER = logging.getLogger(__name__)
_ENDPOINT = 'https://api.resrobot.se/v2/departureBoard?id=740051093&maxJourneys=5&format=json'

DEFAULT_NAME       = 'ResRobot'
DEFAULT_INTERVAL   = 5
DEFAULT_VERIFY_SSL = True
CONF_DEPARTURES    = 'departures'
CONF_MAX_JOURNEYS  = 'max_journeys'
CONF_STOP_ID       = 'stop_id'
CONF_KEY           = 'key'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_KEY, default=0): cv.string,
    vol.Optional(CONF_DEPARTURES): [{
        vol.Required(CONF_STOP_ID): cv.string,
        vol.Optional(CONF_MAX_JOURNEYS, default=5): cv.string,
        vol.Optional(CONF_NAME): cv.string}],
})

SCAN_INTERVAL = timedelta(minutes=DEFAULT_INTERVAL)

def setup_platform(hass, config, add_devices, discovery_info=None):
    sensors    = []
    depatures  = config.get(CONF_DEPARTURES)

    for departure in config.get(CONF_DEPARTURES):
        add_sensors(
            hass,
            config,
            add_devices,
            departure.get(CONF_NAME),
            departure.get(CONF_STOP_ID),
            discovery_info
        )

def add_sensors(hass, config, add_devices, name, location, discovery_info=None):
    method     = 'GET'
    payload    = ''
    auth       = ''
    verify_ssl = DEFAULT_VERIFY_SSL
    headers    = {}
    endpoint   = _ENDPOINT + location
    rest = RestData(method, endpoint, auth, headers, payload, verify_ssl)
    rest.update()

    if rest.data is None:
        _LOGGER.error("Unable to fetch data from Trafiklab")
        return False

    restData = json.loads(rest.data)
    sensors = []

    for data in restData['Departure']:
        transportInformation = {
            name:      data['name'],
            direction: data['direction'],
            time:      data['time'],
            date:      data['date'],
        }
        sensors.append(entityRepresentation(rest, name, location, transportInformation))
    add_devices(sensors, True)

# pylint: disable=no-member
class entityRepresentation(Entity):
    """Representation of a sensor."""

    def __init__(self, rest, prefix, location, data):
        """Initialize a sensor."""
        self._rest       = rest
        self._prefix     = prefix
        self._location   = location
        self._data       = data
        self._attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        if self._state is not None:
            return self._state
        return None

    @property
    def device_state_attributes(self):
        """Return the state attributes of the monitored installation."""
        if self._attributes is not None:
            return self._attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if self._unit is not None:
            return self._unit

    @property
    def icon(self):
        return 'mdi:bus'

    def update(self):
        """Get the latest data from the API and updates the state."""
        try:
            getAttributes = [
                "name",
                "direction",
                "time",
                "date",
            ]

            self._rest.update()
            self._result                   = json.loads(self._rest.data)
            self._name                     = self._prefix + '_' + self._location + '_' + self._data['name']
            for data in self._result['GetSingleStationResult']['Samples']:
                if self._name == self._prefix + '_' + self._location + '_' + data['Name']:
                    self._unit    = 'hours'
                    self._state   = data['time']
                    # self._attributes.update({"last_modified": data['Updated']})
                    for attribute in data:
                        if attribute in getAttributes and data[attribute]:
                            self._attributes.update({attribute: data[attribute]})
        except TypeError as e:
            self._result = None
            _LOGGER.error(
                "Unable to fetch data from trafiklab. " + str(e))
