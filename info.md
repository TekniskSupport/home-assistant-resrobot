# ResRobot integration

## Installation/Configuration:

Add the following to resources in your sensors.yaml:

```yaml
- platform: resrobot
  location: 123
  maxJourneys: 5
```

Or if you want multiple locations

```yaml
- platform: resrobot
  location: 123,456,789
  maxJourneys: 5
```

Replace location with number from from url from [stops.txt] after selecting stop
