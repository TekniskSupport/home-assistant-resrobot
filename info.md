# ResRobot integration
## Installation/Configuration:

First off, this integration is compatible with version 0.117.0 and above (to date).

- HACS -> integrations -> [...] -> custom repositories
- TekniskSupport/home-assistant-resrobot
- Integration
- Save
- Install ResRobot
- Add configuration
- Restart home assistant

### To get your api_key:
- register for an account, and
- create a project at https://www.trafiklab.se/node/add/project
- make sure to include the "ResRobot - Stolptidtabeller 2" data source

### How to configure
#### Add the following to resources in your `sensors.yaml`:


## Replace stop_id with number from [stops.txt](https://raw.githubusercontent.com/TekniskSupport/home-assistant-resrobot/master/stops.txt)


A simple setup that creates a few sensors and displays next departures:

```yaml
- platform: resrobot
  key: YOUR-KEY
  departures:
  - stop_id: STOP_ID
    name: Next bus departures
```

You can also filter the results and adjust how many sensors you want:
```yaml
- platform: ResRobot
  fetch_interval: 10                # Minutes between updating the data
  - stop_id: STOP_ID                # Look in the stops.txt file
    name: Next bus towards the city # Name of sensor
    update_name: True               # If true name will be something like "Länstrafik buss 1" instead of next bus towards the city_0
    max_journeys: 20                # Number of departures to fetch
    sensors: 5                      # Number of sensors to create
    time_offset: 10                 # Do not fetch from NOW but now+n minutes, also consider the departed n minutes before it actually departs, e.g. time it takes you to walk to the bus)
    unit: "🕑"                      # unit_of_measurement
    filter:
    - line: 999
      direction: city
    - line: 991
      direction: other end station
    - line: 990
      direction: yet another
```

I have a bus that only departs every so often:

```yaml
- stop_id: 740000000              # Look in the stops.txt file
  name: next commute bus to city  # Name of sensor
  max_journeys: 200               # Higher number as there are quite a few busses that departs in between this one
  sensors: 1                      # Number of sensors to create
  filter:
  - line: 001
    direction: Operan
```

Filter types are applied to direction only
 default type is must
```yaml
  filter:
  - line: 50                  # I want all directions of bus no. 50
  - line: 5                   # Always filter out all lines defined
    type: "must"              # Exact match
    direction: "station"      # station must be exact match of direction, on line 5
  - line: 5                   # Always filter on lines
    type: "must_not"          # must not match
    direction: "mölndal"      # mölndal cannot be an exact match for direction, on line 5
  - line: 6                   # Add line 6 to allowed number
    type: "contains"          # loose match on name
    direction: "kortedala"    # matches if the name kortedala is in the destination
```

The filter means_of_transport works like line, it also get added to an allow list everything not defined in allow is being filtered out. line, means_of_transport and direction can be combined

```yaml
- stop_id: 740001206
  name: saltholmen
  max_journeys: 100
  filter:
  - means_of_transport: 8
    direction: Vrångö
    type: contains
    line: 281
```
This effectively filters out all but ferries to somewhere containing the word "Vrångö" if the line id is 281.

This example:
```yaml
- stop_id: 740001206
  name: saltholmen
  max_journeys: 100
  filter:
  - means_of_transport: 8
  - line: 281
  - line: 283
```
Will filter out anything that is not a ferry and has line number 281 or 283

At this time you cannot filter direction without either line or means_of_transport.

## Replace stop_id with number from [stops.txt](https://raw.githubusercontent.com/TekniskSupport/home-assistant-resrobot/master/stops.txt)
