# cluon-ARS300

Microservice for reading data from an ARS-300 radar module over CAN and sending objects and targets to a cluon multicast group using pycluon

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

    pytest --verbose tests