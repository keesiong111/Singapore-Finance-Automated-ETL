# Singapore-Finance-Automated-ETL
Automated ETL pipeline for Singapore financial datasets. Features AI-assisted Python scripts for automated data cleaning, transformation, and structured storage.

# Singapore Finance Automated ETL Pipeline (Python & MySQL)

## 🚀 Project Overview
This project demonstrates a **fully automated end-to-end ETL pipeline** designed to process multiple financial datasets from Singapore. Leveraging AI-assisted Python scripting, the pipeline automates the extraction, cleaning, and loading of raw Kaggle data into a structured MySQL database.

## 📊 Data Source
The datasets used in this project are sourced from Kaggle:
*   **Dataset:** [Finance Datasets Complete Singapore](https://www.kaggle.com/datasets/subhamjain/finance-datasets-complete-singapore)
*   **Description:** This collection includes comprehensive financial data from the Singapore government, covering CPF statistics, tax collection, and fiscal positions from various years.

## 🛠️ Key Automated Features
*   **Recursive File Discovery:** Automatically scans the `raw_data` directory and all its subfolders for CSV files.
*   **Intelligent Data Cleaning:** 
    *   Standardizes inconsistent column names into a clean, lower-case underscore format.
    *   Handles complex missing value strings (e.g., "na", "null", "-", "none").
    *   Automated duplicate removal based on configurable strategies.
    *   Automatic whitespace trimming for string columns.
*   **Smart Schema Ingestion:** Automatically transforms CSV filenames into SQL-compliant table names and manages database injection via SQLAlchemy.
*   **Dynamic Reporting:** Generates a real-time cleaning report for every file, tracking row counts, missing values, and data type conversions.

## 💻 Tech Stack
*   **Language:** Python 3.x (Pandas, NumPy)
*   **Database:** MySQL (SQLAlchemy, PyMySQL)
*   **Environment:** Linux (Ubuntu) / Windows
*   **Concepts:** ETL Pipeline, Data Automation, Schema Management

## 📂 Project Structure
*   `data_cleaner.py`: The core automation engine.
*   `raw_data/`: Input directory for original Kaggle CSVs (CPF, Tax, and Government Revenue data).
*   `cleaned_data/`: Output directory mirroring the raw data's folder structure with processed files.

## 📈 Data Insights
This pipeline processes key Singaporean financial indicators, including:
*   **CPF Statistics:** Yearly interest credited to members and retirement withdrawals.
*   **Taxation Records:** Corporate and individual income tax distributions.
*   **Government Revenue:** National operating revenue and fiscal positions.

---
*Note: This project represents a transition from 3D environment art to Data Engineering, showcasing a strong commitment to mastering automation tools and data-driven problem solving.*
