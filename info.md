# ResRobot integration
## Installation/Configuration:

### To get your api_key:
- register for an account, and
- create a project at https://www.trafiklab.se/node/add/project
- make sure to include the "ResRobot - Stolptidtabeller 2" data source

### How to configure
#### Add the following to resources in your `sensors.yaml`:

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
- stop_id: STOP_ID              # Look in the stops.txt file
  name: Next bus towards the city # Name of sensor
  max_journeys: 20                # Number of departures to fetch
  sensors: 5                      # Number of sensors to create
  fetch_interval: 10              # Minutes between updating the data
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

Replace stop_id with number from [stops.txt](https://raw.githubusercontent.com/TekniskSupport/home-assistant-resrobot/master/stops.txt)
