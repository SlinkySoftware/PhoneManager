# Bulk XLSX Imports

This document describes the bulk import workflow for creating Lines and Devices from a populated Excel workbook.

## Overview

The bulk import feature is designed for first-time onboarding and large batched changes.

- Access is restricted to Admin users.
- The frontend provides an Imports page with template download and workbook upload.
- The backend processes uploads entirely in memory and does not store temporary files on disk.
- Imports are partial-success by design: valid rows are created, invalid rows are skipped, and a summary is returned at the end.

## Template Workflow

1. Open the Imports page in the admin UI.
2. Download the template workbook.
3. Populate the two required sheets exactly as provided.
4. Upload the completed `.xlsx` file.
5. Review the import summary for imported and skipped rows.

The workbook must contain exactly two sheets, in this order:

1. `Devices`
2. `Lines`

The backend validates both the sheet names and the header row before processing any data.

## Imports Page Walkthrough

The admin-facing Imports page is intentionally narrow so workbook onboarding stays predictable.

What the page provides:

- A `Download Template` action that fetches the current two-sheet workbook from the backend.
- A single file picker restricted to `.xlsx` files up to 5 MB.
- An `Import Workbook` action that uploads the selected workbook as `multipart/form-data`.
- A summary card showing separate totals for lines and devices.
- Expandable tables showing every skipped row with the workbook row number, identifier, and failure reason.

What users should expect:

- The page does not preview workbook contents before import.
- The page does not update existing rows in place.
- The page keeps successful rows even if later rows fail.
- Errors are displayed inline on the page instead of as transient notifications so they remain visible during troubleshooting.

## Workbook Format

### Devices Sheet

Required headers:

| Column | Required | Description |
| ------ | -------- | ----------- |
| `MAC Address` | Yes | Device MAC address. Colon-separated, dash-separated, or plain 12-hex input is accepted and normalized to uppercase colon format. |
| `Name` | Yes | Friendly device name. Stored as the device description. |
| `Model` | Yes | Exact backend device `TypeID`, for example `YealinkSIPT33G`. |
| `Site` | Yes | Existing Site name already present in the database. |
| `Line E164 Numbers` | Yes | Comma-separated list of line numbers from the `Lines` sheet, in line assignment order. The first number becomes `line_1`. |
| `Enabled` | No | Boolean value. Accepted values are `TRUE` or `FALSE`. Blank defaults to `TRUE`. |

Important rules:

- Device rows may only reference line numbers that appear on the `Lines` sheet in the same workbook.
- The `Model` column must use the exact registered device type identifier, not a display label.
- Duplicate MAC addresses are skipped if they already exist in the database or are repeated within the workbook.
- If a referenced line row fails validation and is skipped, any device depending on that line is also skipped.

### Lines Sheet

Required headers:

| Column | Required | Description |
| ------ | -------- | ----------- |
| `Name` | Yes | Friendly line name. |
| `Line E164 Number` | Yes | Directory number for the line. Must match E.164-style numeric input used by the template rules. |
| `Registration User` | Yes | SIP registration username. |
| `Registration Password` | Yes | SIP registration password in plain text. Stored using the existing encrypted line field. |
| `Phone Label` | No | Optional screen label for supported devices. |
| `Shared` | No | Boolean value. Accepted values are `TRUE` or `FALSE`. Blank defaults to `FALSE`. |

Important rules:

- Duplicate line numbers are skipped if they already exist in the database or are repeated within the workbook.
- Imported line rows are processed before devices.
- Line passwords are written through the existing encrypted field implementation.

## Import Behavior

### Default Configuration Seeding

When a device row is created, its `device_specific_configuration` is seeded from `DeviceTypeConfig.device_defaults` for the selected `TypeID`.

This means the import path uses the same per-device defaults that are configured from the Device Types page.

`common_options` remain type-level settings and are not copied into each imported device record.

### Line Ordering

Secondary line order from the `Line E164 Numbers` column is preserved.

- The first number becomes `line_1`.
- Remaining numbers are attached as additional lines in the same order.
- That order is persisted in `Device.line_configuration['_line_order']` so provisioning renderers can emit lines in the imported order instead of alphabetical order.

### Duplicate Handling

The import is not all-or-nothing.

- Existing MAC addresses are skipped.
- Existing line E164 numbers are skipped.
- Duplicate values repeated within the same workbook are skipped.
- Processing continues for the remaining rows.

### Summary Response

At the end of an upload, the backend returns separate summaries for `lines` and `devices`.

Each section includes:

- `total`
- `imported_count`
- `skipped_count`
- `imported` row list
- `skipped` row list with row number, identifier, and reason

The frontend surfaces those counts and skipped-row reasons on the Imports page.

## API Endpoints

### Download Template

- Method: `GET`
- Path: `/api/imports/template/`
- Auth: Admin only
- Response: `.xlsx` workbook download

### Upload Workbook

- Method: `POST`
- Path: `/api/imports/upload/`
- Auth: Admin only
- Content type: `multipart/form-data`
- Form field: `file`
- Response: JSON import summary

## Limits And Validation

The current implementation applies these guardrails:

- Maximum upload size: 5 MB
- Maximum populated rows per workbook: 2000 combined across both sheets
- Workbook must be `.xlsx`
- Workbook must use the generated headers exactly
- Workbook must contain exactly the `Devices` and `Lines` sheets

## Operational Notes

- The feature is intended for onboarding and batch creation, not update-in-place workflows.
- Existing database rows are never modified by this import path.
- The backend logs the final import counts for audit and troubleshooting.
- Non-admin users cannot access the page or the endpoints.
