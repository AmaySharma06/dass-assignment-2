# DASS Assignment 2 - 2024101095

Git Repository: `https://github.com/AmaySharma06/dass-assignment-2`
OneDrive Link: `https://iiithydstudents-my.sharepoint.com/:u:/g/personal/amay_sharma_students_iiit_ac_in/IQBC3JDhTm1bS7OnDcmatGsAAcoMkn5GjFeytohPaeRzFi8?e=6R9D0E`
## Requirements

- Python 3.10+ (tested on Python 3.12)
- `pytest`
- `requests` (for black-box API tests)

Install dependencies:

```bash
pip install pytest requests
```

## Folder Layout

- `whitebox/`: MoneyPoly white-box testing deliverables
- `integration/`: StreetRace Manager integration testing deliverables
- `blackbox/`: QuickCart REST API black-box testing deliverables

## How To Run

Run white-box tests:

```bash
cd 2024101095/whitebox
pytest tests -v
```

Run integration tests:

```bash
cd 2024101095/integration
pytest tests -v
```

Run black-box API tests:

```bash
cd 2024101095/blackbox
pytest tests -v
```

Notes for black-box tests:

- Expected API base URL is `http://localhost:8080/api/v1`.
- Start QuickCart API before running this suite.
- Some tests are marked skipped/xfail for known API behavior mismatches documented in the black-box report.

## How To Run Code

Run MoneyPoly entrypoint:

```bash
cd 2024101095/whitebox/code
python main.py
```

StreetRace module code is under:

```text
2024101095/integration/code/
```

and is validated through the integration test suite.
