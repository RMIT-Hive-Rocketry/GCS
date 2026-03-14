# Configs

## Notes

There needs to be a mass refactor. All system parameters should follow the spec below

The `config.ini` file holds some parameters. They can be overridden with CLI arguments or an ignored `.env` file which does not exist yet

## C++

Avoid reading any config values from C++. All config information should be passed from `rocket.py` via CLI arguments
