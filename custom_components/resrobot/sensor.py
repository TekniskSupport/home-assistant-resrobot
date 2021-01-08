"""
Get data from trafiklab.se / resrobot.se
"""

import logging
import json

from collections import namedtuple
from datetime import datetime,timedelta
import slugify as unicode_slug
import dateparser

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.components.rest.sensor import RestData
from homeassistant.const import (CONF_NAME)
from dateutil import parser
from datetime import datetime

_LOGGER = logging.getLogger(__name__)
_ENDPOINT = 'https://api.resrobot.se/v2/departureBoard?format=json'

DEFAULT_NAME            = 'ResRobot'
DEFAULT_INTERVAL        = 1
DEFAULT_VERIFY_SSL      = True
CONF_DEPARTURES         = 'departures'
CONF_MAX_JOURNEYS       = 'max_journeys'
CONF_SENSORS            = 'sensors'
CONF_STOP_ID            = 'stop_id'
CONF_UPDATE_NAME        = 'update_name'
CONF_KEY                = 'key'
CONF_FILTER             = 'filter'
CONF_FILTER_LINE        = 'line'
CONF_FILTER_TYPE        = 'type'
CONF_FILTER_DIRECTION   = 'direction'
CONF_FETCH_INTERVAL     = 'fetch_interval'
CONF_UNIT               = 'unit'
CONF_TIME_OFFSET        = 'time_offset'
CONF_MEANS_OF_TRANSPORT = 'means_of_transport'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_KEY, default=0): cv.string,
    vol.Optional(CONF_FETCH_INTERVAL): cv.positive_int,
    vol.Required(CONF_DEPARTURES): [{
        vol.Optional(CONF_SENSORS, default=3): cv.positive_int,
        vol.Required(CONF_STOP_ID): cv.positive_int,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_UPDATE_NAME): cv.boolean,
        vol.Optional(CONF_UNIT): cv.string,
        vol.Optional(CONF_TIME_OFFSET): cv.positive_int,
        vol.Optional(CONF_MAX_JOURNEYS, default=20): cv.positive_int,
        vol.Optional(CONF_FILTER, default=[]): [{
            vol.Optional(CONF_MEANS_OF_TRANSPORT): cv.string,
            vol.Optional(CONF_FILTER_LINE): cv.string,
            vol.Optional(CONF_FILTER_TYPE, default="must"): cv.string,
            vol.Optional(CONF_FILTER_DIRECTION): cv.string,
        }],
    }],
})
SCAN_INTERVAL = timedelta(minutes=DEFAULT_INTERVAL)

async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    sensors        = []
    departures     = config.get(CONF_DEPARTURES)
    api_key        = config.get(CONF_KEY)
    fetch_interval = config.get(CONF_FETCH_INTERVAL) if config.get(CONF_FETCH_INTERVAL) else 10

    for departure in departures:
        await add_sensors(
            hass,
            config,
            async_add_devices,
            api_key,
            fetch_interval,
            departure.get(CONF_SENSORS),
            departure.get(CONF_UNIT),
            departure.get(CONF_NAME),
            departure.get(CONF_UPDATE_NAME),
            departure.get(CONF_STOP_ID),
            departure.get(CONF_MAX_JOURNEYS),
            departure.get(CONF_TIME_OFFSET),
            departure.get(CONF_FILTER),
            discovery_info
        )

async def add_sensors(hass, config, async_add_devices, api_key, fetch_interval,
                      number_of_sensors, unit_of_measurement, name, update_name,
                      location, max_journeys, time_offset, filter,
                      discovery_info=None):
    method         = 'GET'
    payload        = ''
    auth           = None
    verify_ssl     = DEFAULT_VERIFY_SSL
    headers        = {}
    params         = {}
    timeout        = 5000
    time           = None
    resource       = _ENDPOINT + '&key='+ api_key + '&id=' + str(location) + '&maxJourneys='+ str(max_journeys)
    sensors        = []
    helpers        = []
    helper         = 'helper_'+name
    base_resource  = resource
    if time_offset:
        time     = dateparser.parse("in " + str(time_offset) + " minutes")
        resource = resource + '&time='+ time.strftime("%H:%M") + '&date=' + time.strftime('%Y-%m-%d')
    rest           = RestData(hass, method, resource, auth, headers, params, payload, verify_ssl, timeout)
    helpers.append(helperEntity(rest, helper, fetch_interval, time_offset, base_resource, filter))
    async_add_devices(helpers, True)

    for i in range(0, number_of_sensors):
        entityName = name + '_' + str(i)
        sensors.append(entityRepresentation(hass, helper, entityName, i,
                                            number_of_sensors,
                                            unit_of_measurement,
                                            update_name,
                                            time_offset))
    async_add_devices(sensors, True)

