# cluon-ARS300

Microservice for reading data from an ARS-300 radar module over CAN and sending frames (list of targets) to a cluon multicast group using pycluon

## Data description

For each target, the following data values will be sent

 | Signal | [unit] | description | 
 | --- | --- | --- | 
 | sample_time | [s] | time since epoch in  (according to computer running micro service) | 
 | Tar_Dist_rms | [m] | Target range standard deviation | 
 | Tar_Ang_rms | [deg] | Target angle standard deviation | 
 | Tar_Vrel_rms | [m/s] | Target relative velocity standard deviation (to/from radar) | 
 | Tar_Vrel | [m/s] | Target relative velocity (to/from radar; positive likely towards radar, negative away from) | 
 | Tar_Dist | [m] | Target range | 
 | Tar_PdH0 | [%] | Target false alarm probability | 
 | Tar_Length | [m] | Target length (likely range direction) | 
 | Tar_Width | [m] | Target width (likely azimuth direction) | 
 | Tar_Type | [N/A] | Target type -  0:No target, 1:Oncoming, 2:Stationary, 3:Traced (targets moving in the same direction) | 
 | Tar_Ang_stat | [N/A] | Target angle status - 0:Expanded target, 1:Point target, 2:Digital, 3:Invalid (should be ignored, because it is invalid) | 
 | Tar_Ang | [deg] | Target angle | 
 | Tar_RCSValue | [dBm2] | Radar cross section | 

## Production setup
```yaml
version: '3'
services:
  ars300-radar:
    image: ghcr.io/mo-rise/cluon-ars300
    restart: unless-stopped
    network_mode: "host"
    environment:
      - CLUON_CID=121
      - CANBUS_CHANNEL=0
      - CANBUS_TYPE=kvaser
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"
```

## Development setup
To setup the development environment:

    python3 -m venv venv
    source ven/bin/activate

Install everything thats needed for development:

    pip install -r requirements.txt -r requirements_dev.txt

To run the linters:

    black main.py tests
    pylint --extension-pkg-allow-list=pycluon  main.py

To run the tests:

    python -m pytest --verbose tests