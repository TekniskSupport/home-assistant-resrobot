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
_ENDPOINT = 'https://api.resrobot.se/v2/departureBoard?format=json'

DEFAULT_NAME          = 'ResRobot'
DEFAULT_INTERVAL      = 10
DEFAULT_VERIFY_SSL    = True
CONF_DEPARTURES       = 'departures'
CONF_MAX_JOURNEYS     = 'max_journeys'
CONF_SENSORS          = 'sensors'
CONF_STOP_ID          = 'stop_id'
CONF_KEY              = 'key'
CONF_FILTER           = 'filter'
CONF_FILTER_LINE      = 'line'
CONF_FILTER_DIRECTION = 'direction'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_KEY, default=0): cv.string,
    vol.Required(CONF_DEPARTURES): [{
        vol.Optional(CONF_SENSORS, default=3): cv.positive_int,
        vol.Required(CONF_STOP_ID): cv.positive_int,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_MAX_JOURNEYS, default=20): cv.positive_int,
        vol.Optional(CONF_FILTER, default=[]): [{
            vol.Required(CONF_FILTER_LINE): cv.string,
            vol.Optional(CONF_FILTER_DIRECTION): cv.string,
        }],
    }],
})
SCAN_INTERVAL = timedelta(minutes=DEFAULT_INTERVAL)

async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    sensors    = []
    depatures  = config.get(CONF_DEPARTURES)
    api_key    = config.get(CONF_KEY)

    for departure in config.get(CONF_DEPARTURES):
        await add_sensors(
            hass,
            config,
            async_add_devices,
            api_key,
            departure.get(CONF_SENSORS),
            departure.get(CONF_NAME),
            departure.get(CONF_STOP_ID),
            departure.get(CONF_MAX_JOURNEYS),
            departure.get(CONF_FILTER),
            discovery_info
        )

async def add_sensors(hass, config, async_add_devices, api_key, number_of_sensors, name, location, max_journeys, filter, discovery_info=None):
    method     = 'GET'
    payload    = ''
    auth       = None
    verify_ssl = DEFAULT_VERIFY_SSL
    headers    = {}
    timeout    = 5000
    endpoint   = _ENDPOINT + '&key='+ api_key + '&id=' + str(location) + '&maxJourneys='+ str(max_journeys)

    rest = RestData(method, endpoint, auth, headers, payload, verify_ssl, timeout)

    #Set up empty sensors
    sensors = []
    for i in range(0, number_of_sensors):
        entityName = name + '_' + str(i)
        transportInformation = {}
        sensors.append(entityRepresentation(rest, entityName, i, filter, transportInformation))
    async_add_devices(sensors, True)

class entityRepresentation(Entity):
    """Representation of a sensor."""

    def __init__(self, rest, name, k, filter, data):
        """Initialize a sensor."""
        self._rest       = rest
        self._name       = name
        self._k          = k
        self._filter     = filter
        self._data       = data
        self._unit       = "time"
        self._state      = "Unavailable"
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

    def filterResults(self, trips):
        deleteItems = []
        allowedLines = []
        for filter in self._filter:
            allowedLines.append(int(filter["line"]))
        for k,trip in enumerate(trips):
            del trips[k]["Product"]
            del trips[k]["Stops"]
            for f in self._filter:
                if "line" in f and (int(trip["transportNumber"]) not in allowedLines):
                    deleteItems.append(trip)
                if "direction" in f and trip["transportNumber"] == f["line"]:
                    if trip["direction"].lower() != f["direction"].lower():
                        deleteItems.append(trip)
        for d in deleteItems:
            if d and d in trips:
                trips.remove(d)

        return trips

    async def async_update(self):
        """Get the latest data from the API and updates the state."""
        try:
            getAttributes = [
                "type",
                "stop",
                "direction",
                "time",
                "date"
            ]
            await self._rest.async_update()
            self._result = json.loads(self._rest.data)
            trips = self.filterResults(self._result['Departure'])
            _LOGGER.error('Bussresor efter filtrering: '+ str(len(trips)))

            if (not trips or trips is None):
                _LOGGER.error("ResRobot found no trips")
                return False

            for k,data in enumerate(trips):
                if (k == self._k):
                    self._attributes.update({"name": data["name"]})
                    self._attributes.update({"line": data["transportNumber"]})
                    self._attributes.update({"timeDate": data["date"] +" "+ data["time"]})
                    self._state = data['time']
                    for attribute in data:
                        if attribute in getAttributes and data[attribute]:
                            self._attributes.update({attribute: data[attribute]})
        except TypeError as e:
            self._result = None
            _LOGGER.error(
                "Unable to fetch data from Trafiklab. " + str(e))