class helperEntity(Entity):
    def __init__(self, rest, name, fetch_interval, time_offset, base_resource, filter):
        """Initialize a sensor."""
        self._rest        = rest
        self._name        = name
        self._filter      = filter
        self._unit        = "json"
        self._state       = datetime.now()
        self._interval    = int(fetch_interval)
        self._time_offset = time_offset
        self._base_url    = base_resource
        self._attributes  = {}

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
        return 'mdi:code-json'

    def filterResults(self, trips):
        deleteItems             = []
        allowedLines            = []
        allowedMeansOfTransport = []

        for filter in self._filter:
            if "line" in filter:
                allowedLines.append(str(filter["line"]))
        for filter in self._filter:
            if "means_of_transport" in filter:
                allowedMeansOfTransport.append(str(filter["means_of_transport"]))
        for k,trip in enumerate(trips):
            trips[k]["means_of_transport"] = trip["Product"]["catCode"]
            del trips[k]["Product"]
            del trips[k]["Stops"]
            for f in self._filter:
                if "line" in f and str(trip["transportNumber"]) not in allowedLines and allowedLines != []:
                    deleteItems.append(trip)
                if "means_of_transport" in f and str(trip["means_of_transport"]) not in allowedMeansOfTransport and allowedMeansOfTransport != []:
                    deleteItems.append(trip)
                if "direction" in f and (("line" in f and trip["transportNumber"] == f["line"]) or ("means_of_transport" in f and trip["means_of_transport"] == f["means_of_transport"])):
                    if  f["type"] == "must":
                        if trip["direction"].lower() == f["direction"].lower():
                            trips[k]["do_not_delete"] = True
                        else:
                            deleteItems.append(trip)
                    elif f["type"] == "must_not":
                        if trip["direction"].lower() != f["direction"].lower():
                            deleteItems.append(trip)
                    elif f["type"] == "contains":
                        if f["direction"].lower() in trip["direction"].lower():
                            trips[k]["do_not_delete"] = True
                        else:
                            deleteItems.append(trip)
        for d in deleteItems:
            if d and d in trips:
                if "do_not_delete" not in d:
                    trips.remove(d)
        #clean up
        for k,trip in enumerate(trips):
            if "do_not_delete" in trip:
                del trips[k]["do_not_delete"]

        return trips

    async def async_update(self):
        """Get the latest data from the API."""
        try:
            fetch_in_seconds = self._interval*60
            if "json" not in self._attributes or self._state.timestamp()+fetch_in_seconds < datetime.now().timestamp():

                if self._time_offset:
                    time = dateparser.parse("in " + str(self._time_offset) + " minutes")
                    url  = self._base_url + '&time='+ time.strftime("%H:%M") + '&date=' + time.strftime('%Y-%m-%d')
                    self._rest.set_url(url)

                await self._rest.async_update()
                self._result = json.loads(self._rest.data)

                if "Departure" not in self._result:
                    _LOGGER.error("ResRobot found no trips")
                    return False
                trips = self.filterResults(self._result['Departure'])
                self._state = datetime.now()
                self._attributes.update({"json": trips})

        except TypeError as e:
            self._result = None
            _LOGGER.error(
                "Unable to fetch data from Trafiklab. " + str(e))

class entityRepresentation(Entity):
    """Representation of a sensor."""

    def __init__(self, hass, helper, name, k,
                 number_of_sensors, unit_of_measurement,
                 update_name, time_offset):

        """Initialize a sensor."""
        self._hass        = hass
        self._helper      = helper
        self._name        = name
        self._k           = k
        self._s           = number_of_sensors
        self._unit        = unit_of_measurement if unit_of_measurement else "time"
        self._time_offset = time_offset
        self._update_name = update_name
        self._state       = "Unavailable"
        self._attributes  = {}

    def nameToEntityId(self, text: str, *, separator: str = "_") -> str:
        text = text.lower()
        return unicode_slug.slugify(text, separator=separator)

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
        if 'means_of_transport' in self._attributes and self._attributes["means_of_transport"] is not None:
            t = int(self._attributes['means_of_transport'])
            if   t in [1, 2, 4]:
                return "mdi:train"
            elif t in [3, 7]:
                return "mdi:bus"
            elif t in [5]:
                return "mdi:subway"
            elif t in [6]:
                return "mdi:tram"
            elif t in [8]:
                return "mdi:ferry"
            elif t in [9]:
                return "mdi:taxi"
        return 'mdi:bus'

    def filterDeparted(self, trips, time_offset=0):
        for trip in trips:
            removeTrip   = []
            removedTrips = 0
            timeDate     = datetime.strptime(trip["date"]+' '+trip["time"], '%Y-%m-%d %H:%M:%S')
            if timeDate.timestamp() < datetime.now().timestamp():
                removeTrip.append(trip)
            if time_offset:
                if timeDate.timestamp()+(time_offset*60) < datetime.now().timestamp():
                    removeTrip.append(trip)
            for t in removeTrip:
                trips.remove(t)

        return trips

    async def async_update(self):
        """Update sensors using the cached data from helper."""
        try:
            getAttributes = [
                "type",
                "stop",
                "direction",
                "time",
                "date",
                "means_of_transport",
            ]

            trips        = []
            data         = {}
            helper       = self.nameToEntityId(self._helper)
            entity_state = self.hass.states.get('sensor.'+helper)
            if entity_state is not None:
                trips = entity_state.attributes.get('json')

            if trips is not None and len(trips) > 0:
                trips = self.filterDeparted(trips, self._time_offset)
            if trips is None or len(trips) < 1:
                _LOGGER.error("ResRobot found no trips")
                return False

            self._state = "Unavailable"
            for t in getAttributes:
                self._attributes.update({t: None})

            for k,data in enumerate(trips):
                if (k == self._k):
                    if self._update_name:
                        self._name = data["name"]
                    self._attributes.update({"name": data["name"]})
                    self._attributes.update({"line": data["transportNumber"]})
                    if "rTime" in data:
                        self._attributes.update({"timeDate": data["date"] +" "+ data["rTime"]})
                        self._state = data['rTime']
                    else:
                        self._attributes.update({"timeDate": data["date"] +" "+ data["time"]})
                        self._state = data['time']
                    for attribute in data:
                        if attribute in getAttributes and data[attribute]:
                            self._attributes.update({attribute: data[attribute]})

        except TypeError as e:
            self._result = None
            _LOGGER.error(
                "Unable to fetch data from Trafiklab. " + str(e))
