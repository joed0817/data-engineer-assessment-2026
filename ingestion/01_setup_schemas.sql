-- ============================================================
-- Data Engineer Assessment
-- Step 1: Database & Schema Setup
-- Run this in a Snowflake worksheet as ACCOUNTADMIN or SYSADMIN
-- ============================================================

-- Create the database
CREATE DATABASE IF NOT EXISTS ASSESSMENT
    COMMENT = 'Data Engineer Assessment';

-- Create schemas with clear separation of concerns
CREATE SCHEMA IF NOT EXISTS ASSESSMENT.RAW
    COMMENT = 'Raw source data — untouched ingestion layer';

CREATE SCHEMA IF NOT EXISTS ASSESSMENT.STAGING
    COMMENT = 'Cleaned and standardized source data — managed by dbt';

CREATE SCHEMA IF NOT EXISTS ASSESSMENT.MARTS
    COMMENT = 'Analysis-ready models and AI outputs — managed by dbt';

-- Create a warehouse sized for development (auto-suspend to preserve credits)
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    COMMENT = 'Assessment development warehouse';

-- Set context
USE DATABASE ASSESSMENT;
USE SCHEMA RAW;
USE WAREHOUSE COMPUTE_WH;
