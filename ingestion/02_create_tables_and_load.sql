-- ============================================================
-- Rhodes Enterprises | Data Engineer Assessment
-- Step 2: Create Raw Tables & Load Data
-- Run after 01_setup_schemas.sql
-- ============================================================

USE DATABASE ASSESSMENT;
USE SCHEMA RAW;
USE WAREHOUSE COMPUTE_WH;

-- -------------------------------------------------------
-- TABLE 1: Homebuilder Sales (600 rows, CSV)
-- -------------------------------------------------------

CREATE OR REPLACE TABLE RAW.HOMEBUILDER_SALES (
    CONTRACT_ID         VARCHAR(20),
    COMMUNITY           VARCHAR(100),
    CITY                VARCHAR(100),
    REGION              VARCHAR(100),
    PLAN_NAME           VARCHAR(100),
    SQFT                INTEGER,
    BEDROOMS            INTEGER,
    BATHROOMS           FLOAT,
    BASE_PRICE          INTEGER,
    UPGRADE_AMOUNT      INTEGER,
    INCENTIVE_AMOUNT    INTEGER,
    CONTRACT_PRICE      INTEGER,
    CONTRACT_DATE       VARCHAR(20),    -- loaded as string, cast in staging
    CLOSE_DATE          VARCHAR(20),    -- nullable for Cancelled/Under Contract
    DAYS_TO_CLOSE       FLOAT,          -- nullable for open contracts
    STATUS              VARCHAR(30),
    BUYER_SOURCE        VARCHAR(50),
    AGENT_COMMISSION    FLOAT,
    LOAN_TYPE           VARCHAR(30),
    SALES_CONSULTANT    VARCHAR(100)
)
COMMENT = 'Raw homebuilder sales transactions 2023-2024. Source: Homebuilder_Sales.csv';

-- -------------------------------------------------------
-- TABLE 2: Regional Manager Lookup (3 rows, converted CSV)
-- -------------------------------------------------------

CREATE OR REPLACE TABLE RAW.REGIONAL_MANAGER_TARGETS (
    REGION              VARCHAR(100),
    REGIONAL_MANAGER    VARCHAR(100),
    SALES_TARGET_UNITS  INTEGER,
    MARGIN_TARGET_PCT   FLOAT
)
COMMENT = 'Regional manager names and annual sales targets. Source: Regional_Manager_Lookup.xlsx';

-- -------------------------------------------------------
-- LOAD DATA via Snowflake UI (Recommended for Trial)
-- -------------------------------------------------------
-- 1. Go to: Data > Databases > ASSESSMENT > RAW > Tables
-- 2. Click HOMEBUILDER_SALES > Load Data button
-- 3. Upload Homebuilder_Sales.csv — select "Comma" delimiter, first row as header
-- 4. Repeat for REGIONAL_MANAGER_TARGETS using the CSV you exported from the .xlsx
--
-- ALTERNATIVE: Stage-based COPY INTO (if you prefer CLI/scripted load)
-- -------------------------------------------------------

-- Create a named stage for file uploads
CREATE OR REPLACE STAGE RAW.ASSESSMENT_STAGE
    FILE_FORMAT = (
        TYPE = 'CSV'
        FIELD_OPTIONALLY_ENCLOSED_BY = '"'
        SKIP_HEADER = 1
        NULL_IF = ('', 'NULL', 'null')
        EMPTY_FIELD_AS_NULL = TRUE
        DATE_FORMAT = 'YYYY-MM-DD'
    )
    COMMENT = 'Internal stage for assessment file uploads';


-- Then run COPY INTO:
COPY INTO RAW.HOMEBUILDER_SALES
FROM @RAW.ASSESSMENT_STAGE/Homebuilder_Sales.csv
FILE_FORMAT = (
    TYPE = 'CSV'
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    SKIP_HEADER = 1
    NULL_IF = ('', 'NULL', 'null')
    EMPTY_FIELD_AS_NULL = TRUE
)
ON_ERROR = 'ABORT_STATEMENT';

COPY INTO RAW.REGIONAL_MANAGER_LOOKUP
FROM @RAW.ASSESSMENT_STAGE/Regional_Manager_Lookup.csv
FILE_FORMAT = (
    TYPE = 'CSV'
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    SKIP_HEADER = 1
    NULL_IF = ('', 'NULL', 'null')
    EMPTY_FIELD_AS_NULL = TRUE
)
ON_ERROR = 'ABORT_STATEMENT';

-- -------------------------------------------------------
-- Verify Loads
-- -------------------------------------------------------
SELECT 'HOMEBUILDER_SALES' AS table_name, COUNT(*) AS row_count FROM RAW.HOMEBUILDER_SALES
UNION ALL
SELECT 'REGIONAL_MANAGER_TARGETS', COUNT(*) FROM RAW.REGIONAL_MANAGER_TARGETS;

-- Expected: 600 rows, 3 rows
